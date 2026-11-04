#!/usr/bin/env python3
"""Measure the efficiency-uniformity Pareto front by continuation of a weighted cost (the proposed method of this
manuscript) and write ``b5.json``, ``b5_numbers.tex`` and the table files.

The method runs here with the real engine module ``data-pipeline/pipeline/model/holo/methods/beyond/b5_pareto.py`` on the
task of its acceptance test (a 10 x 10 lattice of equal traps, 8 focal bins apart, a 256 x 256 pixel SLM padded 2, a
Gaussian input beam, 850 nm, focal length 250 mm, pitch 12.5 um; ``tests/methods/optim/e3_helpers.py``), over more seeds
than the test uses. The published methods it is compared with are run by the same engine on the same task and seeds
(``methods/optim/_gs_family.py``, which runs the loop of each ladder method, and ``m09_direct_search``). The committed
benchmark ``data/derived/benchmark/results.json`` and the committed bake ``data-pipeline/pipeline/cases/measured_ranges.json``
are read, never re-run. Nothing in the text of the manuscript is typed: every number comes from ``b5.json`` through the
macros of ``b5_numbers.tex`` and the table files.

Parts (``--parts``): ``main`` (the front and the published points, per seed), ``rivals`` (the one-parameter fronts of the
published methods), ``ablation`` (twelve variants of the front on the first ``--seeds-abl`` seeds), ``identity`` (the
algebraic identity and the bound of the Theory section, checked numerically), ``timing`` (the default front timed alone),
``stored`` (the benchmark and the bake), ``diagnostic`` (the loss of the published holograms against the front's, per weight).
``--macros-only`` rewrites the macro and table files from an existing ``b5.json``; ``--only-variants a,b`` runs only those ablation
variants and merges them into it (the thirteenth variant, ``start_gsw100``, was added this way).

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/efficiency-uniformity-front/data/measure.py [--seeds 8] [--seeds-abl 5]

Deterministic given the seeds (the engine's portable generator); the wall-clock times differ between runs and machines.
"""
from __future__ import annotations

import os

# one BLAS thread per worker: the front is timed alone in the ``timing`` part, the other parts only need the values
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ProcessPoolExecutor  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.model.holo.core.forward import point_trap_fields  # noqa: E402
from pipeline.model.holo.core.geometry import Setup, focal_bin_m  # noqa: E402
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities, uniformity  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import TrapSet, square_grid  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.beyond import b5_pareto as B5  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402
from pipeline.model.holo.methods.optim import m09_direct_search as M09  # noqa: E402

# two-sided 95 percent quantiles of Student's t distribution by degrees of freedom
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
       11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 19: 2.093}

BASE_ITERS = 30          # iterations of the published points (the acceptance test)
CG_ITERS = 15            # conjugate-gradient iterations per value of lambda (the acceptance test)
N_LAMBDA = B5.DEFAULT_LAMBDAS
WARM = B5.DEFAULT_WARM
REFS = {"origin": (0.0, 0.0), "e05": (0.5, 0.0), "e07": (0.7, 0.0)}   # reference points of the hypervolume sensitivity


# ------------------------------------------------------------------------------------------------ the task

def make_setup(n_pix: int = 256, pad: int = 2) -> Setup:
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n_pix, pitch_m=12.5e-6, pad=pad,
                 beam="gaussian")


def bin_grid(setup: Setup, nx: int, ny: int, spacing_bins: float) -> TrapSet:
    return square_grid(nx, ny, spacing_bins * focal_bin_m(setup) * 1e6)


def task():
    s = make_setup(256)
    return s, bin_grid(s, 10, 10, 8)


def scores(phi: np.ndarray, setup: Setup, traps: TrapSet) -> tuple[float, float, float]:
    """Efficiency, uniformity and relative standard deviation (percent) of a hologram on the ideal device."""
    v = point_trap_fields(phi, setup, traps)
    iw = trap_intensities(v, traps.weight)
    return efficiency(trap_intensities(v)), uniformity(iw), rel_std(iw)


def stats(values) -> dict:
    """Mean, sample standard deviation, the two-sided 95 percent t interval of the mean, median and range."""
    v = [float(x) for x in values]
    n = len(v)
    mean = statistics.fmean(v)
    sd = statistics.stdev(v) if n > 1 else 0.0
    half = T95.get(n - 1, 1.96) * sd / math.sqrt(n) if n > 1 else float("nan")
    return {"n": n, "mean": mean, "sd": sd, "ci_lo": mean - half, "ci_hi": mean + half, "median": statistics.median(v),
            "min": min(v), "max": max(v)}


# ------------------------------------------------------------------------------------------------ costs and the front

class RawCost(B5._FrontCost):
    """The form of the research record, without the two divisions: ``(1 - lam) sum (I - T)^2 - lam sum I``."""

    def value_grad(self, phi: np.ndarray):
        v, cache = self.fwd.fields(phi)
        i = np.abs(v) ** 2
        d = i - self.target
        lam = self.lam
        value = (1.0 - lam) * float(np.sum(d ** 2)) - lam * float(np.sum(i))
        return value, self.fwd.adjoint((2.0 * (1.0 - lam) * d - lam) * v, cache), v


def schedule(name: str, n: int, e0: float) -> np.ndarray:
    """The values of lambda: ``linear`` (the default), ``quadratic`` (dense near 0) and ``target`` (equal steps of the
    total light the shifted target asks for, from ``e0`` to 1, Proposition 1 of the Theory section)."""
    k = np.linspace(0.0, 1.0, n)
    if name == "linear":
        return k
    if name == "quadratic":
        return k ** 2
    if name == "target":
        r = (1.0 / e0 - 1.0) * k          # relative excess of the target total over e0, 0 to the physical ceiling 1
        return 2.0 * r / (1.0 + 2.0 * r)
    raise ValueError(name)


