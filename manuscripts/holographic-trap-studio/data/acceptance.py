#!/usr/bin/env python3
"""Measure the acceptance quantity of every method of the DinHot ladder (M01 to M19, BS-4 and BS-5) and write ``acceptance.json``.

Each ``measure_<id>`` below computes the quantity of its method's gate test, on the same setup, task, seeds and budget as that
test, with the method modules and ``pipeline.model.holo.core`` of the current engine, and returns the numbers and the text of
its row of the acceptance table of the technical report (``extract.py`` reads the file; no number is typed there). The gate
test each function mirrors is named in its docstring and in the ``source`` field of the row. The script measures, it does not
assert a pass (ADR-0069): a number that misses its bar is written as measured.

BS-1 and BS-2 are measured by ``manuscripts/device-aware-flicker-bounded/data/measure.py`` and are not part of this table.
M17 needs the released network, onnxruntime and the held-out file, which the pipeline environment does not have: its row takes
the values from ``data/derived/models/metrics.json``, the committed artifact its gate test reads, and says so.

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/holographic-trap-studio/data/acceptance.py [--workers 6] [--only M01 M06]

Deterministic: every method takes its seed through the portable generator, so a rerun gives the same numbers up to the floating
point of the machine's FFT.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
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
sys.path.insert(0, str(ROOT / "tests" / "methods" / "optim"))      # e3_helpers: plain functions shared by the gate tests

from e3_helpers import (  # noqa: E402
    bin_grid, check_finite_difference, disc_target, lattice_target, line_target, make_setup, quasi_periodic_119,
    ring_target, signal_error, task_10x10, trap_stats,
)
from pipeline.model.holo.core.camera import EmulatedCamera  # noqa: E402
from pipeline.model.holo.core.device import Device, device_focal_field  # noqa: E402
from pipeline.model.holo.core.forward import fft_focal_field, point_trap_fields, trap_fields_from_fft  # noqa: E402
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude  # noqa: E402
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities, uniformity  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import Trap, TrapSet, lattice_3d, square_grid  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.baseline import (  # noqa: E402
    m01_superposition, m02_random_superposition, m03_random_mask, m04_gs, m05_gaa, m06_gsw, m07_phase_fixed_wgs, m08_mraf,
    m19_multiplane,
)
from pipeline.model.holo.methods.beyond import b4_robust as B4  # noqa: E402
from pipeline.model.holo.methods.beyond import b5_pareto as B5  # noqa: E402
from pipeline.model.holo.methods.control import m12_closed_loop, m14_zernike, m15_vortex, m16_rearrangement  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402
from pipeline.model.holo.methods.optim import m09_direct_search as M09  # noqa: E402
from pipeline.model.holo.methods.optim import m10_cg as M10  # noqa: E402
from pipeline.model.holo.methods.optim import m11_wirtinger_adam as M11  # noqa: E402
from pipeline.model.holo.methods.optim import m13_crosstalk_cg as M13  # noqa: E402
from pipeline.model.holo.methods.optim import m18_ot_mraf as M18  # noqa: E402

IDS = ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14", "M15", "M16", "M17",
       "M18", "M19", "BS-4", "BS-5"]

T_BASE, T_OPT, T_CTRL, T_BEYOND = "tests/methods/baseline/", "tests/methods/optim/", "tests/methods/control/", "tests/methods/beyond/"


# ---------------------------------------------------------------- shared fixtures of the gate tests (tests/methods/conftest.py)

def setup256() -> Setup:
    """The live grid: 256 x 256 SLM pixels padded 2, Gaussian beam of the core default (conftest ``setup256``)."""
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)


def setup256_flat() -> Setup:
    return replace(setup256(), beam="flat")


def grid10(setup: Setup) -> TrapSet:
    return square_grid(10, 10, 8 * focal_bin_m(setup) * 1e6)


def ceiling(setup: Setup) -> float:
    """Efficiency ceiling of the Gaussian beam, ``(mean A_j)^2`` (conftest ``ceiling``)."""
    return float(np.mean(input_amplitude(setup)) ** 2)


def evaluate(phi, traps, setup) -> tuple[float, float, float]:
    """Efficiency, uniformity and relative standard deviation (percent) by the point-trap form (conftest ``evaluate``)."""
    i = trap_intensities(point_trap_fields(np.asarray(phi), setup, traps))
    return efficiency(i), uniformity(i), rel_std(i)


# ---------------------------------------------------------------- formatting

def spread(values, nd: int = 3) -> str:
    """``median [min, max]`` of a list."""
    v = [float(x) for x in values]
    return f"{statistics.median(v):.{nd}f} [{min(v):.{nd}f}, {max(v):.{nd}f}]"


def join_and(values, nd: int = 2) -> str:
    """``a, b and c`` of a list of numbers."""
    s = [f"{float(x):.{nd}f}" for x in values]
    return s[0] if len(s) == 1 else ", ".join(s[:-1]) + " and " + s[-1]


def row(mid: str, text: str, seeds: str, source: str, numbers: dict) -> dict:
    return {"id": mid, "text": text, "seeds": seeds, "source": source, "numbers": numbers}


def first_both(history, lo_e: float, lo_u: float):
    """First iteration at which efficiency and uniformity both hold (gate helper of test_m06_gsw.py), None when never."""
    for h in history:
        if h["efficiency"] >= lo_e and h["uniformity"] >= lo_u:
            return h["iteration"]
    return None


def first_below(history, pct: float):
    """First iteration with a relative standard deviation at most ``pct`` (gate helper of test_m07_phase_fixed_wgs.py)."""
    for h in history:
        if h["rel_std"] <= pct:
            return h["iteration"]
    return None


def or_never(x, budget: int) -> str:
    return f"not within {budget}" if x is None else str(x)


# ---------------------------------------------------------------- M01 to M08

def measure_M01() -> dict:
    """test_m01_superposition.py: 10x10 task, 1 iteration, analytic (no seed spread)."""
    s = setup256()
    g = grid10(s)
    e, u, _ = evaluate(m01_superposition.run(s, Target.from_traps(g), budget=Budget(1), rng=Rng(1)).phi, g, s)
    return row("M01", f"efficiency {e:.3f}, uniformity {u:.4f} (deterministic)", "1", T_BASE + "test_m01_superposition.py",
               {"efficiency": e, "uniformity": u})


def measure_M02() -> dict:
    """test_m02_random_superposition.py: 10x10 task, seeds 0 to 5."""
    s = setup256()
    g = grid10(s)
    v = np.array([evaluate(m02_random_superposition.run(s, Target.from_traps(g), budget=Budget(1), rng=Rng(k)).phi, g, s)
                  for k in range(6)])
    return row("M02", f"efficiency {spread(v[:, 0])}, uniformity {spread(v[:, 1])}", "6",
               T_BASE + "test_m02_random_superposition.py", {"efficiency": v[:, 0].tolist(), "uniformity": v[:, 1].tolist()})


def measure_M03() -> dict:
    """test_m03_random_mask.py: 10x10 task at 256 x 256 (seeds 0 to 4) and at the published 768 x 768 (seeds 0 and 1, history)."""
    s = setup256()
    g = grid10(s)
    v = np.array([evaluate(m03_random_mask.run(s, Target.from_traps(g), budget=Budget(1), rng=Rng(k)).phi, g, s)
                  for k in range(5)])
    s768 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=768, pitch_m=12.5e-6, pad=2)
    t768 = square_grid(10, 10, 8 * focal_bin_m(s768) * 1e6)
    h = [m03_random_mask.run(s768, Target.from_traps(t768), budget=Budget(1), rng=Rng(k)).history[0] for k in range(2)]
    e8, u8 = [x["efficiency"] for x in h], [x["uniformity"] for x in h]
    text = (f"256 squared: efficiency {statistics.median(v[:, 0]):.3f}, uniformity {spread(v[:, 1])}; "
            f"768 squared: efficiency {statistics.median(e8):.3f}, uniformity {spread(u8)}")
    return row("M03", text, "5 and 2", T_BASE + "test_m03_random_mask.py",
               {"e256": v[:, 0].tolist(), "u256": v[:, 1].tolist(), "e768": e8, "u768": u8})


def measure_M04() -> dict:
    """test_m04_gs.py: 10x10 task, 30 iterations, seeds 1 to 3, flat beam and Gaussian beam (against its ceiling)."""
    flat, gauss = setup256_flat(), setup256()
    g = grid10(gauss)
    vf = np.array([evaluate(m04_gs.run(flat, Target.from_traps(g), budget=Budget(30), rng=Rng(k)).phi, g, flat)
                   for k in (1, 2, 3)])
    vg = np.array([evaluate(m04_gs.run(gauss, Target.from_traps(g), budget=Budget(30), rng=Rng(k)).phi, g, gauss)
                   for k in (1, 2, 3)])
    c = ceiling(gauss)
    text = (f"flat beam: efficiency {spread(vf[:, 0])}, uniformity {spread(vf[:, 1])}; Gaussian beam: efficiency "
            f"{statistics.median(vg[:, 0]):.3f} against its ceiling {c:.3f}")
    return row("M04", text, "3", T_BASE + "test_m04_gs.py",
               {"flat_efficiency": vf[:, 0].tolist(), "flat_uniformity": vf[:, 1].tolist(),
                "gauss_efficiency": vg[:, 0].tolist(), "gauss_uniformity": vg[:, 1].tolist(), "ceiling": c})


def measure_M05() -> dict:
    """test_m05_gaa.py: 10x10 task, 30 iterations, seeds 1 to 5, GAA against GS at equal iterations."""
    s = setup256()
    g = grid10(s)
    t = Target.from_traps(g)
    gs = np.array([evaluate(m04_gs.run(s, t, budget=Budget(30), rng=Rng(k)).phi, g, s) for k in range(1, 6)])
    ga = np.array([evaluate(m05_gaa.run(s, t, budget=Budget(30), rng=Rng(k)).phi, g, s) for k in range(1, 6)])
    text = (f"uniformity {spread(ga[:, 1])} against {spread(gs[:, 1])} for GS at equal iterations; efficiency "
            f"{statistics.median(ga[:, 0]):.3f} against {statistics.median(gs[:, 0]):.3f}")
    return row("M05", text, "5", T_BASE + "test_m05_gaa.py",
               {"gaa_uniformity": ga[:, 1].tolist(), "gs_uniformity": gs[:, 1].tolist(),
                "gaa_efficiency": ga[:, 0].tolist(), "gs_efficiency": gs[:, 0].tolist()})


def measure_M06() -> dict:
    """test_m06_gsw.py: first iteration at which both hold on the 10x10 task (flat 0.9/0.9 within 15, Gaussian 0.9 of the ceiling
    and 0.9 within 20) and on the 3 x 3 x 3 lattice (0.9/0.98 within 100), seeds 1 to 3."""
    flat, gauss = setup256_flat(), setup256()
    g = grid10(gauss)
    c = ceiling(gauss)
    f_flat, u10, f_gauss, f_lat = [], [], [], []
    for k in (1, 2, 3):
        h = m06_gsw.run(flat, Target.from_traps(g), budget=Budget(15), rng=Rng(k)).history
        f_flat.append(first_both(h, 0.9, 0.9))
        u10.append(h[9]["uniformity"])
        h = m06_gsw.run(gauss, Target.from_traps(g), budget=Budget(20), rng=Rng(k)).history
        f_gauss.append(first_both(h, 0.9 * c, 0.9))
    lat = lattice_3d(3, 3, 3, 8 * focal_bin_m(gauss) * 1e6, 40e3)
    for k in (1, 2, 3):
        h = m06_gsw.run(gauss, Target.from_traps(lat), budget=Budget(100), rng=Rng(k)).history
        f_lat.append(first_both(h, 0.9, 0.98))
    text = (f"flat beam: efficiency and uniformity both at 0.9 after {join_and([x for x in f_flat if x], 0)} iterations "
            f"(median uniformity {statistics.median(u10):.3f} at 10); Gaussian beam: {join_and([x for x in f_gauss if x], 0)}; "
            f"3 x 3 x 3 lattice (0.9 and 0.98): {join_and([x for x in f_lat if x], 0)}; budgets 15, 20 and 100")
    return row("M06", text, "3", T_BASE + "test_m06_gsw.py (and test_m06_against_slmsuite.py, notebook venv)",
               {"first_both_flat": f_flat, "uniformity_at_10_flat": u10, "first_both_gaussian": f_gauss, "first_both_lattice": f_lat})


def measure_M07() -> dict:
    """test_m07_phase_fixed_wgs.py: 50 x 30 array, budget 150, FFT form, seeds 1 and 2, phase fixed after 60, against M06;
    and the literal Kim setting (fixed after 12, budget 40, seed 1)."""
    s = setup256()
    tr = square_grid(50, 30, 8 * focal_bin_m(s) * 1e6)
    t = Target.from_traps(tr)
    ia, ib, eff = [], [], []
    for k in (1, 2):
        a = m07_phase_fixed_wgs.run(s, t, budget=Budget(150), rng=Rng(k), n_fix=60)
        b = m06_gsw.run(s, t, budget=Budget(150), rng=Rng(k), form="fft")
        ia.append(first_below(a.history, 0.5))
        ib.append(first_below(b.history, 0.5))
        eff.append(a.history[-1]["efficiency"])
    kim = m07_phase_fixed_wgs.run(s, t, budget=Budget(40), rng=Rng(1))
    stall = min(h["rel_std"] for h in kim.history)
    text = (f"50 x 30 array to 0.5 percent in {join_and([x for x in ia if x], 0)} iterations against "
            f"{join_and([or_never(x, 150) for x in ib], 0)} for M06 (phase fixed after 60; efficiency {join_and(eff, 2)}); "
            f"with the source value of 12 it stalls at {stall:.2f} percent")
    return row("M07", text, "2", T_BASE + "test_m07_phase_fixed_wgs.py (and test_m07_against_slmsuite.py, notebook venv)",
               {"iterations_m07": ia, "iterations_m06": ib, "efficiency_m07": eff, "kim_stall_percent": stall})


def measure_M08() -> dict:
    """test_m08_mraf.py: disc, ring and line targets, 45 iterations, starts of 16 and 24 waves, MRAF against GS (worst of the two starts)."""
    s = setup256()
    n = s.n_fft
    yy, xx = np.indices((n, n))
    y, x = yy - n // 2, xx - n // 2
    r = np.hypot(y, x)

    def dilate(mask, rad=8):
        out = mask.copy()
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                out |= np.roll(np.roll(mask, dy, 0), dx, 1)
        return out

    shapes = {"disc": r < 60, "ring": (r > 45) & (r < 75), "line": (np.abs(x) < 120) & (np.abs(y) < 20)}
    ratios, eg, em = {}, {}, {}
    for kind, shape in shapes.items():
        t = Target.from_field(shape.astype(float), dilate(shape, 8))
        rr, g_, m_ = [], [], []
        for w in (16.0, 24.0):
            g = m04_gs.run(s, t, budget=Budget(45), rng=Rng(1), start_waves=w)
            q = m08_mraf.run(s, t, budget=Budget(45), rng=Rng(1), start_waves=w)
            rr.append(g.history[-1]["error"] / q.history[-1]["error"])
            g_.append(g.history[-1]["efficiency"])
            m_.append(q.history[-1]["efficiency"])
        ratios[kind], eg[kind], em[kind] = rr, g_, m_
    low = [min(ratios[k]) for k in ("disc", "ring", "line")]
    e_all_g = [v for k in eg for v in eg[k]]
    e_all_m = [v for k in em for v in em[k]]
    text = (f"signal-region error {low[0]:.1f} (disc), {low[1]:.1f} (ring) and {low[2]:.1f} (bar) times below GS at the worse of "
            f"two starts; efficiency {min(e_all_m):.3f} to {max(e_all_m):.3f} against {min(e_all_g):.3f} to {max(e_all_g):.3f}")
    return row("M08", text, "2 starts", T_BASE + "test_m08_mraf.py",
               {"ratio_disc": ratios["disc"], "ratio_ring": ratios["ring"], "ratio_line": ratios["line"],
                "efficiency_mraf": e_all_m, "efficiency_gs": e_all_g})


# ---------------------------------------------------------------- M09 to M11, M13, M18

def measure_M09() -> dict:
    """test_m09_direct_search.py: 10x10 task, default sweeps, seeds 1 and 2; 119-trap quasi-periodic set, seed 1."""
    s = make_setup(256)
    g = task_10x10(s)
    st = [trap_stats(M09.run(s, Target.from_traps(g), budget=Budget(M09.DEFAULT_SWEEPS), rng=Rng(k)).phi, s, g) for k in (1, 2)]
    q = quasi_periodic_119(s)
    sq = trap_stats(M09.run(s, Target.from_traps(q), budget=Budget(M09.DEFAULT_SWEEPS), rng=Rng(1)).phi, s, q)
    text = (f"uniformity {join_and([a[1] for a in st], 4)} (efficiency {join_and([a[0] for a in st], 2)}); "
            f"{len(q)} quasi-periodic traps at {sq[2]:.3f} percent rms")
    return row("M09", text, "2 and 1", T_OPT + "test_m09_direct_search.py",
               {"uniformity": [a[1] for a in st], "efficiency": [a[0] for a in st], "quasi_rel_std_percent": sq[2],
                "quasi_traps": len(q)})


def measure_M10() -> dict:
    """test_m10_cg.py: gradient against finite differences (shaped target and traps, t = 2 and 4, 6 directions, 16 pixel grid);
    4 x 4 square lattice on the 64 pixel grid, default iterations, seeds 1 and 2."""
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, guard=2.0)
    errs = []
    for t in (2, 4):
        cost = C.FieldCost(s, amp, mask, t=t, efficiency=0.4)
        phi = Rng(5).phases(256).reshape(16, 16)
        errs.append(check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(1), n_dirs=6))
    traps = bin_grid(s, 3, 3, 12)
    for t in (2, 4):
        cost = C.TrapCost(s, traps, t=t, efficiency=0.8)
        phi = Rng(6).phases(256).reshape(16, 16)
        errs.append(check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(2), n_dirs=6))
    s64 = make_setup(64)
    a2, m2 = lattice_target(s64, 4, 16.0, 3.0)
    lat = []
    for k in (1, 2):
        res = M10.run(s64, Target.from_field(a2, m2), budget=Budget(M10.DEFAULT_LATTICE_ITERATIONS), rng=Rng(k), t=2)
        lat.append(100 * signal_error(fft_focal_field(res.phi, s64), a2, m2)[0])
    text = (f"analytic gradient within {max(errs):.1e} of finite differences; square lattice error {join_and(lat, 2)} percent")
    return row("M10", text, "2", T_OPT + "test_m10_cg.py",
               {"gradient_worst_rel_error": max(errs), "gradient_errors": errs, "lattice_error_percent": lat})


def measure_M11() -> dict:
    """test_m11_wirtinger_adam.py: 10x10 task, 30 iterations, seeds 1 to 3, relative standard deviation against GS."""
    s = make_setup(256)
    g = task_10x10(s)
    adam, gs = [], []
    for k in (1, 2, 3):
        res = M11.run(s, Target.from_traps(g), budget=Budget(30), rng=Rng(k))
        adam.append(trap_stats(res.phi, s, g)[2])
        phi, _ = G.weighted_gs(s, g, 30, Rng(k), variant="gs")
        gs.append(trap_stats(phi, s, g)[2])
    text = f"relative standard deviation {join_and(adam, 2)} percent against {join_and(gs, 2)} for GS at 30 iterations"
    return row("M11", text, "3", T_OPT + "test_m11_wirtinger_adam.py", {"adam_rel_std": adam, "gs_rel_std": gs})


def measure_M13() -> dict:
    """test_m13_crosstalk_cg.py: disc of 24 bins radius on the 64 pixel grid, crosstalk device, 100 iterations, seed 1, M13 against M10."""
    dev = Device(crosstalk=(1.24, 1.80), upsample=3)
    s = make_setup(64)
    amp, mask = disc_target(s, 24.0, 3.0)
    out = {}
    for name, mod, d in (("m10", M10, None), ("m13", M13, dev)):
        res = mod.run(s, Target.from_field(amp, mask), device=d, budget=Budget(100), rng=Rng(1), t=2)
        out[name] = signal_error(device_focal_field(res.phi, s, dev, None), amp, mask)
    text = (f"error {out['m13'][0]:.3f} (efficiency {out['m13'][1]:.3f}) against {out['m10'][0]:.3f} ({out['m10'][1]:.3f}) for "
            f"M10 without the device model, large disc on the crosstalk device")
    return row("M13", text, "1", T_OPT + "test_m13_crosstalk_cg.py",
               {"m13_error": out["m13"][0], "m13_efficiency": out["m13"][1], "m10_error": out["m10"][0],
                "m10_efficiency": out["m10"][1]})


def measure_M18() -> dict:
    """test_m18_ot_mraf.py: disc, ring and line at the live size (64 pixel SLM, random starts 5 and 6, 100 iterations); disc and
    ring at the baked size (128 pixel SLM, random start 5). The OT start is deterministic."""
    def tgt(setup, name):
        sc = setup.n_pix / 64
        return {"disc": lambda: disc_target(setup, 24 * sc, 3 * sc), "ring": lambda: ring_target(setup, 22 * sc, 8 * sc, 2 * sc),
                "line": lambda: line_target(setup, 50 * sc, 8 * sc, 2 * sc)}[name]()

    def pair(setup, name, seeds):
        amp, mask = tgt(setup, name)
        ot = M18.run(setup, Target.from_field(amp, mask), budget=Budget(100), rng=Rng(1))
        e_ot = signal_error(ot.fields, amp, mask)
        rand = []
        for sd in seeds:
            init = Rng(sd).phases(setup.n_pix**2).reshape(setup.n_pix, setup.n_pix)
            r = M18.run(setup, Target.from_field(amp, mask), budget=Budget(100), rng=Rng(1), init=init)
            rand.append(signal_error(r.fields, amp, mask)[0])
        return e_ot, rand

    live = {k: pair(make_setup(64), k, (5, 6)) for k in ("disc", "ring", "line")}
    baked = {k: pair(make_setup(128), k, (5,)) for k in ("disc", "ring")}
    text = (f"signal-region error {live['disc'][0][0]:.4f} (disc), {live['ring'][0][0]:.4f} (ring) and {live['line'][0][0]:.4f} "
            f"(line) against {min(live['disc'][1]):.3f}, {min(live['ring'][1]):.3f} and {min(live['line'][1]):.3f} for MRAF "
            f"from a random start (the better of two); baked size: {baked['disc'][0][0]:.4f} (disc) and "
            f"{baked['ring'][0][0]:.4f} (ring) against {baked['disc'][1][0]:.3f} and {baked['ring'][1][0]:.3f}")
    nums = {f"live_{k}_ot": v[0][0] for k, v in live.items()} | {f"live_{k}_random": v[1] for k, v in live.items()}
    nums |= {f"baked_{k}_ot": v[0][0] for k, v in baked.items()} | {f"baked_{k}_random": v[1] for k, v in baked.items()}
    return row("M18", text, "2 and 1", T_OPT + "test_m18_ot_mraf.py", nums)


# ---------------------------------------------------------------- M12, M14 to M16

def measure_M12() -> dict:
    """test_m12_closed_loop.py: Nogrette setting (gain error 19 percent rms, gain 0.7, 20 iterations) and Kim setting (22 percent
    rms, square-root update, three phase-fixed steps), seeds 1 and 2."""
    s = setup256()
    g = grid10(s)
    t = Target.from_traps(g)
    n0, n1, k0, k1 = [], [], [], []
    for k in (1, 2):
        cam = EmulatedCamera(seed=k, gain_rms=0.19, noise_rms=0.0, blur_bins=0.0, rolloff=False)
        r = m12_closed_loop.run(s, t, budget=Budget(20), rng=Rng(k), camera=cam, gain=0.7)
        n0.append(r.meta["open_loop_rel_std"])
        n1.append(r.history[-1]["rel_std"])
        cam = EmulatedCamera(seed=k, gain_rms=0.22, rolloff=False)
        r = m12_closed_loop.run(s, t, budget=Budget(3), rng=Rng(k), camera=cam, variant="kim")
        k0.append(r.meta["open_loop_rel_std"])
        k1.append(r.history[-1]["rel_std"])
    text = (f"emulated camera loop: open-loop {join_and(n0, 1)} percent to {join_and(n1, 2)} percent in 20 iterations; "
            f"{join_and(k0, 1)} percent to {join_and(k1, 2)} percent in three phase-fixed steps")
    return row("M12", text, "2", T_CTRL + "test_m12_closed_loop.py",
               {"nogrette_open_loop": n0, "nogrette_closed": n1, "kim_open_loop": k0, "kim_closed": k1})


def injected_set(seed: int) -> np.ndarray:
    """Noll 4 to 11, random signs, amplitudes 0.06 to 0.12 waves (test_m14_zernike.py ``injected_set``)."""
    rg = Rng(1000 + seed)
    c = np.zeros(11)
    for j in range(4, 12):
        c[j - 1] = (0.06 + 0.06 * rg.uniform()) * (1.0 if rg.uniform() < 0.5 else -1.0)
    return c


def measure_M14() -> dict:
    """test_m14_zernike.py: sensorless modal recovery of Noll modes 4 to 11, budget 6, seeds 1 to 3, worst per-mode relative error."""
    s = setup256()
    t = Target.from_traps(grid10(s))
    worst = []
    for k in (1, 2, 3):
        inj = injected_set(k)
        r = m14_zernike.run(s, t, budget=Budget(6), rng=Rng(k), mode="recover", injected=inj)
        est = r.meta["coefficients"]
        worst.append(float(np.max(np.abs(est[3:11] - inj[3:11]) / np.abs(inj[3:11]))))
    return row("M14", f"worst per-mode relative error {spread(worst)} over Noll modes 4 to 11", "3",
               T_CTRL + "test_m14_zernike.py", {"worst_relative_error": worst})


def measure_M15() -> dict:
    """test_m15_vortex.py: isolated vortices of charge 1, 2, 3 and -2, seeds 1 and 2, budget 5; maximum deviation of the ring phase
    from the l theta line and the winding error."""
    s = setup256()
    mx, wind = [], []
    for charge in (1, 2, 3, -2):
        tr = TrapSet([Trap(0, 0.0, 0.0, 0.0, 1.0, charge)])
        for k in (1, 2):
            r = m15_vortex.run(s, Target.from_traps(tr), budget=Budget(5), rng=Rng(k))
            prof = m15_vortex.ring_phase_profile(r.phi, s, tr.traps[0])
            mx.append(float(prof["max_error"]))
            wind.append(abs(float(prof["winding"]) - 2 * math.pi * charge))
    exact = "winding error below the 1e-9 rad of the arithmetic" if max(wind) < 1e-9 else f"winding error at most {max(wind):.1e} rad"
    text = (f"ring phase winds by 2 pi l ({exact}) with a maximum error of {spread(mx)} rad "
            f"(isolated vortices of charge 1, 2, 3 and -2)")
    return row("M15", text, "2 per charge", T_CTRL + "test_m15_vortex.py", {"max_error": mx, "winding_error": wind})


def measure_M16() -> dict:
    """test_m16_rearrangement.py: crossings of alpha 1.5 on 7x7 to 3x3 over 60 random loadings; worst moving-trap intensity ratio
    of the linear phase interpolation over 5 loadings (budget 30)."""
    s = setup256()
    b = focal_bin_m(s)
    n = 7
    sites = [((i - (n - 1) / 2) * 8 * b, (j - (n - 1) / 2) * 8 * b) for j in range(n) for i in range(n)]
    targets = TrapSet(Trap(k, (i - 1) * 8 * b, (j - 1) * 8 * b) for k, (j, i) in enumerate(itertools.product(range(3), range(3))))

    def loading(seed):
        pick = np.random.default_rng(seed).choice(len(sites), size=21, replace=False)
        return TrapSet(Trap(k, *sites[p]) for k, p in enumerate(sorted(pick)))

    crossings = 0
    for seed in range(60):
        atoms = loading(seed)
        f = m16_rearrangement.assign(np.c_[targets.x_m, targets.y_m] / b, np.c_[atoms.x_m, atoms.y_m] / b, alpha=1.5)
        starts = np.c_[atoms.x_m, atoms.y_m][f] / b
        crossings += m16_rearrangement.count_crossings(starts, np.c_[targets.x_m, targets.y_m] / b)
    worst = []
    for seed in range(5):
        atoms = loading(seed)
        r = m16_rearrangement.run(s, Target.from_traps(targets), budget=Budget(30), rng=Rng(seed + 1), atoms=atoms)
        worst.append(float(r.meta["min_ratio"][r.meta["moved"]].min()))
    text = (f"{crossings} path crossings in 60 loadings; moving traps keep {spread(worst)} of their mean intensity "
            f"(worst moving trap of each of 5 loadings)")
    return row("M16", text, "60 loadings", T_CTRL + "test_m16_rearrangement.py",
               {"crossings": crossings, "worst_ratio": worst})


# ---------------------------------------------------------------- M17, M19

def measure_M17() -> dict:
    """test_m17_cgh_net.py: the multi-plane network refined by M19 against M19 at the same wall-clock. Its gate needs the released
    graph, onnxruntime and the held-out file, which the pipeline environment lacks: the values are those of the committed artifact
    ``data/derived/models/metrics.json`` that the gate test reads (it checks ``held_out_n`` of that file)."""
    doc = json.loads((ROOT / "data" / "derived" / "models" / "metrics.json").read_text(encoding="utf-8"))
    e = doc["slots"]["cgh-net"]
    a, n = e["accuracy_vs_gs"], e["held_out_n"]
    text = (f"three-plane network refined by M19: median accuracy ratio {a['median']:.3f} (quartiles {a['q1']:.3f} and "
            f"{a['q3']:.3f}) on {n} held-out volumes; taken from the committed metrics.json, not remeasured here")
    return row("M17", text, f"{n} volumes", "tests/learned/test_m17_cgh_net.py; data/derived/models/metrics.json",
               {"median": a["median"], "q1": a["q1"], "q3": a["q3"], "held_out_n": n})


def measure_M19() -> dict:
    """test_m19_multiplane.py: three planes of 5 x 5 traps (plane step 40 mm, spacing 6 voxels), budget 20, seeds 1 and 2; plane mean
    over the mean of all traps."""
    s = setup256()
    dz = 40e-3
    vox = s.pad * focal_bin_m(s)
    base = square_grid(5, 5, 6 * vox * 1e6)
    traps = []
    for p, (z, sx, sy) in enumerate([(-dz, 0, 0), (0.0, 3, 3), (dz, -3, 3)]):
        for t in base:
            traps.append(Trap(p * len(base) + t.id, t.x_m + sx * vox, t.y_m + sy * vox, z))
    tr = TrapSet(traps)
    ratios = []
    for k in (1, 2):
        r = m19_multiplane.run(s, Target.from_traps(tr), budget=Budget(20), rng=Rng(k), dz_m=dz)
        inten = np.abs(r.fields) ** 2
        z = r.meta["snapped"].z_m
        mean_all = inten.mean()
        ratios.append([float(inten[z == zz].mean() / mean_all) for zz in np.unique(z)])
    text = "plane means over overall mean " + " and ".join(join_and(v, 3) for v in ratios) + " on three planes"
    return row("M19", text, "2", T_BASE + "test_m19_multiplane.py", {"plane_ratios": ratios})


# ---------------------------------------------------------------- BS-4, BS-5

def measure_BS4() -> dict:
    """test_b4_robust.py: 10x10 task, 200-sample aberration ensemble (seed 999), B4 at 40 iterations against the phase-fixed WGS
    of the GS family at 30 (p95 of the relative standard deviation and mean efficiency), on seeds 1 to 3 (the SDD row's median);
    pointing ensemble of 20 samples at 0.15 bin with B4 at 3 iterations and q = 2 on seed 1 (a finite-ratio check in the test, a
    measured negative here)."""
    s = make_setup(256)
    g = task_10x10(s)
    t = Target.from_traps(g)
    ratios, effs, sb4, sm7 = [], [], [], []
    for seed in (1, 2, 3):
        base, _ = G.weighted_gs(s, g, 30, Rng(seed), variant="pfwgs")
        res = B4.run(s, t, budget=Budget(40), rng=Rng(seed), pointing_bins=0.0)
        nom = B4.ensemble_stats(s, base, g, pointing_bins=0.0)
        rob = B4.ensemble_stats(s, res.phi, g, pointing_bins=0.0)
        ratios.append(nom["sigma_p95"] / rob["sigma_p95"])
        effs.append(rob["efficiency_mean"] / nom["efficiency_mean"])
        sb4.append(rob["sigma_p95"])
        sm7.append(nom["sigma_p95"])
        if seed == 1:
            base1 = base
    res_p = B4.run(s, t, budget=Budget(3), rng=Rng(1), q=2, pointing_bins=0.15)
    nom_p = B4.ensemble_stats(s, base1, g, n=20, pointing_bins=0.15)
    rob_p = B4.ensemble_stats(s, res_p.phi, g, n=20, pointing_bins=0.15)
    ratio_p = nom_p["sigma_p95"] / rob_p["sigma_p95"]
    med = statistics.median(ratios)
    text = (f"95th percentile of the relative standard deviation a median {med:.3f} times below M07 ({min(ratios):.2f} to "
            f"{max(ratios):.2f}) over a 200-sample aberration ensemble, at a median {statistics.median(effs):.3f} of its efficiency; "
            f"pointing errors {ratio_p:.2f} times (seed 1)")
    return row("BS-4", text, "3 (pointing 1)", T_BEYOND + "test_b4_robust.py",
               {"ratio": ratios, "eff_ratio": effs, "sigma_p95_b4": sb4, "sigma_p95_m07": sm7, "pointing_ratio": ratio_p,
                "pointing_sigma_p95_b4": rob_p["sigma_p95"], "pointing_sigma_p95_m07": nom_p["sigma_p95"]})


def measure_BS5() -> dict:
    """test_b5_pareto.py: 10x10 task, seed 1; hypervolume of the continuation front (15 iterations, 20 lambdas) against the points of
    GS, GAA, GSW (GS family, 30 iterations) and one sweep of M09; fronts that dominate M04 and M05."""
    s = make_setup(256)
    g = task_10x10(s)
    base = {}
    for name, variant in (("M04", "gs"), ("M05", "gaa"), ("M06", "gsw")):
        phi, _ = G.weighted_gs(s, g, 30, Rng(1), variant=variant)
        base[name] = trap_stats(phi, s, g)[:2]
    ds = M09.run(s, Target.from_traps(g), budget=Budget(1), rng=Rng(1))
    base["M09"] = trap_stats(ds.phi, s, g)[:2]
    t0 = time.perf_counter()
    res = B5.run(s, Target.from_traps(g), budget=Budget(15), rng=Rng(1))
    elapsed = time.perf_counter() - t0
    front = res.meta["front"][:, :2]
    hv_base = B5.hypervolume(np.array(list(base.values())))
    dom = {n: int(np.sum((front[:, 0] >= base[n][0]) & (front[:, 1] > base[n][1]))) for n in ("M04", "M05")}
    text = (f"hypervolume {res.meta['hypervolume']:.4f} against {hv_base:.4f} for the union of the M04, M05, M06 and M09 points; "
            f"{dom['M04']} front points dominate M04 and {dom['M05']} dominate M05")
    return row("BS-5", text, "1", T_BEYOND + "test_b5_pareto.py",
               {"hypervolume": float(res.meta["hypervolume"]), "hypervolume_base": float(hv_base), "dominating_m04": dom["M04"],
                "dominating_m05": dom["M05"], "front_seconds": elapsed})


def _plain(o):
    """JSON form of the numpy scalars and arrays that a row's numbers may hold."""
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serializable: {type(o)}")


MEASURE = {mid: globals()["measure_" + mid.replace("-", "")] for mid in IDS}


def _run(mid: str) -> dict:
    t0 = time.perf_counter()
    r = MEASURE[mid]()
    r["measure_seconds"] = round(time.perf_counter() - t0, 1)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=6, help="processes (each id is independent; results do not depend on it)")
    ap.add_argument("--only", nargs="*", choices=IDS, help="measure these ids only (the output then holds only them)")
    ap.add_argument("--out", type=Path, default=HERE / "acceptance.json")
    args = ap.parse_args()
    ids = args.only or IDS
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(_run, ids))
    doc = {"schema": "dinhot.manuscript-acceptance/v1",
           "note": "Measured by acceptance.py on the engine of this commit; each row mirrors the gate test named in its source.",
           "rows": rows}
    args.out.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=_plain) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['id']:5s} {r['measure_seconds']:7.1f}s  {r['text']}")
    print(f"wrote {args.out} in {time.perf_counter() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
