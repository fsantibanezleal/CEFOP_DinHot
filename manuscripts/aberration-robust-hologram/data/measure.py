#!/usr/bin/env python3
"""Measure the aberration-robust hologram of DinHot and write ``robust.json``, ``robust_numbers.tex`` and the tables.

Every number of the manuscript comes from this script, through the macros of ``robust_numbers.tex`` and the table files
``tab_*.tex``. The methods are the real ones of ``data-pipeline/pipeline/model/holo`` (B4 through ``b4_robust.run`` and
``ensemble_stats``, the published methods through ``optim/_gs_family``, ``optim/m10_cg`` and ``optim/m11_wirtinger_adam``);
the task, the setup, the ensemble and the budgets are those of the acceptance test ``tests/methods/beyond/test_b4_robust.py``
and of ``manuscripts/holographic-trap-studio/data/acceptance.py`` (read, not edited), over more seeds than the test uses.
The committed bake (``data-pipeline/pipeline/cases/measured_ranges.json``) is read for the cases of the studio.

The ablation reuses the engine's own pieces (``TrapCost``, ``cg_minimize``, the phase-fixed WGS start) in a replica of the
sigma-point run that varies the number and kind of design samples, the modes, the prior amplitude, the target level and the
iterations; the replica is checked against ``b4_robust.run`` on the default configuration (``replica`` in the JSON).

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/aberration-robust-hologram/data/measure.py [--workers 12] [--seeds 10]

Phases: 1 holograms of B4 (one per seed, cached in the cache folder), 2 evaluations, theory checks, pointing and ablation in
parallel, 3 the JSON, the macros and the tables. ``--emit-only`` rewrites the macros and the tables from an existing
``robust.json``. Deterministic: every method takes its seed through the portable generator, so a rerun gives the same
numbers up to the floating point of the machine's FFT.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import json
import math
import re
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.model.holo.core.forward import point_trap_projection, slm_field  # noqa: E402
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude, slm_grid  # noqa: E402
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import TrapSet, square_grid  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.core.zernike import wavefront_waves  # noqa: E402
from pipeline.model.holo.methods.beyond import b4_robust as B4  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402
from pipeline.model.holo.methods.optim import m10_cg as M10  # noqa: E402
from pipeline.model.holo.methods.optim import m11_wirtinger_adam as M11  # noqa: E402

TEST_SEED = 999          # seed of the ensemble of the acceptance test
N_ENS = 200              # ensemble size of the acceptance test
ITERS = 40               # CG iterations of B4 in the acceptance test
WARM = 30                # iterations of the phase-fixed WGS start and of the baseline
HELD_OUT = (1001, 1002, 1003, 1004, 1005)
THEORY_EPS = 1e-3        # waves, central difference of the first-order model
CURV_DELTA = 0.05        # bins, central difference of the pointing curvature


# ------------------------------------------------------------------------------------------------ setup and basis

def make_setup(n_pix: int = 256, pad: int = 2) -> Setup:
    """The setup of the acceptance tests: 12.5 um pitch, f = 250 mm, 850 nm, Gaussian beam of waist 1."""
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n_pix, pitch_m=12.5e-6, pad=pad,
                 beam="gaussian")


def task_traps(setup: Setup) -> TrapSet:
    """The 10 x 10 square lattice of equal traps, 8 FFT bins apart (the task of the acceptance test)."""
    return square_grid(10, 10, 8 * focal_bin_m(setup) * 1e6)


_ZB: dict[int, np.ndarray] = {}


def zbasis(setup: Setup) -> np.ndarray:
    """The 21 Noll modes of the engine on the SLM grid, in waves, shape (21, n, n); index = Noll j minus 1."""
    key = setup.n_pix
    if key not in _ZB:
        _ZB[key] = np.stack([wavefront_waves(np.eye(21)[j], setup) for j in range(21)])
    return _ZB[key]


def ab_phase(setup: Setup, c: np.ndarray) -> np.ndarray:
    """The aberration phase 2 pi sum_j c_j Z_j (radians, not wrapped: the field only sees it through exp)."""
    return 2.0 * math.pi * np.tensordot(np.asarray(c, dtype=np.float64), zbasis(setup)[: len(c)], axes=1)


def draw_coeffs(n: int, seed: int, aberration: float, n_traps: int) -> np.ndarray:
    """The coefficients of ``n`` draws of the engine's ``sample_perturbation`` (Noll 4 to 11) with the same stream order."""
    rng = Rng(seed)
    out = np.zeros((n, 21))
    for i in range(n):
        out[i, 3:11] = aberration * rng.normal_array(8)
        rng.normal_array(n_traps)       # the engine draws the pointing displacements (scale zero here) from the same stream
        rng.normal_array(n_traps)
    return out


def evaluate(phi: np.ndarray, setup: Setup, traps: TrapSet, coeffs: np.ndarray) -> dict:
    """Efficiency and relative standard deviation of one hologram over aberration draws (the engine's ``ensemble_stats``)."""
    eff, sig = [], []
    for c in coeffs:
        v = point_trap_projection(slm_field(phi + ab_phase(setup, c), setup), setup, traps)
        i = trap_intensities(v)
        eff.append(efficiency(i))
        sig.append(rel_std(i / traps.weight))
    sig = np.array(sig)
    return {"eff": np.array(eff), "sig": sig, "p95": float(np.percentile(sig, 95)), "mean": float(sig.mean()),
            "median": float(np.median(sig)), "max": float(sig.max()), "eff_mean": float(np.mean(eff))}


def summary(r: dict) -> dict:
    return {k: r[k] for k in ("p95", "mean", "median", "max", "eff_mean")}


# ------------------------------------------------------------------------------------------------ robust design replica

def sigma_points(modes: list[int], s: float) -> list[np.ndarray]:
    """``+- s sqrt(n)`` waves on one of the ``n`` modes at a time (mean zero, covariance ``s^2 I`` over the modes)."""
    pts = []
    for k in modes:
        for sg in (1.0, -1.0):
            c = np.zeros(21)
            c[k - 1] = sg * s * math.sqrt(len(modes))
            pts.append(c)
    return pts


def random_points(k: int, s: float, seed: int, modes: list[int]) -> list[np.ndarray]:
    rng = Rng(seed)
    pts = []
    for _ in range(k):
        c = np.zeros(21)
        z = rng.normal_array(len(modes))
        for j, m in enumerate(modes):
            c[m - 1] = s * z[j]
        pts.append(c)
    return pts


def design_run(setup: Setup, traps: TrapSet, seed: int, points: list[np.ndarray], *, level_fraction: float = 0.9,
               iterations: int = ITERS, warm: int = WARM) -> tuple[np.ndarray, np.ndarray, float]:
    """The sigma-point path of ``b4_robust.run`` with the design samples as an argument: returns (phi, start phi, level)."""
    phi0, _ = G.weighted_gs(setup, traps, warm, Rng(seed), variant="pfwgs")
    v0 = point_trap_projection(slm_field(phi0, setup), setup, traps)
    level = level_fraction * efficiency(trap_intensities(v0))
    phases = [ab_phase(setup, c) for c in points]
    cost = C.TrapCost(setup, traps, t=2, efficiency=level)

    def fun(x):
        total, grad = 0.0, 0.0
        for ab in phases:
            val, g, _ = cost.value_grad(x + ab)
            total += val / len(phases)
            grad = grad + g / len(phases)
        return total, grad, None

    res = C.cg_minimize(fun, phi0, iterations)
    return np.mod(res.x, 2.0 * math.pi), phi0, level