def front_run(seed: int, *, n_lambda: int = N_LAMBDA, cg: int = CG_ITERS, sched: str = "linear", warm_start: bool = True,
              start: str = "pfwgs", raw: bool = False) -> dict:
    """The loop of ``B5.run`` with the choices the ablation varies; the default arguments reproduce ``B5.run``."""
    setup, traps = task()
    rng = Rng(seed)
    t0 = time.perf_counter()
    if start == "pfwgs":
        phi0, _ = G.weighted_gs(setup, traps, WARM, rng, variant="pfwgs")
    elif start == "gs":
        phi0, _ = G.weighted_gs(setup, traps, WARM, rng, variant="gs")
    elif start == "random":
        phi0 = G.sr_start(setup, traps, rng)
    elif start == "gsw100":
        phi0, _ = G.weighted_gs(setup, traps, 100, rng, variant="gsw")
    else:
        raise ValueError(start)
    fwd = C.TrapForward(setup, traps)
    v, _ = fwd.fields(phi0)
    e0 = efficiency(trap_intensities(v))
    cost = (RawCost if raw else B5._FrontCost)(setup, traps, e0)
    ref_cost = B5._FrontCost(setup, traps, e0)          # the loss objectives E and S, always in the normalized form
    lambdas = schedule(sched, n_lambda, e0)
    phi = phi0
    rows, phis = [], []
    for lam in lambdas:
        cost.lam = float(lam)
        res = C.cg_minimize(cost.value_grad, phi if warm_start else phi0, cg)
        phi = res.x
        v, _ = fwd.fields(phi)
        i = np.abs(v) ** 2
        iw = trap_intensities(v, traps.weight)
        e_loss = float(np.sum((i - ref_cost.target) ** 2)) / ref_cost.tt
        rows.append([float(lam), efficiency(trap_intensities(v)), uniformity(iw), rel_std(iw), e_loss, float(np.sum(i)) / e0])
        phis.append(phi)
    front = np.array(rows)
    pareto = B5.pareto_indices(front[:, 1:3])
    return {"seed": seed, "e0": e0, "lambda": front[:, 0].tolist(), "e": front[:, 1].tolist(), "u": front[:, 2].tolist(),
            "sigma": front[:, 3].tolist(), "E": front[:, 4].tolist(), "S": front[:, 5].tolist(), "pareto": pareto,
            "hv": B5.hypervolume(front[:, 1:3]), "hv_refs": {k: B5.hypervolume(front[:, 1:3], r) for k, r in REFS.items()},
            "knee": int(np.argmax(front[:, 1] * front[:, 2])), "seconds": time.perf_counter() - t0}


def hv_of(points, ref=(0.0, 0.0)) -> float:
    return B5.hypervolume(np.asarray(points, dtype=np.float64).reshape(-1, 2), ref)


def published_points(seed: int) -> dict:
    """The points of the published methods on the task, one seed: the four of the acceptance criterion at 30 iterations
    (direct search with one sweep) and phase-fixed WGS, each scored on the ideal device."""
    setup, traps = task()
    pts = {}
    for name, variant in (("M04", "gs"), ("M05", "gaa"), ("M06", "gsw"), ("M07", "pfwgs")):
        phi, _ = G.weighted_gs(setup, traps, BASE_ITERS, Rng(seed), variant=variant)
        pts[name] = list(scores(phi, setup, traps)[:2])
    t0 = time.perf_counter()
    ds = M09.run(setup, Target.from_traps(traps), budget=Budget(1), rng=Rng(seed))
    pts["M09"] = list(scores(ds.phi, setup, traps)[:2])
    pts["M09_seconds"] = time.perf_counter() - t0
    return pts


def rival_fronts(seed: int) -> dict:
    """The one-parameter fronts the published methods give on the same task: the iterates of weighted GS and of
    phase-fixed WGS over 100 iterations, and the sweep of the adaptive additive exponent from 0 to 1 at 30 iterations."""
    setup, traps = task()
    out = {}
    for name, variant in (("gsw_path", "gsw"), ("pfwgs_path", "pfwgs")):
        _, hist = G.weighted_gs(setup, traps, 100, Rng(seed), variant=variant)
        out[name] = [[float(h["efficiency"]), float(h["uniformity"])] for h in hist]
    sweep = []
    for a in np.linspace(0.0, 1.0, 11):
        phi, _ = G.weighted_gs(setup, traps, BASE_ITERS, Rng(seed), variant="gaa", alpha=float(a))
        sweep.append(list(scores(phi, setup, traps)[:2]))
    out["gaa_sweep"] = sweep
    return out


# ------------------------------------------------------------------------------------------------ workers

ABLATION = {
    "default": {},
    "n_lambda_5": {"n_lambda": 5}, "n_lambda_10": {"n_lambda": 10}, "n_lambda_40": {"n_lambda": 40},
    "cg_5": {"cg": 5}, "cg_30": {"cg": 30},
    "quadratic": {"sched": "quadratic"}, "target": {"sched": "target"},
    "cold": {"warm_start": False},
    "start_gs": {"start": "gs"}, "start_random": {"start": "random"}, "start_gsw100": {"start": "gsw100"},
    "raw_loss": {"raw": True},
}


ABL_KEY = {"default": "Default", "n_lambda_5": "NLamFive", "n_lambda_10": "NLamTen", "n_lambda_40": "NLamForty",
           "cg_5": "CgFive", "cg_30": "CgThirty", "quadratic": "Quad", "target": "Target", "cold": "Cold",
           "start_gs": "StartGs", "start_random": "StartRand", "start_gsw100": "StartGswH", "raw_loss": "Raw"}


def diagnose(seed: int, front: dict) -> dict:
    """Is a hologram of a published method better, on the loss itself, than the front point at some weight? The holograms of
    weighted GS and of phase-fixed WGS after 30 and 100 iterations are scored on the normalized error E and the light S of the
    seed's front (same target, same e0), and their loss at each weight of the front is compared with the front's own."""
    setup, traps = task()
    cost = B5._FrontCost(setup, traps, front["e0"])
    fwd = C.TrapForward(setup, traps)
    out = {"seed": seed}
    lam = np.asarray(front["lambda"])
    lf = (1.0 - lam) * np.asarray(front["E"]) - lam * np.asarray(front["S"])
    for name, variant, its in (("gsw30", "gsw", 30), ("gsw100", "gsw", 100), ("pf100", "pfwgs", 100)):
        phi, _ = G.weighted_gs(setup, traps, its, Rng(seed), variant=variant)
        v, _ = fwd.fields(phi)
        i = np.abs(v) ** 2
        e_loss = float(np.sum((i - cost.target) ** 2)) / cost.tt
        s_light = float(np.sum(i)) / front["e0"]
        lg = (1.0 - lam) * e_loss - lam * s_light
        better = [int(k) for k in np.flatnonzero(lg < lf - 1e-12)]
        out[name] = {"E": e_loss, "S": s_light, "e": efficiency(trap_intensities(v)), "better_weights": better,
                     "n_better": len(better), "max_gain": float(np.max(lf - lg))}
    return out


def work(job: tuple) -> tuple:
    kind, seed, variant = job
    if kind == "main":
        return job, {"front": front_run(seed), "published": published_points(seed)}
    if kind == "rivals":
        return job, rival_fronts(seed)
    if kind == "ablation":
        return job, front_run(seed, **ABLATION[variant])
    raise ValueError(kind)


def run_jobs(jobs: list[tuple], workers: int) -> dict:
    out = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for job, res in ex.map(work, jobs):
            out[job] = res
            print(f"[{job[0]} seed {job[1]} {job[2] or ''}] done", flush=True)
    return out


# ------------------------------------------------------------------------------------------------ the checks of the Theory section

