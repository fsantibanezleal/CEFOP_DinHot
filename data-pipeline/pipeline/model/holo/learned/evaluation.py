"""Held-out evaluation of the two slots (numpy and onnxruntime; offline). It runs the RELEASED graphs through the method modules
``methods/learned/m17_cgh_net.py`` and ``b3_warm_start.py`` and the baselines through the engine, on the held-out files of
``heldout.py``; ``stages/evaluate.py`` writes its numbers into ``data/derived/models/metrics.json``.

cgh-net: per held-out target, the accuracy AC (unit-sum intensities, ``torch_forward.accuracy`` in numpy) of the network's mask
and of GS (M04) given the SAME wall-clock as the network's median inference time (``Budget`` with a time cap; at least one
iteration), plus GS at 30 iterations (the catalog baseline) and 300 iterations, and a lean numpy GS (two FFTs per iteration)
at the same wall-clock, because the engine's M04 does extra bookkeeping per iteration. ``accuracy_vs_gs`` is the per-target ratio.

warmstart-model: per held-out geometry and per seed, M07 from the random start (its own, ``init=None``) and from the learned
start, the same ``Rng`` seed and the same iteration budget; iterations to 1 percent of relative standard deviation (the budget
plus one when never reached) and the final efficiency, uniformity and relative standard deviation.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from ..core.forward import fft_focal_field
from ..core.geometry import Setup, focal_bin_m
from ..core.rng import Rng
from ..core.traps import Trap, TrapSet
from ..core.types import Budget, Target
from ..methods.baseline import m19_multiplane
from ..methods.baseline import m07_phase_fixed_wgs as m07
from ..methods.learned import b3_warm_start, m17_cgh_net
from . import convert, heldout

SETUP128 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
SETUP256 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)
BIG = 10**6
CURVE_FRACTIONS = (0.33, 0.6)


def stat(x) -> dict:
    x = np.asarray(x, dtype=np.float64)
    return {"median": float(np.median(x)), "q1": float(np.percentile(x, 25)), "q3": float(np.percentile(x, 75))}


# ----------------------------------------------------------------------------------------------------- cgh-net

def plane_accuracy(amps: np.ndarray, phi: np.ndarray, setup: Setup = SETUP128, z_planes=(-8.0, 0.0, 8.0)) -> float:
    """Volume accuracy of the mask ``phi``: the mean over the planes of ``2 sum(TI) / (sum T^2 + sum I^2)`` with unit-sum plane
    intensities, the plane field being the engine's focal field of the mask minus the plane's lens phase (same definition as the loss)."""
    n = setup.n_pix
    c = np.arange(n) - (n - 1) / 2.0
    q = (c[None, :] ** 2 + c[:, None] ** 2) / (n / 2.0) ** 2
    ac = []
    for a, z in zip(amps, z_planes):
        i = np.abs(fft_focal_field(phi - z * q, setup)) ** 2
        i = i / i.sum()
        t = np.asarray(a, dtype=np.float64) ** 2
        t = t / t.sum()
        ac.append(2.0 * np.sum(t * i) / (np.sum(t**2) + np.sum(i**2)))
    return float(np.mean(ac))


def _timed(fn):
    t0 = time.perf_counter()
    r = fn()
    return r, time.perf_counter() - t0


def volume_target(traps_arr: np.ndarray) -> Target:
    """The M19 / M17 target of a volume: its point voxels, positions in bins and plane indices converted to metres."""
    b, zr = focal_bin_m(SETUP128), convert.rayleigh_range_m(SETUP128)
    return Target.from_traps(TrapSet(Trap(i, float(r[0] * b), float(r[1] * b), float(r[2] * 8.0 * zr), float(r[3])) for i, r in enumerate(traps_arr)))


def evaluate_cgh(models_dir: Path, heldout_path: Path) -> tuple[dict, dict]:
    """``(metrics entry of the schema, detail document)`` of the multi-plane cgh-net.

    The wall-clock budget ``T`` is the median time of the baseline (M19, volumetric 3D GS, 30 iterations) on this machine. Per volume:
    M19 alone for ``T`` (the baseline), the hybrid (network pass, then M19 from its phase in what is left of ``T``), the network alone,
    M19 at 30 iterations. ``accuracy_vs_gs`` is the per-volume ratio hybrid / M19 alone; ``time_ms`` the hybrid's wall time. The detail
    adds the same ratio at fractions of ``T`` on every third volume.
    """
    amps, trap_sets, kinds = heldout.load_cgh_vol(heldout_path)
    tgs = [volume_target(t) for t in trap_sets]
    for _ in range(2):
        m17_cgh_net.run(SETUP128, tgs[0], budget=Budget(1), rng=Rng(1), models_dir=models_dir)
    t30 = [_timed(lambda: m19_multiplane.run(SETUP128, t, budget=Budget(30), rng=Rng(1), dz_m=m17_cgh_net.plane_dz_m(SETUP128)))[1] for t in tgs[::4]]
    budget_s = float(np.median(t30))
    dz = m17_cgh_net.plane_dz_m(SETUP128)
    rows = []
    for i, (a, t) in enumerate(zip(amps, tgs)):
        net = m17_cgh_net.run(SETUP128, t, budget=Budget(BIG), rng=Rng(1), models_dir=models_dir, refine=False)
        if net.meta["provenance"] != "real":
            raise RuntimeError("the cgh-net slot is not released in " + str(models_dir))
        hyb, t_hyb = _timed(lambda: m17_cgh_net.run(SETUP128, t, budget=Budget(BIG, budget_s), rng=Rng(1), models_dir=models_dir))
        base, t_base = _timed(lambda: m19_multiplane.run(SETUP128, t, budget=Budget(BIG, budget_s), rng=Rng(1), dz_m=dz))
        g30 = m19_multiplane.run(SETUP128, t, budget=Budget(30), rng=Rng(1), dz_m=dz)
        rows.append({"volume": f"{i:03d}/{kinds[i]}", "ac_hybrid": plane_accuracy(a, hyb.phi), "time_hybrid_ms": 1000 * t_hyb,
                     "hybrid_refine_iterations": hyb.meta["refine_iterations"], "network_ms": 1000 * hyb.meta["network_s"],
                     "ac_net_alone": plane_accuracy(a, net.phi), "ac_m19_matched": plane_accuracy(a, base.phi),
                     "time_m19_matched_ms": 1000 * t_base, "m19_matched_iterations": base.meta["iterations"],
                     "ac_m19_30": plane_accuracy(a, g30.phi)})
    curve = {}
    for frac in CURVE_FRACTIONS:
        tb, rr = frac * budget_s, []
        for a, t in list(zip(amps, tgs))[::3]:
            h = m17_cgh_net.run(SETUP128, t, budget=Budget(BIG, tb), rng=Rng(1), models_dir=models_dir)
            g = m19_multiplane.run(SETUP128, t, budget=Budget(BIG, tb), rng=Rng(1), dz_m=dz)
            rr.append(plane_accuracy(a, h.phi) / plane_accuracy(a, g.phi))
        curve[f"{1000 * tb:.0f} ms"] = {"fraction_of_T": frac, "n_volumes": len(rr), "ratio_hybrid_over_m19": stat(rr), "share_above_1": float(np.mean(np.array(rr) > 1.0))}
    col = lambda k: np.array([r[k] for r in rows])  # noqa: E731
    ratio = col("ac_hybrid") / col("ac_m19_matched")
    entry = {"held_out_n": len(rows), "accuracy_vs_gs": stat(ratio), "time_ms": stat(col("time_hybrid_ms")), "baseline": "M04"}
    kinds_arr = np.array([k.split("/")[1] if "/" in k else k for k in kinds])
    detail = {
        "slot": "cgh-net", "variant": "three planes at Z = -8, 0, +8 Rayleigh ranges", "baseline_is": "M19 (the schema constant 'M04' names GS, the catalog baseline before this decision)",
        "wall_clock_budget_ms": 1000 * budget_s, "budget_definition": "median wall time of M19 at 30 iterations on the held-out volumes, this machine",
        "accuracy": "mean over planes of AC = 2 sum(TI) / (sum T^2 + sum I^2), unit-sum plane intensities",
        "ac_median": {k: float(np.median(col(k))) for k in ("ac_hybrid", "ac_net_alone", "ac_m19_matched", "ac_m19_30")},
        "ratio_by_kind": {k: float(np.median(ratio[kinds_arr == k])) for k in sorted(set(kinds_arr))},
        "ratio_net_alone_over_m19_matched": stat(col("ac_net_alone") / col("ac_m19_matched")),
        "share_hybrid_above_m19": float(np.mean(ratio > 1.0)),
        "network_ms_median": float(np.median(col("network_ms"))), "hybrid_refine_iterations_median": float(np.median(col("hybrid_refine_iterations"))),
        "m19_matched_iterations_median": float(np.median(col("m19_matched_iterations"))),
        "budget_curve": curve, "rows": rows,
    }
    return entry, detail


# ------------------------------------------------------------------------------------------------ warmstart-model

def first_below(history, pct: float = 1.0, cap: int | None = None) -> int:
    for h in history:
        if h["rel_std"] <= pct:
            return int(h["iteration"])
    return (len(history) if cap is None else cap) + 1


def evaluate_warm(models_dir: Path, heldout_path: Path, seeds=(301, 302, 303), budget: int = 60, every: int = 1) -> tuple[dict, dict]:
    """``every`` > 1 evaluates every n-th geometry (the tests); the stage uses all of them."""
    gen, bench = heldout.load_warm(heldout_path)
    sets = [(f"gen/{i:02d}", a, 256) for i, a in enumerate(gen)] + [(f"bench/{n}", a, p) for n, a, p in bench]
    sets = [x for i, x in enumerate(sets) if i % every == 0 and (every == 1 or x[2] == 256)]
    rows = []
    for name, arr, n_pix in sets:
        setup = SETUP256 if n_pix == 256 else heldout._bench_setup(n_pix)
        t, m = np.zeros((1, convert.MAX_TRAPS, 4), np.float32), np.zeros((1, convert.MAX_TRAPS), np.float32)
        t[0, : len(arr)], m[0, : len(arr)] = arr, 1.0
        ts = convert.input_to_traps(setup, t, m)
        tgt = Target.from_traps(ts)
        per = {"random": [], "model": []}
        for s in seeds:
            rnd = m07.run(setup, tgt, budget=Budget(budget), rng=Rng(s), form="point")
            mod = b3_warm_start.run(setup, tgt, budget=Budget(budget), rng=Rng(s), models_dir=models_dir)
            if mod.meta["provenance"] != "real":
                raise RuntimeError("the warmstart-model slot is not released in " + str(models_dir))
            for arm, r in (("random", rnd), ("model", mod)):
                last = r.history[-1]
                per[arm].append((first_below(r.history, cap=budget), last["efficiency"], last["uniformity"], last["rel_std"]))
        row = {"geometry": name, "traps": int(len(arr)), "n_pix": n_pix}
        for arm in per:
            a = np.array(per[arm])
            row[arm] = {"iterations_to_1pct": float(np.median(a[:, 0])), "efficiency": float(np.median(a[:, 1])),
                        "uniformity": float(np.median(a[:, 2])), "rel_std_pct": float(np.median(a[:, 3]))}
        rows.append(row)
    col = lambda arm, k: np.array([r[arm][k] for r in rows])  # noqa: E731
    entry = {
        "held_out_n": len(rows),
        "iterations_to_1pct": {"model": stat(col("model", "iterations_to_1pct")), "random": stat(col("random", "iterations_to_1pct"))},
        "final_rel_std_pct": {"model": stat(col("model", "rel_std_pct")), "random": stat(col("random", "rel_std_pct"))},
    }
    rel = lambda k: float(abs(np.median(col("model", k)) - np.median(col("random", k))) / np.median(col("random", k)))  # noqa: E731
    gen_rows = [r for r in rows if r["geometry"].startswith("gen/")]
    bench_rows = [r for r in rows if r["geometry"].startswith("bench/")]
    detail = {
        "slot": "warmstart-model", "seeds": list(seeds), "iteration_budget": budget, "n_fix": 12,
        "iterations_never_reached_counted_as": budget + 1,
        "median_iterations_ratio_random_over_model": float(np.median(col("random", "iterations_to_1pct")) / np.median(col("model", "iterations_to_1pct"))),
        "final_metrics_relative_difference_of_medians": {"efficiency": rel("efficiency"), "uniformity": rel("uniformity")},
        "groups": {name: {"n": len(g), "iterations_median": {arm: float(np.median([r[arm]["iterations_to_1pct"] for r in g])) for arm in ("random", "model")}}
                   for name, g in (("gen", gen_rows), ("bench", bench_rows))},
        "rows": rows,
    }
    return entry, detail