def circ_diff(a: np.ndarray, b: np.ndarray) -> float:
    d = np.angle(np.exp(1j * (a - b)))
    return float(np.abs(d).max())


# ------------------------------------------------------------------------------------------------ statistics

def sign_test_p(wins: int, n: int) -> float:
    """Two-sided exact binomial p-value of ``wins`` out of ``n`` under probability one half."""
    k = min(wins, n - wins)
    return float(min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / 2.0**n))


def boot_ratio(nom: np.ndarray, rob: np.ndarray, seed: int, reps: int = 2000) -> tuple[float, float]:
    """Paired bootstrap interval (2.5 and 97.5 percent) of the ratio of the 95th percentiles over the ensemble draws."""
    rng = np.random.default_rng(seed)
    n = len(nom)
    out = np.empty(reps)
    for r in range(reps):
        idx = rng.integers(0, n, n)
        out[r] = np.percentile(nom[idx], 95) / np.percentile(rob[idx], 95)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def boot_median(values: list[float], seed: int = 7, reps: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    v = np.array(values)
    med = np.array([np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(reps)])
    return float(np.percentile(med, 2.5)), float(np.percentile(med, 97.5))


# ------------------------------------------------------------------------------------------------ tasks (phase 1 and 2)

def cache_path(cache: str, seed: int) -> Path:
    return Path(cache) / f"b4_seed{seed}.npz"


def task_main(seed: int, cache: str, check_replica: bool) -> dict:
    """The hologram of B4 of one seed through the engine, the nominal one, and the acceptance ensemble for both."""
    t0 = time.time()
    s = make_setup()
    g = task_traps(s)
    base, _ = G.weighted_gs(s, g, WARM, Rng(seed), variant="pfwgs")
    res = B4.run(s, Target.from_traps(g), budget=Budget(ITERS), rng=Rng(seed), pointing_bins=0.0)
    run_s = time.time() - t0
    Path(cache).mkdir(parents=True, exist_ok=True)
    np.savez(cache_path(cache, seed), base=base, b4=res.phi, level=res.meta["level"],
             loss=np.array([h["loss"] for h in res.history]))
    coeffs = draw_coeffs(N_ENS, TEST_SEED, B4.DEFAULT_ABERRATION, len(g))
    nom, rob = evaluate(base, s, g, coeffs), evaluate(res.phi, s, g, coeffs)
    out = {"seed": seed, "nominal": summary(nom), "b4": summary(rob), "run_s": run_s,
           "ratio": nom["p95"] / rob["p95"], "eff_ratio": rob["eff_mean"] / nom["eff_mean"],
           "ratio_mean": nom["mean"] / rob["mean"], "level": float(res.meta["level"]),
           "wins": int(np.sum(rob["sig"] < nom["sig"])), "draws": N_ENS,
           "sig_nominal": nom["sig"].tolist(), "sig_b4": rob["sig"].tolist(),
           "loss": [float(h["loss"]) for h in res.history],
           "history_rel_std": [float(h["rel_std"]) for h in res.history],
           "history_eff": [float(h["efficiency"]) for h in res.history]}
    out["p95_ci"] = boot_ratio(nom["sig"], rob["sig"], seed)
    out["sign_p"] = sign_test_p(out["wins"], N_ENS)
    # the evaluator of this script against the engine's ensemble_stats (same hologram, same ensemble)
    eng = B4.ensemble_stats(s, res.phi, g, pointing_bins=0.0)
    out["evaluator_check"] = {"p95_here": rob["p95"], "p95_engine": eng["sigma_p95"],
                              "eff_here": rob["eff_mean"], "eff_engine": eng["efficiency_mean"]}
    if check_replica:
        phi, _, level = design_run(s, g, seed, sigma_points(list(range(4, 12)), B4.DEFAULT_ABERRATION))
        out["replica"] = {"max_phase_diff_rad": circ_diff(phi, res.phi), "level_diff": abs(level - res.meta["level"])}
    out["elapsed_s"] = time.time() - t0
    return out


def load_holograms(cache: str, seed: int) -> tuple[np.ndarray, np.ndarray, float]:
    z = np.load(cache_path(cache, seed))
    return z["base"], z["b4"], float(z["level"])


def task_heldout(seed: int, cache: str) -> dict:
    """The holograms of one seed on ensembles of other seeds (new draws of the same prior)."""
    s = make_setup()
    g = task_traps(s)
    base, b4, _ = load_holograms(cache, seed)
    rows = []
    for es in HELD_OUT:
        coeffs = draw_coeffs(N_ENS, es, B4.DEFAULT_ABERRATION, len(g))
        nom, rob = evaluate(base, s, g, coeffs), evaluate(b4, s, g, coeffs)
        rows.append({"ensemble_seed": es, "ratio": nom["p95"] / rob["p95"], "eff_ratio": rob["eff_mean"] / nom["eff_mean"]})
    return {"seed": seed, "rows": rows}


def task_mismatch(seed: int, cache: str) -> dict:
    """The holograms of one seed on ensembles that differ from the design prior (amplitude, modes outside the design)."""
    s = make_setup()
    g = task_traps(s)
    base, b4, _ = load_holograms(cache, seed)
    c0 = draw_coeffs(N_ENS, TEST_SEED, 1.0, len(g))           # unit-scale draws, scaled below
    rows = []
    for amp in (0.005, 0.01, 0.02, 0.03, 0.04):
        nom, rob = evaluate(base, s, g, c0 * amp), evaluate(b4, s, g, c0 * amp)
        rows.append({"kind": "amplitude", "value": amp, "nominal_p95": nom["p95"], "b4_p95": rob["p95"],
                     "ratio": nom["p95"] / rob["p95"], "eff_ratio": rob["eff_mean"] / nom["eff_mean"]})
    extra = Rng(4242)
    c1 = c0 * B4.DEFAULT_ABERRATION
    for label, modes in (("noll 12 to 15 added", (12, 13, 14, 15)), ("noll 12 to 21 as well", tuple(range(12, 22)))):
        c2 = c1.copy()
        zz = np.array([extra.normal_array(len(modes)) for _ in range(N_ENS)])
        for j, m in enumerate(modes):
            c2[:, m - 1] = B4.DEFAULT_ABERRATION * zz[:, j]
        nom, rob = evaluate(base, s, g, c2), evaluate(b4, s, g, c2)
        rows.append({"kind": "modes", "value": label, "nominal_p95": nom["p95"], "b4_p95": rob["p95"],
                     "ratio": nom["p95"] / rob["p95"], "eff_ratio": rob["eff_mean"] / nom["eff_mean"]})
    return {"seed": seed, "rows": rows}


def intensities(phi: np.ndarray, s: Setup, traps: TrapSet, c: np.ndarray | None = None) -> np.ndarray:
    ph = phi if c is None else phi + ab_phase(s, c)
    return trap_intensities(point_trap_projection(slm_field(ph, s), s, traps))


def task_theory(seed: int, cache: str) -> dict:
    """First-order model of the trap intensities in the aberration coefficients, checked against the ensemble."""
    s = make_setup()
    g = task_traps(s)
    base, b4, level = load_holograms(cache, seed)
    coeffs = draw_coeffs(N_ENS, TEST_SEED, B4.DEFAULT_ABERRATION, len(g))
    sa = B4.DEFAULT_ABERRATION
    cost = C.TrapCost(s, g, t=2, efficiency=level)
    pts = [ab_phase(s, c) for c in sigma_points(list(range(4, 12)), sa)]
    tsum = float(np.sum(cost.target**2))
    out = {"seed": seed}
    for name, phi in (("nominal", base), ("b4", b4)):
        i0 = intensities(phi, s, g)
        gm = np.zeros((len(g), 8))
        for col, k in enumerate(range(4, 12)):
            e = np.zeros(21)
            e[k - 1] = THEORY_EPS
            gm[:, col] = (intensities(phi, s, g, e) - intensities(phi, s, g, -e)) / (2 * THEORY_EPS)
        sig, lin = [], []
        for c in coeffs:
            sig.append(rel_std(intensities(phi, s, g, c) / g.weight))
            lin.append(rel_std((i0 + gm @ c[3:11]) / g.weight))
        sig, lin = np.array(sig), np.array(lin)
        ibar = float(i0.mean())
        gc = gm - gm.mean(axis=0, keepdims=True)
        p_total = sa**2 * float(np.sum(gm**2))
        pred_centered = rel_std(i0 / g.weight) ** 2 + 100.0**2 * sa**2 * float(np.sum(gc**2)) / (len(g) * ibar**2)
        bound = rel_std(i0 / g.weight) ** 2 + 100.0**2 * p_total / (len(g) * ibar**2)
        l0 = cost.value_grad(phi)[0]
        j_sig = float(np.mean([cost.value_grad(phi + ab)[0] for ab in pts]))
        out[name] = {"sigma0": rel_std(i0 / g.weight), "mean_intensity": ibar, "p_total": p_total,
                     "measured_mean_sq": float(np.mean(sig**2)), "pred_mean_sq": pred_centered, "bound_mean_sq": bound,
                     "pearson": float(np.corrcoef(sig, lin)[0, 1]), "p95_measured": float(np.percentile(sig, 95)),
                     "p95_linear": float(np.percentile(lin, 95)), "median_ratio_lin_over_true": float(np.median(lin / sig)),
                     "l0": float(l0), "j_sigma": j_sig, "delta_j": j_sig - float(l0), "gauss_newton": p_total / tsum,
                     "sig": sig.tolist(), "lin": lin.tolist(),
                     "g_rms_per_mode": [float(x) for x in np.sqrt(np.mean(gm**2, axis=0))]}
    return out


def task_published(seed: int, cache: str) -> dict:
    """Published methods run by the product on the same task and scored on the same ensemble."""
    s = make_setup()
    g = task_traps(s)
    t = Target.from_traps(g)
    base, b4, _ = load_holograms(cache, seed)
    coeffs = draw_coeffs(N_ENS, TEST_SEED, B4.DEFAULT_ABERRATION, len(g))
    holos = {"M04": G.weighted_gs(s, g, WARM, Rng(seed), variant="gs")[0],
             "M05": G.weighted_gs(s, g, WARM, Rng(seed), variant="gaa")[0],
             "M06": G.weighted_gs(s, g, WARM, Rng(seed), variant="gsw")[0],
             "M07": base,
             "M10": M10.run(s, t, budget=Budget(ITERS), rng=Rng(seed)).phi,
             "M11": M11.run(s, t, budget=Budget(ITERS), rng=Rng(seed)).phi,
             "B4": b4}
    rows = {}
    for name, phi in holos.items():
        r = evaluate(phi, s, g, coeffs)
        i0 = intensities(phi, s, g)
        rows[name] = {**summary(r), "nominal_sigma": rel_std(i0 / g.weight), "nominal_eff": efficiency(i0)}
    return {"seed": seed, "rows": rows}


def task_abl(name: str, seed: int, cache: str) -> dict:
    """One ablation configuration on one seed, scored on the acceptance ensemble against the seed's nominal hologram."""
    s = make_setup()
    g = task_traps(s)
    base, _, _ = load_holograms(cache, seed)
    coeffs = draw_coeffs(N_ENS, TEST_SEED, B4.DEFAULT_ABERRATION, len(g))
    sa0 = B4.DEFAULT_ABERRATION
    all_modes = list(range(4, 12))
    kw: dict = {}
    t0 = time.time()
    if name.startswith("rand"):                              # K fixed random draws
        k = int(name[4:])
        pts = random_points(k, sa0, 1000 + seed, all_modes)
    elif name == "nominal":                                  # one point: the nominal cost minimised by the same CG
        pts = [np.zeros(21)]
    elif name == "adam":                                     # resampled draws, Adam: the engine's design 'sample'
        res = B4.run(s, Target.from_traps(g), budget=Budget(ITERS), rng=Rng(seed), design="sample", q=8)
        phi = res.phi
        pts = None
    elif name.startswith("modes"):
        spec = name[5:]
        lo, hi = (int(x) for x in spec.split("-"))
        pts = sigma_points(list(range(lo, hi + 1)), sa0)
    elif name.startswith("prior"):
        pts = sigma_points(all_modes, float(name[5:]))
    elif name.startswith("level"):
        pts = sigma_points(all_modes, sa0)
        kw["level_fraction"] = float(name[5:])
    elif name.startswith("iter"):
        pts = sigma_points(all_modes, sa0)
        kw["iterations"] = int(name[4:])
    else:
        raise ValueError(name)
    if pts is not None:
        phi, _, _ = design_run(s, g, seed, pts, **kw)
    nom = evaluate(base, s, g, coeffs)
    rob = evaluate(phi, s, g, coeffs)
    i0 = intensities(phi, s, g)
    return {"name": name, "seed": seed, "p95": rob["p95"], "nominal_p95": nom["p95"], "ratio": nom["p95"] / rob["p95"],
            "eff_ratio": rob["eff_mean"] / nom["eff_mean"], "nominal_sigma": rel_std(i0 / g.weight),
            "elapsed_s": time.time() - t0}


def pointing_stats(s: Setup, phi: np.ndarray, g: TrapSet, n: int, bins: float) -> dict:
    r = B4.ensemble_stats(s, phi, g, n=n, pointing_bins=bins)
    return {"p95": r["sigma_p95"], "eff_mean": r["efficiency_mean"]}


def curvature(phi: np.ndarray, s: Setup, g: TrapSet, delta: float = CURV_DELTA, axis: str = "x") -> float:
    """Mean over traps of ``-(I(+d) + I(-d) - 2 I(0)) / (d^2 I(0))`` for a displacement of ``d`` bins along ``axis`` (bins^-2)."""
    b = focal_bin_m(s)
    i0 = trap_intensities(point_trap_projection(slm_field(phi, s), s, g))
    out = []
    for sg in (1.0, -1.0):
        if axis == "x":
            moved = TrapSet(replace(t, x_m=t.x_m + sg * delta * b) for t in g)
        else:
            moved = TrapSet(replace(t, y_m=t.y_m + sg * delta * b) for t in g)
        out.append(trap_intensities(point_trap_projection(slm_field(phi, s), s, moved)))
    return float(np.mean(-(out[0] + out[1] - 2.0 * i0) / (delta**2 * i0)))


def slope_square(phi: np.ndarray, s: Setup, g: TrapSet, delta: float = CURV_DELTA) -> float:
    """Mean over traps of ``s_x^2 + s_y^2`` with ``s = (I(+d) - I(-d)) / (2 d I(0))`` per focal bin (central differences)."""
    b = focal_bin_m(s)
    i0 = trap_intensities(point_trap_projection(slm_field(phi, s), s, g))
    tot = 0.0
    for axis in ("x", "y"):
        vals = []
        for sg in (1.0, -1.0):
            if axis == "x":
                moved = TrapSet(replace(t, x_m=t.x_m + sg * delta * b) for t in g)
            else:
                moved = TrapSet(replace(t, y_m=t.y_m + sg * delta * b) for t in g)
            vals.append(trap_intensities(point_trap_projection(slm_field(phi, s), s, moved)))
        tot += float(np.mean(((vals[0] - vals[1]) / (2 * delta * i0)) ** 2))
    return tot


def aperture_curvature(s: Setup) -> float:
    """``2 Var_A(k_x)`` in bins^-2: the curvature of a spot whose pixel phases are all aligned (amplitude-weighted variance)."""
    x, _ = slm_grid(s)
    a = input_amplitude(s)
    k = 2.0 * math.pi * x / (s.pad * s.n_pix * s.pitch_m)       # radians per bin of focal displacement
    w = a / a.sum()
    mean = float(np.sum(w * k))
    return 2.0 * float(np.sum(w * (k - mean) ** 2))


def task_point(seed: int, cache: str) -> dict:
    """Pointing errors: the acceptance configuration, a larger budget, the aberration design on the joint ensemble, curvature."""
    s = make_setup()
    g = task_traps(s)
    t = Target.from_traps(g)
    base, b4, _ = load_holograms(cache, seed)
    out = {"seed": seed}
    res = B4.run(s, t, budget=Budget(3), rng=Rng(seed), q=2, pointing_bins=0.15)
    nom, rob = pointing_stats(s, base, g, 20, 0.15), pointing_stats(s, res.phi, g, 20, 0.15)
    out["acceptance"] = {"nominal_p95": nom["p95"], "b4_p95": rob["p95"], "ratio": nom["p95"] / rob["p95"],
                         "eff_ratio": rob["eff_mean"] / nom["eff_mean"]}
    rows = []
    for d in (0.05, 0.10, 0.15):
        r2 = B4.run(s, t, budget=Budget(20), rng=Rng(seed), q=8, pointing_bins=d)
        nm, rb, sg = pointing_stats(s, base, g, 100, d), pointing_stats(s, r2.phi, g, 100, d), pointing_stats(s, b4, g, 100, d)
        rows.append({"bins": d, "nominal_p95": nm["p95"], "sample_p95": rb["p95"], "sigma_design_p95": sg["p95"],
                     "ratio_sample": nm["p95"] / rb["p95"], "ratio_sigma_design": nm["p95"] / sg["p95"],
                     "eff_ratio_sample": rb["eff_mean"] / nm["eff_mean"]})
    out["rows"] = rows
    out["curvature"] = {"nominal": curvature(base, s, g), "b4": curvature(b4, s, g), "aperture": aperture_curvature(s)}
    return out


def task_pointonly(seed: int, cache: str) -> dict:
    """Pointing errors alone (no aberration in the ensemble): the spread against the curvature prediction of Proposition 4."""
    s = make_setup()
    g = task_traps(s)
    t = Target.from_traps(g)
    base, b4, _ = load_holograms(cache, seed)
    kx, ky = curvature(base, s, g), curvature(base, s, g, axis="y")
    sl2 = slope_square(base, s, g)
    kap = 0.5 * (kx + ky)
    rows = []
    for d in (0.05, 0.10, 0.15):
        nm = B4.ensemble_stats(s, base, g, n=N_ENS, aberration=0.0, pointing_bins=d)
        rb = B4.ensemble_stats(s, b4, g, n=N_ENS, aberration=0.0, pointing_bins=d)
        row = {"bins": d, "nominal_mean": nm["sigma_mean"], "b4_mean": rb["sigma_mean"], "nominal_p95": nm["sigma_p95"],
               "b4_p95": rb["sigma_p95"], "predicted_nominal": 100.0 * kap * d * d,
               "predicted_with_slope": 100.0 * math.sqrt(sl2 * d * d + (kap * d * d) ** 2),
               "nominal_eff": nm["efficiency_mean"], "b4_eff": rb["efficiency_mean"]}
        # the same cost with a displacement prior alone (no aberration in the design), 20 steps, scored on the same ensemble
        res = B4.run(s, t, budget=Budget(20), rng=Rng(seed), q=8, aberration=0.0, pointing_bins=d)
        pr = B4.ensemble_stats(s, res.phi, g, n=N_ENS, aberration=0.0, pointing_bins=d)
        row["pointing_design_mean"] = pr["sigma_mean"]
        row["pointing_design_p95"] = pr["sigma_p95"]
        row["pointing_design_eff"] = pr["efficiency_mean"]
        # a five times larger budget
        res = B4.run(s, t, budget=Budget(100), rng=Rng(seed), q=8, aberration=0.0, pointing_bins=d)
        pr = B4.ensemble_stats(s, res.phi, g, n=N_ENS, aberration=0.0, pointing_bins=d)
        row["pointing_design_100_p95"] = pr["sigma_p95"]
        row["pointing_design_100_mean"] = pr["sigma_mean"]
        row["pointing_design_100_eff"] = pr["efficiency_mean"]
        row["pointing_design_100_slope_square"] = slope_square(res.phi, s, g)
        row["pointing_design_100_curvature"] = curvature(res.phi, s, g)
        rows.append(row)
    return {"seed": seed, "kappa_x": kx, "kappa_y": ky, "kappa_b4_x": curvature(b4, s, g), "slope_square_nominal": sl2,
            "slope_square_b4": slope_square(b4, s, g), "rows": rows}


# ------------------------------------------------------------------------------------------------ the bake

def bake_rows() -> dict:
    d = json.loads((ROOT / "data-pipeline" / "pipeline" / "cases" / "measured_ranges.json").read_text(encoding="utf-8"))
    rows = {}
    for case, vals in d["measured"].items():
        if "B4.rel_std_pct" not in vals:
            continue
        rows[case] = {k: vals[k] for k in ("B4.rel_std_pct", "B4.efficiency", "M07.rel_std_pct", "M07.efficiency")
                      if k in vals}
    return {"seeds": d["seeds"], "cases": rows}


# ------------------------------------------------------------------------------------------------ driver

ABLATION = [  # (group, name, label)
    ("design", "default", "sigma points, 16 deterministic draws (default)"),
    ("design", "nominal", "nominal cost only, same CG (one point)"),
    ("design", "rand4", "4 fixed random draws, same CG"),
    ("design", "rand8", "8 fixed random draws, same CG"),
    ("design", "rand16", "16 fixed random draws, same CG"),
    ("design", "rand32", "32 fixed random draws, same CG"),
    ("design", "adam", "resampled draws (8 per step), Adam"),
    ("modes", "modes4-4", "defocus only (Noll 4)"),
    ("modes", "modes4-6", "Noll 4 to 6"),
    ("modes", "modes4-8", "Noll 4 to 8"),
    ("modes", "modes9-11", "Noll 9 to 11 (not the dominant modes)"),
    ("modes", "default", "Noll 4 to 11 (default)"),
    ("prior", "prior0.005", "design amplitude 0.005 waves per mode"),
    ("prior", "prior0.01", "design amplitude 0.01 waves per mode"),
    ("prior", "default", "design amplitude 0.02 waves per mode (default)"),
    ("prior", "prior0.03", "design amplitude 0.03 waves per mode"),
    ("prior", "prior0.04", "design amplitude 0.04 waves per mode"),
    ("level", "level0.8", "target level 0.80"),
    ("level", "level0.85", "target level 0.85"),
    ("level", "default", "target level 0.90 (default)"),
    ("level", "level0.937", "target level 0.937"),
    ("level", "level0.95", "target level 0.95"),
    ("level", "level1.0", "target level 1.00"),
    ("iterations", "iter5", "5 CG iterations"),
    ("iterations", "iter10", "10 CG iterations"),
    ("iterations", "iter20", "20 CG iterations"),
    ("iterations", "default", "40 CG iterations (default)"),
    ("iterations", "iter80", "80 CG iterations"),
]


ABL_KEY = {"default": "Default", "nominal": "Nominal", "rand4": "RandFour", "rand8": "RandEight", "rand16": "RandSixteen",
           "rand32": "RandThirtyTwo", "adam": "Adam", "modes4-4": "ModesDefocus", "modes4-6": "ModesToSix",
           "modes4-8": "ModesToEight", "modes9-11": "ModesHigh", "prior0.005": "PriorA", "prior0.01": "PriorB",
           "prior0.03": "PriorD", "prior0.04": "PriorE", "level0.8": "LevelA", "level0.85": "LevelB", "level0.937": "LevelD",
           "level0.95": "LevelE", "level1.0": "LevelF", "iter5": "IterA", "iter10": "IterB", "iter20": "IterC",
           "iter80": "IterE"}
PUB_KEY = {"M04": "GS", "M05": "GAA", "M06": "GSW", "M07": "PFWGS", "M10": "CG", "M11": "Wirt", "B4": "Bfour"}


def rng_summary(v: list[float]) -> dict:
    return {"median": statistics.median(v), "min": min(v), "max": max(v), "n": len(v)}


def run_all(args) -> dict:
    cache = args.cache
    seeds = list(range(1, args.seeds + 1))
    three = seeds[:3]
    t_start = time.time()
    data: dict = {"meta": {"seeds": seeds, "ensemble_size": N_ENS, "ensemble_seed": TEST_SEED, "iterations": ITERS, "warm": WARM,
                           "aberration": B4.DEFAULT_ABERRATION, "level_fraction": B4.DEFAULT_LEVEL_FRACTION,
                           "q": B4.DEFAULT_Q, "lr": B4.DEFAULT_LR, "held_out_seeds": list(HELD_OUT), "workers": args.workers,
                           "command": "python manuscripts/aberration-robust-hologram/data/measure.py "
                                      f"--workers {args.workers} --seeds {args.seeds}"}}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        print(f"phase 1: B4 holograms of {len(seeds)} seeds", flush=True)
        futs = [ex.submit(task_main, sd, cache, sd == 1) for sd in seeds]
        data["main"] = sorted((f.result() for f in futs), key=lambda r: r["seed"])
        print(f"phase 1 done at {time.time() - t_start:.0f} s", flush=True)
        jobs = {"heldout": [ex.submit(task_heldout, sd, cache) for sd in three],
                "mismatch": [ex.submit(task_mismatch, sd, cache) for sd in three],
                "theory": [ex.submit(task_theory, sd, cache) for sd in three],
                "published": [ex.submit(task_published, sd, cache) for sd in three],
                "point": [ex.submit(task_point, sd, cache) for sd in three]}
        abl = [ex.submit(task_abl, n, sd, cache) for _, n, _ in ABLATION if n != "default" for sd in three]
        for key, fl in jobs.items():
            data[key] = sorted((f.result() for f in fl), key=lambda r: r["seed"])
            print(f"{key} done at {time.time() - t_start:.0f} s", flush=True)
        po = [ex.submit(task_pointonly, sd, cache) for sd in three]
        data["pointonly"] = sorted((f.result() for f in po), key=lambda r: r["seed"])
        data["ablation_runs"] = [f.result() for f in abl]
        print(f"ablation done at {time.time() - t_start:.0f} s", flush=True)
    data["bake"] = bake_rows()
    data["meta"]["total_s"] = time.time() - t_start
    data["meta"]["machine_note"] = "wall-clock of this run on the development machine; the rows' run_s are per-seed times of one B4 run"
    return data


# ------------------------------------------------------------------------------------------------ macros and tables

def neg(s: str) -> str:
    """A number as text with a typeset minus sign."""
    return "$-$" + s[1:] if s.startswith("-") else s


def f(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}"


def macro_name(name: str) -> str:
    return "\\newcommand{\\" + name + "}{"


class Macros:
    def __init__(self) -> None:
        self.lines: list[str] = ["% Written by data/measure.py: do not edit.\n"]

    def add(self, name: str, value: str) -> None:
        assert name.isalpha(), name
        self.lines.append(macro_name(name) + value + "}\n")


def write_outputs(data: dict, out: Path) -> None:
    m = Macros()
    main = data["main"]
    three = [r for r in main if r["seed"] <= 3]
    ratios3 = [r["ratio"] for r in three]
    effs3 = [r["eff_ratio"] for r in three]
    ratios_all = [r["ratio"] for r in main]
    effs_all = [r["eff_ratio"] for r in main]
    meta = data["meta"]
    lo, hi = boot_median(ratios_all)
    # parameters read from the engine
    m.add("parNens", str(meta["ensemble_size"]))
    m.add("parEnsSeed", str(meta["ensemble_seed"]))
    m.add("parIters", str(meta["iterations"]))
    m.add("parWarm", str(meta["warm"]))
    m.add("parAb", f(meta["aberration"], 2))
    m.add("parAbSqrt", f(meta["aberration"] * math.sqrt(8), 3))
    m.add("parAbRms", f(meta["aberration"] * math.sqrt(8), 3))
    m.add("parLevel", f(meta["level_fraction"], 2))
    m.add("parQ", str(meta["q"]))
    m.add("parLr", f(meta["lr"], 2))
    m.add("workersUsed", str(meta["workers"]))
    m.add("parCurvDelta", f(CURV_DELTA, 2))
    m.add("nSeedsAll", str(len(main)))
    m.add("nSeedsThree", str(len(three)))
    m.add("ratioMed", f(statistics.median(ratios3), 3))
    m.add("ratioMin", f(min(ratios3), 2))
    m.add("ratioMax", f(max(ratios3), 2))
    m.add("effRatioMed", f(statistics.median(effs3), 3))
    m.add("effRatioMin", f(min(effs3), 3))
    m.add("effRatioMax", f(max(effs3), 3))
    m.add("ratioAllMed", f(statistics.median(ratios_all), 3))
    m.add("ratioAllMin", f(min(ratios_all), 2))
    m.add("ratioAllMax", f(max(ratios_all), 2))
    m.add("ratioAllCiLo", f(lo, 2))
    m.add("ratioAllCiHi", f(hi, 2))
    m.add("effAllMed", f(statistics.median(effs_all), 3))
    m.add("effAllMin", f(min(effs_all), 3))
    m.add("effAllMax", f(max(effs_all), 3))
    m.add("seedsPassing", str(sum(1 for r in ratios_all if r >= 1.25)))
    m.add("ciBelowN", str(sum(1 for r in main if r["p95_ci"][0] < 1.25)))
    m.add("seedsEffPassing", str(sum(1 for r in effs_all if r >= 0.9)))
    s1 = main[0]
    m.add("sigmaNomOne", f(s1["nominal"]["p95"], 3))
    m.add("sigmaBfourOne", f(s1["b4"]["p95"], 3))
    m.add("ratioOne", f(s1["ratio"], 2))
    m.add("ratioOneLo", f(s1["p95_ci"][0], 2))
    m.add("ratioOneHi", f(s1["p95_ci"][1], 2))
    m.add("winsOne", str(s1["wins"]))
    mant, ex = "{:.1e}".format(s1["sign_p"]).split("e")
    m.add("signPOne", mant + "\\times10^{" + str(int(ex)) + "}")
    m.add("runSeconds", f(statistics.median(r["run_s"] for r in main), 0))
    m.add("totalMinutes", f(meta["total_s"] / 60.0, 0))
    m.add("pointonlyMinutes", f(meta.get("extra_s", {}).get("pointonly", float("nan")) / 60.0, 0))
    m.add("pointonlyWorkers", str(meta.get("extra_workers", {}).get("pointonly", "")))
    m.add("evalMeanNom", f(s1["nominal"]["mean"], 2))
    m.add("evalMeanBfour", f(s1["b4"]["mean"], 2))
    m.add("evalMaxNom", f(s1["nominal"]["max"], 1))
    m.add("evalMaxBfour", f(s1["b4"]["max"], 1))
    m.add("evalMedNom", f(s1["nominal"]["median"], 2))
    m.add("evalMedBfour", f(s1["b4"]["median"], 2))
    m.add("meanRatioOne", f(s1["ratio_mean"], 2))
    m.add("levelAbs", f(s1["level"], 4))
    m.add("effDropOne", f(s1["nominal"]["eff_mean"] / (s1["level"] / meta["level_fraction"]), 3))
    m.add("strehlExp", f(math.exp(-((2.0 * math.pi * meta["aberration"] * math.sqrt(8.0)) ** 2)), 3))
    m.add("phaseRms", f(2.0 * math.pi * meta["aberration"] * math.sqrt(8.0), 2))
    m.add("strehlThree", f(math.exp(-((2.0 * math.pi * 0.03 * math.sqrt(8.0)) ** 2)), 2))
    m.add("startEffOne", f(s1["level"] / meta["level_fraction"], 3))
    rep = s1.get("replica", {})
    m.add("replicaDiff", "{:.1e}".format(rep.get("max_phase_diff_rad", float("nan"))))
    chk = [r["evaluator_check"] for r in main]
    m.add("evalCheckMax", "{:.1e}".format(max(max(abs(c["p95_here"] - c["p95_engine"]), abs(c["eff_here"] - c["eff_engine"])) for c in chk)))
    # trap loss
    loss1 = s1["loss"]
    m.add("lossStart", "{:.3g}".format(loss1[0]))
    m.add("lossEnd", "{:.3g}".format(loss1[-1]))
    m.add("nIterHist", str(len(loss1)))
    # held-out ensembles
    ho = [(r["seed"], x) for r in data["heldout"] for x in r["rows"]]
    hr = [x["ratio"] for _, x in ho]
    m.add("heldMed", f(statistics.median(hr), 2))
    m.add("heldMin", f(min(hr), 2))
    m.add("heldMax", f(max(hr), 2))
    m.add("heldN", str(len(hr)))
    m.add("heldEffMed", f(statistics.median(x["eff_ratio"] for _, x in ho), 3))
    # mismatch
    mis = {}
    for r in data["mismatch"]:
        for x in r["rows"]:
            mis.setdefault((x["kind"], x["value"]), []).append(x)
    for (kind, val), xs in mis.items():
        if kind == "amplitude":
            tag = {0.005: "A", 0.01: "B", 0.02: "C", 0.03: "D", 0.04: "E"}[val]
            m.add("mis" + tag + "Med", f(statistics.median(x["ratio"] for x in xs), 2))
            m.add("mis" + tag + "Min", f(min(x["ratio"] for x in xs), 2))
            m.add("mis" + tag + "Max", f(max(x["ratio"] for x in xs), 2))
        else:
            tag = "F" if val.startswith("noll 12 to 15") else "G"
            m.add("mis" + tag + "Med", f(statistics.median(x["ratio"] for x in xs), 2))
            m.add("mis" + tag + "Min", f(min(x["ratio"] for x in xs), 2))
            m.add("mis" + tag + "Max", f(max(x["ratio"] for x in xs), 2))
    # theory
    th = data["theory"]
    for name, tag in (("nominal", "Nom"), ("b4", "Bfour")):
        m.add("thPearson" + tag, f(statistics.median(t[name]["pearson"] for t in th), 3))
        m.add("thPtotal" + tag, "{:.3g}".format(statistics.median(t[name]["p_total"] for t in th)))
        m.add("thMeasSq" + tag, f(statistics.median(t[name]["measured_mean_sq"] for t in th), 2))
        m.add("thPredSq" + tag, f(statistics.median(t[name]["pred_mean_sq"] for t in th), 2))
        m.add("thBoundSq" + tag, f(statistics.median(t[name]["bound_mean_sq"] for t in th), 2))
        m.add("thQMeas" + tag, f(statistics.median(t[name]["p95_measured"] for t in th), 2))
        m.add("thQLin" + tag, f(statistics.median(t[name]["p95_linear"] for t in th), 2))
        m.add("thSigmaZero" + tag, "{:.2g}".format(statistics.median(t[name]["sigma0"] for t in th)))
        m.add("thDeltaJ" + tag, neg("{:.3g}".format(statistics.median(t[name]["delta_j"] for t in th))))
        m.add("thGN" + tag, "{:.3g}".format(statistics.median(t[name]["gauss_newton"] for t in th)))
        m.add("thLzero" + tag, "{:.3g}".format(statistics.median(t[name]["l0"] for t in th)))
        m.add("thJsig" + tag, "{:.3g}".format(statistics.median(t[name]["j_sigma"] for t in th)))
    m.add("thPRatio", f(statistics.median(t["nominal"]["p_total"] / t["b4"]["p_total"] for t in th), 2))
    m.add("thQLinRatio", f(statistics.median(t["nominal"]["p95_linear"] / t["b4"]["p95_linear"] for t in th), 2))
    m.add("thResidNom", neg(f(statistics.median(t["nominal"]["delta_j"] - t["nominal"]["gauss_newton"] for t in th), 3)))
    # pointing
    pt = data["point"]
    acc = [p["acceptance"] for p in pt]
    m.add("ptAccMed", f(statistics.median(a["ratio"] for a in acc), 2))
    m.add("ptAccMin", f(min(a["ratio"] for a in acc), 2))
    m.add("ptAccMax", f(max(a["ratio"] for a in acc), 2))
    m.add("ptAccOne", f(acc[0]["ratio"], 2))
    m.add("ptAccNomOne", f(acc[0]["nominal_p95"], 3))
    m.add("ptAccBfourOne", f(acc[0]["b4_p95"], 3))
    for d, tag in ((0.05, "A"), (0.10, "B"), (0.15, "C")):
        rows = [r for p in pt for r in p["rows"] if abs(r["bins"] - d) < 1e-9]
        m.add("pt" + tag + "Sample", f(statistics.median(r["ratio_sample"] for r in rows), 2))
        m.add("pt" + tag + "SampleMin", f(min(r["ratio_sample"] for r in rows), 2))
        m.add("pt" + tag + "SampleMax", f(max(r["ratio_sample"] for r in rows), 2))
        m.add("pt" + tag + "Sigma", f(statistics.median(r["ratio_sigma_design"] for r in rows), 2))
        m.add("pt" + tag + "Eff", f(statistics.median(r["eff_ratio_sample"] for r in rows), 3))
    cv = [p["curvature"] for p in pt]
    m.add("curvNom", f(statistics.median(c["nominal"] for c in cv), 3))
    m.add("curvBfour", f(statistics.median(c["b4"] for c in cv), 3))
    m.add("curvAp", f(cv[0]["aperture"], 3))
    m.add("curvRelLoss", f(statistics.median(c["nominal"] for c in cv) * 0.15**2 / 2.0 * 100.0, 1))
    # pointing alone
    if "pointonly" in data:
        po = data["pointonly"]
        for d, tag in ((0.05, "A"), (0.10, "B"), (0.15, "C")):
            rows = [r for p in po for r in p["rows"] if abs(r["bins"] - d) < 1e-9]
            m.add("po" + tag + "Nom", f(statistics.median(r["nominal_mean"] for r in rows), 2))
            m.add("po" + tag + "Pred", f(statistics.median(r["predicted_nominal"] for r in rows), 2))
            m.add("po" + tag + "PredSlope", f(statistics.median(r["predicted_with_slope"] for r in rows), 2))
            m.add("po" + tag + "Bfour", f(statistics.median(r["b4_mean"] for r in rows), 2))
            m.add("po" + tag + "Design", f(statistics.median(r["pointing_design_mean"] for r in rows), 2))
            m.add("po" + tag + "Ratio", f(statistics.median(r["nominal_p95"] / r["pointing_design_p95"] for r in rows), 2))
            m.add("po" + tag + "RatioMin", f(min(r["nominal_p95"] / r["pointing_design_p95"] for r in rows), 2))
            m.add("po" + tag + "RatioMax", f(max(r["nominal_p95"] / r["pointing_design_p95"] for r in rows), 2))
            m.add("po" + tag + "Eff", f(statistics.median(r["pointing_design_eff"] / r["nominal_eff"] for r in rows), 3))
        for d, tag in ((0.05, "A"), (0.10, "B"), (0.15, "C")):
            big = [r for p in po for r in p["rows"] if abs(r["bins"] - d) < 1e-9]
            rr = [r["nominal_p95"] / r["pointing_design_100_p95"] for r in big]
            m.add("po" + tag + "Long", f(statistics.median(rr), 2))
            m.add("po" + tag + "LongMin", f(min(rr), 2))
            m.add("po" + tag + "LongMax", f(max(rr), 2))
            m.add("po" + tag + "LongEff", f(statistics.median(r["pointing_design_100_eff"] / r["nominal_eff"] for r in big), 3))
            m.add("po" + tag + "LongMean", f(statistics.median(r["pointing_design_100_mean"] for r in big), 2))
            m.add("po" + tag + "LongSlope", f(statistics.median(r["pointing_design_100_slope_square"] for r in big), 3))
            m.add("po" + tag + "LongCurv", f(statistics.median(r["pointing_design_100_curvature"] for r in big), 3))
        m.add("poKx", f(statistics.median(p["kappa_x"] for p in po), 3))
        m.add("poKy", f(statistics.median(p["kappa_y"] for p in po), 3))
        m.add("poSlopeSq", f(statistics.median(p["slope_square_nominal"] for p in po), 3))
        m.add("poSlopeRms", f(math.sqrt(statistics.median(p["slope_square_nominal"] for p in po)), 2))
        m.add("poSlopeSqBfour", f(statistics.median(p["slope_square_b4"] for p in po), 3))
    # ablation
    by: dict[str, dict] = {}
    for r in data["ablation_runs"]:
        by.setdefault(r["name"], {"ratio": [], "eff": []})
        by[r["name"]]["ratio"].append(r["ratio"])
        by[r["name"]]["eff"].append(r["eff_ratio"])
    by["default"] = {"ratio": ratios3, "eff": effs3}
    for name, d in by.items():
        key = "abl" + ABL_KEY[name]
        m.add(key + "Med", f(statistics.median(d["ratio"]), 2))
        m.add(key + "Min", f(min(d["ratio"]), 2))
        m.add(key + "Max", f(max(d["ratio"]), 2))
        m.add(key + "Eff", f(statistics.median(d["eff"]), 3))
    # published
    pub = data["published"]
    names = list(pub[0]["rows"])
    p95_pf = {sd["seed"]: sd["rows"]["M07"]["p95"] for sd in pub}
    for nm in names:
        key = "pub" + PUB_KEY[nm]
        m.add(key + "Pn", f(statistics.median(sd["rows"][nm]["p95"] for sd in pub), 2))
        m.add(key + "Ratio", f(statistics.median(p95_pf[sd["seed"]] / sd["rows"][nm]["p95"] for sd in pub), 2))
        m.add(key + "Eff", f(statistics.median(sd["rows"][nm]["eff_mean"] / sd["rows"]["M07"]["eff_mean"] for sd in pub), 3))
    # bake
    bk = data["bake"]["cases"]
    c9 = bk.get("C09_aberrated")
    ideal = [x for case in ("C01_square_grid", "C02_grid_feedback", "C07_high_na") for x in bk.get(case, {}).get("M07.rel_std_pct", [])]
    m.add("bakeIdealBelow", str(sum(1 for x in ideal if x < 0.01)))
    m.add("bakeIdealN", str(len(ideal)))
    if c9:
        m.add("bakeNineB", f(statistics.mean(c9["B4.rel_std_pct"]), 2))
        m.add("bakeNineM", f(statistics.mean(c9["M07.rel_std_pct"]), 2))
        m.add("bakeNineRatio", f(statistics.mean(c9["M07.rel_std_pct"]) / statistics.mean(c9["B4.rel_std_pct"]), 2))
        m.add("bakeNineEff", f(statistics.mean(c9["B4.efficiency"]) / statistics.mean(c9["M07.efficiency"]), 2))
    (out / "robust_numbers.tex").write_text("".join(m.lines), encoding="utf-8")

    # ---- tables
    def tex_table(fname: str, lines: list[str]) -> None:
        """Rows of a table body; the last row has no row end, the including document adds it after the input."""
        body = "\n".join(lines)
        body = re.sub(r"\s*\\\\\s*$", "", body)
        (out / fname).write_text(body + "\n", encoding="utf-8")

    L = []
    for r in main:
        L.append(f"{r['seed']} & {f(r['nominal']['p95'], 3)} & {f(r['b4']['p95'], 3)} & {f(r['ratio'], 2)} "
                 f"[{f(r['p95_ci'][0], 2)}, {f(r['p95_ci'][1], 2)}] & {f(r['eff_ratio'], 3)} & {r['wins']}/{r['draws']} \\\\")
    tex_table("tab_main_rows.tex", L)

    L = []
    label = {"M04": "Gerchberg--Saxton", "M05": "generalized adaptive additive", "M06": "weighted GS",
             "M07": "phase-fixed WGS", "M10": "conjugate gradient, nominal cost",
             "M11": "Wirtinger gradient with Adam", "B4": "aberration-robust hologram"}
    for nm in names:
        rows = [sd["rows"][nm] for sd in pub]
        L.append(f"{label[nm]} & {f(statistics.median(r['p95'] for r in rows), 2)} & "
                 f"{f(statistics.median(r['mean'] for r in rows), 2)} & "
                 f"{f(statistics.median(r['eff_mean'] for r in rows), 3)} & "
                 f"{statistics.median(r['nominal_sigma'] for r in rows):.2g} \\\\")
    tex_table("tab_pub_rows.tex", L)

    L = []
    group_title = {"design": "Design samples", "modes": "Modes in the design", "prior": "Design amplitude",
                   "level": "Target level", "iterations": "Iterations"}
    cur = None
    for grp, name, lab in ABLATION:
        if grp != cur:
            if cur is not None:
                L.append("\\midrule")
            L.append(f"\\emph{{{group_title[grp]}}} & & & \\\\")
            cur = grp
        d = by[name]
        L.append(f"\\quad {lab} & {f(statistics.median(d['ratio']), 2)} & {f(min(d['ratio']), 2)} to {f(max(d['ratio']), 2)} & "
                 f"{f(statistics.median(d['eff']), 3)} \\\\")
    tex_table("tab_abl_rows.tex", L)

    L = []
    for (kind, val), xs in mis.items():
        lab = f"{val} waves per mode, Noll 4 to 11" if kind == "amplitude" else f"design modes plus {val[5:]}" if val.startswith("noll 12 to 15") else "design modes plus Noll 12 to 21"
        L.append(f"{lab} & {f(statistics.median(x['nominal_p95'] for x in xs), 2)} & {f(statistics.median(x['b4_p95'] for x in xs), 2)} & "
                 f"{f(statistics.median(x['ratio'] for x in xs), 2)} ({f(min(x['ratio'] for x in xs), 2)} to {f(max(x['ratio'] for x in xs), 2)}) & "
                 f"{f(statistics.median(x['eff_ratio'] for x in xs), 3)} \\\\")
    tex_table("tab_mismatch_rows.tex", L)

    L = []
    for t in th:
        for name, lab in (("nominal", "phase-fixed WGS"), ("b4", "robust hologram")):
            x = t[name]
            L.append(f"{t['seed']} & {lab} & {x['sigma0']:.2g} & {f(x['measured_mean_sq'], 2)} & {f(x['pred_mean_sq'], 2)} & "
                     f"{f(x['bound_mean_sq'], 2)} & {f(x['pearson'], 3)} & {f(x['p95_measured'], 2)} & {f(x['p95_linear'], 2)} \\\\")
    tex_table("tab_theory_rows.tex", L)

    L = []
    for t in th:
        for name, lab in (("nominal", "phase-fixed WGS"), ("b4", "robust hologram")):
            x = t[name]
            L.append(f"{t['seed']} & {lab} & {x['l0']:.3g} & {x['j_sigma']:.3g} & {neg(format(x['delta_j'], '.3g'))} & {x['gauss_newton']:.3g} \\\\")
    tex_table("tab_cost_rows.tex", L)

    L = []
    for p in pt:
        a = p["acceptance"]
        L.append(f"{p['seed']} & acceptance configuration, 0.15 bin, 20 draws & {f(a['nominal_p95'], 3)} & {f(a['b4_p95'], 3)} & {f(a['ratio'], 2)} \\\\")
        for r in p["rows"]:
            L.append(f"{p['seed']} & 20 steps, 8 draws per step, {r['bins']:.2f} bin, 100 draws & {f(r['nominal_p95'], 3)} & {f(r['sample_p95'], 3)} & {f(r['ratio_sample'], 2)} \\\\")
    tex_table("tab_point_rows.tex", L)

    if "pointonly" in data:
        L = []
        for p in data["pointonly"]:
            for r in p["rows"]:
                L.append(f"{p['seed']} & {r['bins']:.2f} & {f(r['nominal_mean'], 2)} & {f(r['predicted_nominal'], 2)} & "
                         f"{f(r['predicted_with_slope'], 2)} & {f(r['b4_mean'], 2)} & {f(r['pointing_design_mean'], 2)} & "
                         f"{f(r['nominal_p95'], 2)} & {f(r['pointing_design_p95'], 2)} & {f(r['pointing_design_100_p95'], 2)} \\\\")
        tex_table("tab_pointonly_rows.tex", L)

    L = []
    for case, v in bk.items():
        L.append(f"{case.replace('_', ' ')} & {f(statistics.mean(v['M07.rel_std_pct']), 3)} & {f(statistics.mean(v['B4.rel_std_pct']), 3)} & "
                 f"{f(min(v['B4.rel_std_pct']), 2)} to {f(max(v['B4.rel_std_pct']), 2)} & {f(statistics.mean(v['M07.efficiency']), 3)} & {f(statistics.mean(v['B4.efficiency']), 3)} \\\\")
    tex_table("tab_bake_rows.tex", L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--seeds", type=int, default=10, help="seeds of the main comparison (seeds 1 to 3 feed the other parts)")
    ap.add_argument("--cache", default=None,
                    help="folder of the intermediate holograms (default: <CAOS_TEMP_ROOT>/dinhot-robust-cache)")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--extra", choices=["pointonly"], help="run one part again on the cached holograms and merge it into robust.json")
    ap.add_argument("--emit-only", action="store_true", help="rewrite the macros and tables from an existing robust.json")
    a = ap.parse_args()
    if a.cache is None and not a.emit_only:
        if not os.environ.get("CAOS_TEMP_ROOT"):
            ap.error("set CAOS_TEMP_ROOT (the device's temp root) or pass --cache")
        a.cache = str(Path(os.environ["CAOS_TEMP_ROOT"]) / "dinhot-robust-cache")
    out = Path(a.out)
    if a.extra:
        data = json.loads((out / "robust.json").read_text(encoding="utf-8"))
        t_extra = time.time()
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            data[a.extra] = sorted((f.result() for f in [ex.submit(task_pointonly, sd, a.cache) for sd in (1, 2, 3)]),
                                   key=lambda r: r["seed"])
        data["meta"].setdefault("extra_s", {})[a.extra] = time.time() - t_extra
        data["meta"].setdefault("extra_workers", {})[a.extra] = a.workers
        (out / "robust.json").write_text(json.dumps(data), encoding="utf-8")
    elif a.emit_only:
        data = json.loads((out / "robust.json").read_text(encoding="utf-8"))
    else:
        data = run_all(a)
        (out / "robust.json").write_text(json.dumps(data), encoding="utf-8")
    write_outputs(data, out)
    print("written", out)


if __name__ == "__main__":
    main()