def identity_check() -> dict:
    """Numerical check of Proposition 1 (the loss is the squared error against a uniformly raised target, up to a constant)
    and of Proposition 3 (``sigma <= sqrt(E) e0 / e`` for equal weights) on random phases of a small array; Proposition 2
    (monotonicity of the global minimizers) is checked on the measured fronts."""
    s = make_setup(32)
    traps = bin_grid(s, 4, 4, 4)
    e0 = 0.6
    cost = B5._FrontCost(s, traps, e0)
    res = {"resid": 0.0, "bound_slack_min": 1e9}
    rng = np.random.default_rng(7)
    tt = cost.tt
    for trial in range(20):
        phi = rng.uniform(0, 2 * np.pi, (32, 32))
        v, _ = cost.fwd.fields(phi)
        i = np.abs(v) ** 2
        for lam in (0.0, 0.1, 0.3, 0.6, 0.9):
            cost.lam = lam
            val, _, _ = cost.value_grad(phi)
            kappa = lam * tt / ((1.0 - lam) * e0) if lam < 1.0 else 0.0
            shifted = (1.0 - lam) / tt * float(np.sum((i - cost.target - kappa / 2.0) ** 2)) \
                - (1.0 - lam) / tt * (kappa * float(np.sum(cost.target)) + len(i) * kappa ** 2 / 4.0)
            res["resid"] = max(res["resid"], abs(val - shifted))
        e_loss = float(np.sum((i - cost.target) ** 2)) / tt
        sigma = 100.0 * float(np.std(i)) / float(np.mean(i))
        bound = 100.0 * math.sqrt(e_loss) * e0 / float(np.sum(i))
        res["bound_slack_min"] = min(res["bound_slack_min"], bound - sigma)
    res["trials"] = 20
    return res


def timing(seeds: list[int]) -> dict:
    """The default front timed alone, one process, the BLAS threads of the machine, and the engine's own ``run``."""
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.pop(k, None)
    setup, traps = task()
    rows = []
    for seed in seeds:
        t0 = time.perf_counter()
        res = B5.run(setup, Target.from_traps(traps), budget=Budget(CG_ITERS), rng=Rng(seed))
        sec = time.perf_counter() - t0
        front = np.asarray(res.meta["front"])
        rows.append({"seed": seed, "seconds": sec, "hv": float(res.meta["hypervolume"]), "e": front[:, 0].tolist(),
                     "u": front[:, 1].tolist(), "knee": int(res.meta["knee"])})
        print(f"[timing seed {seed}] {sec:.1f} s, hv {res.meta['hypervolume']:.4f}", flush=True)
    return {"rows": rows}


# ------------------------------------------------------------------------------------------------ stored artifacts

def stored() -> dict:
    """The benchmark and the bake as committed: the hypervolume of the stored front of each geometry against the union of
    the published points at 30 and 100 iterations on the ideal device, and the bake's knee on the cases that run the method."""
    bench = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    names = {g["id"]: g["name"]["en"] for g in bench["geometries"]}
    out = {"engine_version": bench["engine_version"], "n_rows": len(bench["rows"]), "seeds": bench["protocol"]["seeds"],
           "geometries": []}
    for budget in (30, 100):
        cells = {(r["method"], r["geometry"]): r for r in bench["rows"] if r["budget_kind"] == "iterations"
                 and r["budget"] == budget and r["params"] == "default" and r["device"] == "ideal"}
        for f in sorted(bench.get("pareto") or [], key=lambda p: p["geometry"]):
            g = f["geometry"]
            pts = [(cells[(m, g)]["efficiency"]["median"], cells[(m, g)]["uniformity"]["median"])
                   for m in ("M04", "M05", "M06", "M09") if (m, g) in cells]
            if not pts:
                continue
            front = [(p["efficiency"], p["uniformity"]) for p in f["points"]]
            rec = {"budget": budget, "geometry": g, "name": names[g], "hv_front": hv_of(front), "hv_published": hv_of(pts),
                   "n_front": len(front), "lam_max": max(p["lambda"] for p in f["points"]),
                   "n_published": len(pts), "seeds_b5": cells[("B5", g)]["n_seeds"] if ("B5", g) in cells else None}
            rec["margin"] = rec["hv_front"] - rec["hv_published"]
            out["geometries"].append(rec)
    mr = json.loads((ROOT / "data-pipeline" / "pipeline" / "cases" / "measured_ranges.json").read_text(encoding="utf-8"))
    bake = {}
    for case, vals in mr["measured"].items():
        if "B5.efficiency" in vals:
            bake[case] = {m: stats(vals[f"B5.{m}"]) for m in ("efficiency", "uniformity", "rel_std_pct")}
            bake[case]["M06"] = {m: stats(vals[f"M06.{m}"]) for m in ("efficiency", "uniformity", "rel_std_pct")} \
                if "M06.efficiency" in vals else None
            bake[case]["M07"] = {m: stats(vals[f"M07.{m}"]) for m in ("efficiency", "uniformity", "rel_std_pct")} \
                if "M07.efficiency" in vals else None
    out["bake"] = bake
    out["bake_seeds"] = mr["seeds"]
    return out


# ------------------------------------------------------------------------------------------------ analysis

def dominating(front: dict, point) -> int:
    """Number of front points with efficiency at least and uniformity greater than the point (the criterion of the test)."""
    e, u = np.asarray(front["e"]), np.asarray(front["u"])
    return int(np.sum((e >= point[0]) & (u > point[1])))


def analyse(data: dict) -> dict:
    """Per-seed derived quantities and their summaries, written back into ``data['analysis']``."""
    rows = data["main"]
    a: dict = {}
    names = ("M04", "M05", "M06", "M09")
    hv_f, hv_b, hv_b7, ratio = [], [], [], []
    dom = {n: [] for n in (*names, "M07")}
    any_dom_all = []
    refs_f = {k: [] for k in REFS}
    refs_b = {k: [] for k in REFS}
    knee_e, knee_u, knee_s, secs, npar, emin, emax, umin = [], [], [], [], [], [], [], []
    mono_e_viol, mono_E_viol, mono_u_viol, sig_slack, e0s = [], [], [], [], []
    u_slack, u_informative, u_total = [], [], []
    lam_sat = []
    for r in rows:
        f, p = r["front"], r["published"]
        base = [p[n] for n in names]
        hv_f.append(f["hv"])
        hv_b.append(hv_of(base))
        hv_b7.append(hv_of(base + [p["M07"]]))
        ratio.append(f["hv"] / hv_b[-1])
        for k, ref in REFS.items():
            refs_f[k].append(f["hv_refs"][k])
            refs_b[k].append(hv_of(base, ref))
        for n in (*names, "M07"):
            dom[n].append(dominating(f, p[n]))
        any_dom_all.append(all(dominating(f, p[n]) > 0 for n in ("M04", "M05")))
        kn = f["knee"]
        knee_e.append(f["e"][kn]); knee_u.append(f["u"][kn]); knee_s.append(f["sigma"][kn])
        secs.append(f["seconds"]); npar.append(len(f["pareto"]))
        emin.append(min(f["e"])); emax.append(max(f["e"])); umin.append(min(f["u"]))
        S, E = np.asarray(f["S"]), np.asarray(f["E"])
        mono_e_viol.append(int(np.sum(np.diff(f["e"]) < -1e-9)))
        mono_E_viol.append(int(np.sum(np.diff(E) < -1e-9)))
        mono_u_viol.append(int(np.sum(np.diff(f["u"]) > 1e-9)))
        # Proposition 3 on every front point: bound minus measured relative standard deviation (percent)
        bound = 100.0 * np.sqrt(E) * f["e0"] / np.asarray(f["e"])
        sig_slack.append(float(np.min(bound - np.asarray(f["sigma"]))))
        # Proposition 3, second bound: u >= 1 - sqrt(M E), informative where sqrt(M E) < 1
        ub = 1.0 - np.sqrt(100.0 * E)
        u_slack.append(float(np.min(np.asarray(f["u"]) - ub)))
        u_informative.append(int(np.sum(ub > 0.0)))
        u_total.append(len(E))
        e0s.append(f["e0"])
        emax_r = max(f["e"])
        rr = emax_r / f["e0"] - 1.0
        lam_sat.append(2.0 * rr / (1.0 + 2.0 * rr))
    a["hv_front"] = stats(hv_f); a["hv_published"] = stats(hv_b); a["hv_published_with_m07"] = stats(hv_b7)
    a["hv_ratio"] = stats(ratio)
    a["hv_diff"] = stats([x - y for x, y in zip(hv_f, hv_b)])
    a["hv_diff_m07"] = stats([x - y for x, y in zip(hv_f, hv_b7)])
    a["hv_ge_count"] = int(sum(1 for x, y in zip(hv_f, hv_b) if x >= y))
    a["hv_ge_count_m07"] = int(sum(1 for x, y in zip(hv_f, hv_b7) if x >= y))
    a["refs"] = {k: {"front": stats(refs_f[k]), "published": stats(refs_b[k]),
                     "diff": stats([x - y for x, y in zip(refs_f[k], refs_b[k])]),
                     "ge": int(sum(1 for x, y in zip(refs_f[k], refs_b[k]) if x >= y))} for k in REFS}
    a["dominating"] = {n: {"stats": stats(v), "seeds_with_any": int(sum(1 for x in v if x > 0))} for n, v in dom.items()}
    a["both_ms_dominated_seeds"] = int(sum(any_dom_all))
    a["knee"] = {"e": stats(knee_e), "u": stats(knee_u), "sigma": stats(knee_s),
                 "seeds_at_uniform_end": int(sum(1 for r in rows if r["front"]["knee"] == 0))}
    def gain_u09(r):
        f = r["front"]
        last = max(k for k, u in enumerate(f["u"]) if u >= 0.9)
        return f["e"][last] - f["e0"]
    a["e_gain_u09"] = stats([gain_u09(r) for r in rows])
    a["raw_factor"] = stats([100.0 / r["front"]["e0"] for r in rows])
    a["e_gain"] = stats([max(r["front"]["e"]) - r["front"]["e0"] for r in rows])
    a["e_ratio"] = stats([max(r["front"]["e"]) / r["front"]["e0"] for r in rows])
    a["seconds_pool"] = stats(secs)
    a["ds_seconds"] = stats([r["published"]["M09_seconds"] for r in rows])
    a["n_pareto"] = stats(npar)
    a["e_min"] = stats(emin); a["e_max"] = stats(emax); a["u_min"] = stats(umin); a["e0"] = stats(e0s)
    a["mono"] = {"efficiency_violations": stats(mono_e_viol), "loss_error_violations": stats(mono_E_viol),
                 "uniformity_violations": stats(mono_u_viol),
                 "seeds_efficiency_monotone": int(sum(1 for x in mono_e_viol if x == 0)),
                 "seeds_loss_error_monotone": int(sum(1 for x in mono_E_viol if x == 0)),
                 "seeds_uniformity_monotone": int(sum(1 for x in mono_u_viol if x == 0))}
    a["sigma_bound_slack_min"] = min(sig_slack)
    a["u_bound_slack_min"] = min(u_slack)
    a["u_bound_informative"] = int(sum(u_informative)); a["u_bound_points"] = int(sum(u_total))
    a["lambda_saturation"] = stats(lam_sat)
    # the points of the published methods
    a["points"] = {n: {"e": stats([r["published"][n][0] for r in rows]), "u": stats([r["published"][n][1] for r in rows])}
                   for n in (*names, "M07")}
    # rival one-parameter fronts
    if data.get("rivals"):
        riv = data["rivals"]
        a["rivals"] = {}
        for key in ("gsw_path", "pfwgs_path", "gaa_sweep"):
            hv = [hv_of(r[key]) for r in riv]
            diff = [row["front"]["hv"] - h for row, h in zip(rows, hv)]
            a["rivals"][key] = {"hv": stats(hv), "diff": stats(diff), "front_ge": int(sum(1 for d in diff if d >= 0))}
        union = []
        for row, r in zip(rows, riv):
            pts = [row["published"][n] for n in (*names, "M07")] + r["gsw_path"] + r["pfwgs_path"] + r["gaa_sweep"]
            union.append(hv_of(pts))
        diff = [row["front"]["hv"] - h for row, h in zip(rows, union)]
        a["rivals"]["union"] = {"hv": stats(union), "diff": stats(diff), "front_ge": int(sum(1 for d in diff if d >= 0))}
        # points of the rival families that no front point dominates (efficiency at least, uniformity at least)
        undominated = []
        for row, r in zip(rows, riv):
            f = row["front"]
            cnt = 0
            for key in ("gsw_path", "pfwgs_path", "gaa_sweep"):
                for e, u in r[key]:
                    if not any(fe >= e and fu >= u for fe, fu in zip(f["e"], f["u"])):
                        cnt += 1
            undominated.append(cnt)
        a["rivals"]["undominated_points"] = stats(undominated)
    if data.get("rivals"):
        dom_pub, gain = [], []
        for row, r in zip(rows, data["rivals"]):
            fr = row["front"]
            F = list(zip(fr["e"], fr["u"]))
            pub = [tuple(row["published"][n]) for n in (*names, "M07")] \
                + [tuple(x) for k in ("gsw_path", "pfwgs_path", "gaa_sweep") for x in r[k]]
            dom_pub.append(sum(1 for e, u in F if any(e2 >= e and u2 >= u and (e2 > e or u2 > u) for e2, u2 in pub)))
            gain.append(hv_of(F + pub) - fr["hv"])
        a["front_dominated_by_published"] = stats(dom_pub)
        a["hv_gain_from_published"] = stats(gain)
    if data.get("diagnostic"):
        dg = {}
        for name in ("gsw30", "gsw100", "pf100"):
            dg[name] = {"n_better": stats([x[name]["n_better"] for x in data["diagnostic"]]),
                        "seeds_with_any": int(sum(1 for x in data["diagnostic"] if x[name]["n_better"] > 0)),
                        "max_gain": stats([x[name]["max_gain"] for x in data["diagnostic"]]),
                        "E": stats([x[name]["E"] for x in data["diagnostic"]]),
                        "S": stats([x[name]["S"] for x in data["diagnostic"]])}
        a["diagnostic"] = dg
    # ablation
    if data.get("ablation"):
        ab = {}
        base_hv = {r["seed"]: r["hv"] for r in data["ablation"]["default"]}
        for name, runs in data["ablation"].items():
            hv = [r["hv"] for r in runs]
            diff = [r["hv"] - base_hv[r["seed"]] for r in runs]
            dom = []
            for r in runs:
                rv = data["rivals"][r["seed"] - 1]
                row = rows[r["seed"] - 1]
                pub = [tuple(row["published"][n]) for n in (*names, "M07")] \
                    + [tuple(x) for k in ("gsw_path", "pfwgs_path", "gaa_sweep") for x in rv[k]]
                dom.append(sum(1 for e, u in zip(r["e"], r["u"])
                               if any(e2 >= e and u2 >= u and (e2 > e or u2 > u) for e2, u2 in pub)))
            ab[name] = {"hv": stats(hv), "diff": stats(diff), "seconds": stats([r["seconds"] for r in runs]),
                        "dominated_by_published": stats(dom), "n_points": len(runs[0]["e"]),
                        "e_first": stats([r["e"][0] for r in runs]),
                        "u_min": stats([min(r["u"]) for r in runs]), "e_max": stats([max(r["e"]) for r in runs]),
                        "n_pareto": stats([len(r["pareto"]) for r in runs]),
                        "knee_eu": stats([r["e"][r["knee"]] * r["u"][r["knee"]] for r in runs]),
                        "lam_max": stats([max(r["lambda"]) for r in runs]),
                        "n_lambda": len(runs[0]["lambda"])}
        a["ablation"] = ab
        # time model: seconds against n_lambda times cg iterations, ordinary least squares over the ablation runs
        xs, ys = [], []
        cfg = {"default": (20, 15), "n_lambda_5": (5, 15), "n_lambda_10": (10, 15), "n_lambda_40": (40, 15), "cg_5": (20, 5),
               "cg_30": (20, 30), "quadratic": (20, 15), "target": (20, 15), "cold": (20, 15), "start_gs": (20, 15),
               "start_random": (20, 15), "start_gsw100": (20, 15), "raw_loss": (20, 15)}
        for name, runs in data["ablation"].items():
            if name in ("raw_loss",):
                continue
            for r in runs:
                xs.append(cfg[name][0] * cfg[name][1]); ys.append(r["seconds"])
        x, y = np.array(xs, float), np.array(ys, float)
        b, c = np.polyfit(x, y, 1)
        pred = b * x + c
        ss_res, ss_tot = float(np.sum((y - pred) ** 2)), float(np.sum((y - y.mean()) ** 2))
        a["time_model"] = {"slope": float(b), "intercept": float(c), "r2": 1.0 - ss_res / ss_tot, "n": len(xs)}
    if data.get("timing"):
        a["timing"] = {"seconds": stats([r["seconds"] for r in data["timing"]["rows"]]),
                       "under_60": int(sum(1 for r in data["timing"]["rows"] if r["seconds"] < 60.0)),
                       "n": len(data["timing"]["rows"]),
                       "hv_match_max": max(abs(r["hv"] - rows[i]["front"]["hv"]) for i, r in enumerate(data["timing"]["rows"]))}
    return a


# ------------------------------------------------------------------------------------------------ macros and tables

def macro(name: str, value) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def pm(s: dict, d: int = 3) -> str:
    """``mean \\pm half-width`` of the 95 percent interval, as a math string."""
    half = (s["ci_hi"] - s["ci_lo"]) / 2.0
    return f"${s['mean']:.{d}f}\\pm{half:.{d}f}$"


def ci(s: dict, d: int = 3) -> str:
    return f"{s['ci_lo']:.{d}f} to {s['ci_hi']:.{d}f}"


SHORT = {"G1": "lattice 10 x 10", "G2": "ring, 36 traps", "G3": "random, 100 traps", "G4": "quasi-periodic, 119",
         "G5": "3D lattice 5 x 5 x 3", "G6": "large, 1024 and 819"}


def write_outputs(data: dict) -> None:
    a = data["analysis"]
    L: list[str] = ["% written by data/measure.py from b5.json: do not edit\n"]
    m = L.append
    meta = data["meta"]
    m(macro("nSeeds", meta["seeds"])); m(macro("nSeedsAbl", meta["seeds_abl"]))
    m(macro("nLambda", N_LAMBDA)); m(macro("cgIters", CG_ITERS)); m(macro("warmIters", WARM)); m(macro("baseIters", BASE_ITERS))
    m(macro("nPix", meta["n_pix"])); m(macro("nTraps", meta["n_traps"]))
    m(macro("hvFront", f(a["hv_front"]["mean"], 4)))
    m(macro("hvFrontCi", ci(a["hv_front"], 4)))
    m(macro("hvPub", f(a["hv_published"]["mean"], 4)))
    m(macro("hvPubCi", ci(a["hv_published"], 4)))
    m(macro("hvDiff", f(a["hv_diff"]["mean"], 4)))
    m(macro("hvDiffLo", f(a["hv_diff"]["ci_lo"], 4))); m(macro("hvDiffHi", f(a["hv_diff"]["ci_hi"], 4)))
    m(macro("hvDiffMin", f(a["hv_diff"]["min"], 4))); m(macro("hvDiffMax", f(a["hv_diff"]["max"], 4)))
    m(macro("hvRatio", f(a["hv_ratio"]["mean"], 4)))
    m(macro("hvRatioLo", f(a["hv_ratio"]["ci_lo"], 4))); m(macro("hvRatioHi", f(a["hv_ratio"]["ci_hi"], 4)))
    m(macro("hvRatioPct", f(100 * (a["hv_ratio"]["mean"] - 1), 2)))
    m(macro("hvGeCount", a["hv_ge_count"]))
    m(macro("hvPubSeven", f(a["hv_published_with_m07"]["mean"], 4)))
    m(macro("hvDiffSevenLo", f(a["hv_diff_m07"]["ci_lo"], 4))); m(macro("hvDiffSevenHi", f(a["hv_diff_m07"]["ci_hi"], 4)))
    m(macro("hvDiffSeven", f(a["hv_diff_m07"]["mean"], 4)))
    m(macro("hvGeCountSeven", a["hv_ge_count_m07"]))
    for k, nm in (("origin", "Zero"), ("e05", "Half"), ("e07", "Seven")):
        r = a["refs"][k]
        m(macro(f"hvRef{nm}Front", f(r["front"]["mean"], 4))); m(macro(f"hvRef{nm}Pub", f(r["published"]["mean"], 4)))
        m(macro(f"hvRef{nm}Diff", f(r["diff"]["mean"], 4)))
        m(macro(f"hvRef{nm}Lo", f(r["diff"]["ci_lo"], 4))); m(macro(f"hvRef{nm}Hi", f(r["diff"]["ci_hi"], 4)))
        m(macro(f"hvRef{nm}Ge", r["ge"]))
    for n, nm in (("M04", "GS"), ("M05", "GAA"), ("M06", "GSW"), ("M09", "DS"), ("M07", "PF")):
        d = a["dominating"][n]
        m(macro(f"dom{nm}Mean", f(d["stats"]["mean"], 1))); m(macro(f"dom{nm}Min", int(d["stats"]["min"])))
        m(macro(f"dom{nm}Max", int(d["stats"]["max"]))); m(macro(f"dom{nm}Seeds", d["seeds_with_any"]))
    m(macro("domBothSeeds", a["both_ms_dominated_seeds"]))
    for n, nm in (("M04", "GS"), ("M05", "GAA"), ("M06", "GSW"), ("M09", "DS"), ("M07", "PF")):
        p = a["points"][n]
        m(macro(f"pt{nm}E", f(p["e"]["mean"], 3))); m(macro(f"pt{nm}U", f(p["u"]["mean"], 3)))
    kn = a["knee"]
    m(macro("kneeE", f(kn["e"]["mean"], 3))); m(macro("kneeELo", f(kn["e"]["ci_lo"], 3))); m(macro("kneeEHi", f(kn["e"]["ci_hi"], 3)))
    m(macro("kneeU", f(kn["u"]["mean"], 3))); m(macro("kneeULo", f(kn["u"]["ci_lo"], 3))); m(macro("kneeUHi", f(kn["u"]["ci_hi"], 3)))
    m(macro("kneeSigma", f(kn["sigma"]["mean"], 2))); m(macro("kneeSigmaLo", f(kn["sigma"]["ci_lo"], 2)))
    m(macro("kneeSigmaHi", f(kn["sigma"]["ci_hi"], 2)))
    m(macro("kneeZeroSeeds", kn["seeds_at_uniform_end"]))
    m(macro("eMaxFrontDelta", f(a["e_gain"]["mean"], 4))); m(macro("eMaxRatio", f(a["e_ratio"]["mean"], 3)))
    m(macro("eGainUNine", f(a["e_gain_u09"]["mean"], 4)))
    m(macro("eGainUNinePp", f(100 * a["e_gain_u09"]["mean"], 1)))
    m(macro("rawFactor", f(a["raw_factor"]["mean"], 0)))
    lam1 = 1.0 / (N_LAMBDA - 1)
    m(macro("rawShiftRel", f(lam1 / (2 * (1 - lam1)) * a["raw_factor"]["mean"], 1)))
    m(macro("eMaxRatioPct", f(100 * (a["e_ratio"]["mean"] - 1), 1)))
    for k, nm in (("e05", "Half"), ("e07", "Seven")):
        m(macro(f"hvRef{nm}Rel", f(100 * a["refs"][k]["diff"]["mean"] / a["refs"][k]["published"]["mean"], 1)))
    r0, v0 = data["main"][0], data["rivals"][0]
    gE, gU = v0["gsw_path"][-1]
    near = min(range(len(r0["front"]["e"])), key=lambda k: abs(r0["front"]["e"][k] - gE))
    m(macro("seedOneGswE", f(gE, 4))); m(macro("seedOneGswU", f(gU, 4)))
    m(macro("seedOneNearE", f(r0["front"]["e"][near], 4))); m(macro("seedOneNearU", f(r0["front"]["u"][near], 4)))
    m(macro("eStart", f(a["e0"]["mean"], 3)))
    m(macro("eMin", f(a["e_min"]["mean"], 3))); m(macro("eMaxFront", f(a["e_max"]["mean"], 4)))
    m(macro("eMaxFrontLo", f(a["e_max"]["ci_lo"], 4))); m(macro("eMaxFrontHi", f(a["e_max"]["ci_hi"], 4)))
    m(macro("uMinFront", f(a["u_min"]["mean"], 3)))
    m(macro("uMinFrontLo", f(a["u_min"]["ci_lo"], 3))); m(macro("uMinFrontHi", f(a["u_min"]["ci_hi"], 3)))
    m(macro("nParetoMean", f(a["n_pareto"]["mean"], 1))); m(macro("nParetoMin", int(a["n_pareto"]["min"])))
    m(macro("nParetoMax", int(a["n_pareto"]["max"])))
    mo = a["mono"]
    m(macro("monoESeeds", mo["seeds_efficiency_monotone"])); m(macro("monoLossSeeds", mo["seeds_loss_error_monotone"]))
    m(macro("monoUSeeds", mo["seeds_uniformity_monotone"]))
    m(macro("monoEViolMax", int(mo["efficiency_violations"]["max"]))); m(macro("monoLossViolMax", int(mo["loss_error_violations"]["max"])))
    m(macro("monoUViolMax", int(mo["uniformity_violations"]["max"])))
    m(macro("sigmaSlackMin", f"{a['sigma_bound_slack_min']:.3g}"))
    m(macro("uSlackMin", f"{a['u_bound_slack_min']:.3g}")); m(macro("uBoundInf", a["u_bound_informative"])); m(macro("uBoundPts", a["u_bound_points"]))
    m(macro("lamSat", f(a["lambda_saturation"]["mean"], 3)))
    m(macro("lamSatLo", f(a["lambda_saturation"]["ci_lo"], 3))); m(macro("lamSatHi", f(a["lambda_saturation"]["ci_hi"], 3)))
    ident = data["identity"]
    m(macro("identResid", f"{ident['resid']:.1e}"))
    m(macro("identTrials", ident["trials"]))
    m(macro("identBoundSlack", f"{ident['bound_slack_min']:.3g}"))
    if "rivals" in a:
        rv = a["rivals"]
        for key, nm in (("gsw_path", "Gsw"), ("pfwgs_path", "Pf"), ("gaa_sweep", "Gaa"), ("union", "Union")):
            m(macro(f"riv{nm}Hv", f(rv[key]["hv"]["mean"], 4)))
            m(macro(f"riv{nm}Diff", f(rv[key]["diff"]["mean"], 4)))
            m(macro(f"riv{nm}Lo", f(rv[key]["diff"]["ci_lo"], 4))); m(macro(f"riv{nm}Hi", f(rv[key]["diff"]["ci_hi"], 4)))
            m(macro(f"riv{nm}Ge", rv[key]["front_ge"]))
        m(macro("rivUndom", f(rv["undominated_points"]["mean"], 1)))
        m(macro("rivUndomMax", int(rv["undominated_points"]["max"])))
    if "front_dominated_by_published" in a:
        d_ = a["front_dominated_by_published"]
        m(macro("frontDomMean", f(d_["mean"], 1))); m(macro("frontDomMin", int(d_["min"]))); m(macro("frontDomMax", int(d_["max"])))
        m(macro("hvGainPub", f(a["hv_gain_from_published"]["mean"], 4)))
        m(macro("hvGainPubMax", f(a["hv_gain_from_published"]["max"], 4)))
    if "diagnostic" in a:
        for key, nm in (("gsw30", "GswThirty"), ("gsw100", "GswHundred"), ("pf100", "PfHundred")):
            dd = a["diagnostic"][key]
            m(macro(f"diag{nm}Seeds", dd["seeds_with_any"])); m(macro(f"diag{nm}Mean", f(dd["n_better"]["mean"], 1)))
            m(macro(f"diag{nm}Min", int(dd["n_better"]["min"]))); m(macro(f"diag{nm}Max", int(dd["n_better"]["max"])))
            m(macro(f"diag{nm}E", f"{dd['E']['mean']:.2e}")); m(macro(f"diag{nm}S", f(dd["S"]["mean"], 4)))
            m(macro(f"diag{nm}Gain", f"{dd['max_gain']['mean']:.2e}"))
    if "ablation" in a:
        ab = a["ablation"]
        for name, s in ab.items():
            key = ABL_KEY[name]
            m(macro(f"abl{key}Hv", f(s["hv"]["mean"], 4)))
            m(macro(f"abl{key}Diff", f(s["diff"]["mean"], 4)))
            m(macro(f"abl{key}Abs", f(abs(s["diff"]["mean"]), 4)))
            m(macro(f"abl{key}Sec", f(s["seconds"]["mean"], 1)))
            m(macro(f"abl{key}UMin", f(s["u_min"]["mean"], 3)))
            m(macro(f"abl{key}EMax", f(s["e_max"]["mean"], 4)))
            m(macro(f"abl{key}LamMax", f(s["lam_max"]["mean"], 3)))
            m(macro(f"abl{key}Dom", f(s["dominated_by_published"]["mean"], 1)))
            m(macro(f"abl{key}NPts", s["n_points"]))
            m(macro(f"abl{key}NPar", f(s["n_pareto"]["mean"], 1)))
            m(macro(f"abl{key}EFirst", f(s["e_first"]["mean"], 3)))
            m(macro(f"abl{key}DiffLo", f(s["diff"]["ci_lo"], 4))); m(macro(f"abl{key}DiffHi", f(s["diff"]["ci_hi"], 4)))
        raw = data["ablation"]["raw_loss"]
        m(macro("ablRawFirstU", f(statistics.fmean(r["u"][1] for r in raw), 3)))
        m(macro("ablRawLaterU", f(max(max(r["u"][2:]) for r in raw), 3)))
        m(macro("ablRawLamOne", f(raw[0]["lambda"][1], 3)))
        tm = a["time_model"]
        m(macro("timeSlope", f"{1000 * tm['slope']:.1f}")); m(macro("timeIntercept", f(tm["intercept"], 1)))
        m(macro("timeRTwo", f(tm["r2"], 3))); m(macro("timeN", tm["n"]))
    if "timing" in a:
        t = a["timing"]
        m(macro("timeAlone", f(t["seconds"]["mean"], 1))); m(macro("timeAloneMax", f(t["seconds"]["max"], 1)))
        m(macro("timeAloneMin", f(t["seconds"]["min"], 1))); m(macro("timeAloneN", t["n"]))
        m(macro("timeAloneUnder", t["under_60"]))
        m(macro("timeAloneHvMatch", f"{t['hv_match_max']:.1e}"))
    m(macro("timePool", f(a["seconds_pool"]["mean"], 1)))
    m(macro("dsSec", f(a["ds_seconds"]["mean"], 0)))
    cons = data["consistency"]
    m(macro("consistMax", f"{cons['max_abs_diff']:.1e}"))
    st = data["stored"]
    for budget, nm in ((30, "Thirty"), (100, "Hundred")):
        cells = [g for g in st["geometries"] if g["budget"] == budget]
        m(macro(f"benchN{nm}", len(cells)))
        m(macro(f"benchPass{nm}", sum(1 for g in cells if g["margin"] >= 0)))
        m(macro(f"benchWorst{nm}", f(min(g["margin"] for g in cells), 3)))
        m(macro(f"benchBest{nm}", f(max(g["margin"] for g in cells), 3)))
        m(macro(f"benchWorstAbs{nm}", f(abs(min(g["margin"] for g in cells)), 3)))
    m(macro("benchRows", st["n_rows"])); m(macro("benchSeeds", st["seeds"])); m(macro("benchEngine", st["engine_version"]))
    m(macro("bakeSeeds", st["bake_seeds"]))
    (HERE / "b5_numbers.tex").write_text("".join(L), encoding="utf-8")

    # ------------------------------------------------------------------ tables
    def row(cells: list[str]) -> str:
        return " & ".join(cells) + " \\\\\n"

    T = []
    # main comparison: mean and interval over the seeds of each point and of the front
    T.append("\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n")
    T.append(row(["Result", "Efficiency", "Uniformity", "Hypervolume"]))
    T.append("\\midrule\n")
    names = {"M04": "Gerchberg-Saxton (M04)", "M05": "Adaptive additive (M05)", "M06": "Weighted GS (M06)",
             "M07": "Phase-fixed WGS (M07)", "M09": "Direct search (M09)"}
    for n in ("M04", "M05", "M06", "M07", "M09"):
        p = a["points"][n]
        hv = stats([e * u for e, u in zip([r["published"][n][0] for r in data["main"]], [r["published"][n][1] for r in data["main"]])])
        T.append(row([names[n], pm(p["e"]), pm(p["u"]), pm(hv, 3)]))
    T.append("\\midrule\n")
    T.append(row(["Union of M04, M05, M06, M09", "", "", pm(a["hv_published"], 4)]))
    T.append(row(["Front (knee point)", pm(a["knee"]["e"]), pm(a["knee"]["u"]), ""]))
    T.append(row(["Front (whole)", f"{f(a['e_min']['mean'])} to {f(a['e_max']['mean'])}", f"{f(a['u_min']['mean'])} to 1", pm(a["hv_front"], 4)]))
    T.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_main.tex").write_text("".join(T), encoding="utf-8")

    T = ["\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"]
    T.append(row(["Reference of the hypervolume", "Front", "Published union", "Difference, 95\\% interval"]))
    T.append("\\midrule\n")
    for k, lab in (("origin", "$(0,0)$"), ("e05", "$(0.5,0)$"), ("e07", "$(0.7,0)$")):
        r = a["refs"][k]
        T.append(row([lab, pm(r["front"], 4), pm(r["published"], 4), pm(r["diff"], 4)]))
    T.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_refs.tex").write_text("".join(T), encoding="utf-8")

    if "rivals" in a:
        T = ["\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"]
        T.append(row(["One-parameter front of a published method", "Hypervolume", "Front minus it", "Seeds front $\\ge$"]))
        T.append("\\midrule\n")
        lab = {"gsw_path": "Weighted GS, iterates 1 to 100", "pfwgs_path": "Phase-fixed WGS, iterates 1 to 100",
               "gaa_sweep": "Adaptive additive, exponent 0 to 1", "union": "Union of all of them and the five points"}
        for key in ("gsw_path", "pfwgs_path", "gaa_sweep", "union"):
            r = a["rivals"][key]
            T.append(row([lab[key], pm(r["hv"], 4), pm(r["diff"], 4), f"{r['front_ge']} of {meta['seeds']}"]))
        T.append("\\bottomrule\n\\end{tabular}\n")
        (HERE / "tab_rivals.tex").write_text("".join(T), encoding="utf-8")

    if "ablation" in a:
        T = ["\\begin{tabular}{@{}llrrrr@{}}\n\\toprule\n"]
        T.append(row(["Component", "Variant", "Hypervolume", "Change", "Lowest $u$", "Seconds"]))
        T.append("\\midrule\n")
        spec = [("Reference", "default", "20 values, 15 steps, linear, warm"),
                ("Number of values", "n_lambda_5", "5 values"), ("", "n_lambda_10", "10 values"), ("", "n_lambda_40", "40 values"),
                ("Steps per value", "cg_5", "5 steps"), ("", "cg_30", "30 steps"),
                ("Schedule", "quadratic", "quadratic in $\\lambda$"), ("", "target", "target-spaced"),
                ("Continuation", "cold", "cold start per value"),
                ("Start", "start_gs", "plain GS start"), ("", "start_random", "random, no iteration"),
                ("", "start_gsw100", "weighted GS, 100 it."),
                ("Loss scaling", "raw_loss", "unscaled loss")]
        for comp, key, lab in spec:
            s = a["ablation"][key]
            T.append(row([comp, lab, pm(s["hv"], 4), "" if key == "default" else pm(s["diff"], 4), f(s["u_min"]["mean"], 3),
                          f(s["seconds"]["mean"], 1)]))
        T.append("\\bottomrule\n\\end{tabular}\n")
        (HERE / "tab_ablation.tex").write_text("".join(T), encoding="utf-8")

    T = ["\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n"]
    T.append(row(["Geometry", "Iter.", "Points", "Largest $\\lambda$", "Front", "Union", "Difference"]))
    T.append("\\midrule\n")
    for g in st["geometries"]:
        T.append(row([g["geometry"] + " " + SHORT.get(g["geometry"], g["name"]), str(g["budget"]), str(g["n_front"]),
                      f(g["lam_max"], 3), f(g["hv_front"], 4), f(g["hv_published"], 4), f"{g['margin']:+.4f}"]))
    T.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_bench.tex").write_text("".join(T), encoding="utf-8")

    T = ["\\begin{tabular}{@{}lrrr@{}}\n\\toprule\n"]
    T.append(row(["Case", "Efficiency", "Uniformity", "Relative std. dev. (percent)"]))
    T.append("\\midrule\n")
    for case, v in st["bake"].items():
        T.append(row([case.split("_")[0], pm(v["efficiency"], 3), pm(v["uniformity"], 3), pm(v["rel_std_pct"], 2)]))
    T.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_bake.tex").write_text("".join(T), encoding="utf-8")


# ------------------------------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--seeds-abl", type=int, default=5)
    ap.add_argument("--seeds-timing", type=int, default=3)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--parts", default="main,rivals,ablation,identity,timing,stored")
    ap.add_argument("--only-variants", default="", help="run only these ablation variants and merge them into b5.json")
    ap.add_argument("--macros-only", action="store_true")
    a = ap.parse_args()
    path = HERE / "b5.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not a.macros_only:
        parts = a.parts.split(",")
        seeds = list(range(1, a.seeds + 1))
        if not a.only_variants and "main" in parts:
            data["meta"] = {"seeds": a.seeds, "seeds_abl": a.seeds_abl, "n_pix": 256, "n_traps": 100,
                            "task": "10 x 10 square lattice, 8 bins apart, 256 x 256 pixels padded 2, Gaussian beam, 850 nm",
                            "workers": a.workers}
        data.setdefault("meta", {})
        t_all = time.perf_counter()
        if "main" in parts:
            res = run_jobs([("main", s, None) for s in seeds], a.workers)
            data["main"] = [{"seed": s, **res[("main", s, None)]} for s in seeds]
            # the loop of this script must be the engine's: B5.run on seed 1 against the first main run
            setup, traps = task()
            ref = B5.run(setup, Target.from_traps(traps), budget=Budget(CG_ITERS), rng=Rng(1))
            mine = np.array([data["main"][0]["front"]["e"], data["main"][0]["front"]["u"]]).T
            data["consistency"] = {"max_abs_diff": float(np.max(np.abs(mine - np.asarray(ref.meta["front"])[:, :2]))),
                                   "hv_engine": float(ref.meta["hypervolume"]), "hv_here": data["main"][0]["front"]["hv"]}
        if "rivals" in parts:
            res = run_jobs([("rivals", s, None) for s in seeds], a.workers)
            data["rivals"] = [res[("rivals", s, None)] for s in seeds]
        if "ablation" in parts:
            sa = list(range(1, a.seeds_abl + 1))
            names = a.only_variants.split(",") if a.only_variants else list(ABLATION)
            res = run_jobs([("ablation", s, v) for v in names for s in sa], a.workers)
            data.setdefault("ablation", {})
            for v in names:
                data["ablation"][v] = [res[("ablation", s, v)] for s in sa]
        if "diagnostic" in parts:
            data["diagnostic"] = [diagnose(r["seed"], r["front"]) for r in data["main"]]
        if "identity" in parts:
            data["identity"] = identity_check()
        if "stored" in parts:
            data["stored"] = stored()
        if "timing" in parts:
            data["timing"] = timing(list(range(1, a.seeds_timing + 1)))
        data["meta"].setdefault("runs", []).append({"parts": a.parts, "only_variants": a.only_variants,
                                                    "wall_clock_s": time.perf_counter() - t_all})
        data["meta"]["command"] = ".venv-pipeline/Scripts/python.exe manuscripts/efficiency-uniformity-front/data/measure.py " \
                                  f"--seeds {a.seeds} --seeds-abl {a.seeds_abl} --seeds-timing {a.seeds_timing}"
    data["analysis"] = analyse(data)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    write_outputs(data)
    print("wrote b5.json, b5_numbers.tex and the tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
