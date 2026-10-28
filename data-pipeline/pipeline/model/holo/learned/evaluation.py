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
from ..core.geometry import Setup, input_amplitude
from ..core.rng import Rng
from ..core.types import Budget, Target
from ..methods.baseline import _gs, m04_gs
from ..methods.baseline import m07_phase_fixed_wgs as m07
from ..methods.learned import b3_warm_start, m17_cgh_net
from . import convert, heldout

SETUP128 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
SETUP256 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)
BIG = 10**6


def stat(x) -> dict:
    x = np.asarray(x, dtype=np.float64)
    return {"median": float(np.median(x)), "q1": float(np.percentile(x, 25)), "q3": float(np.percentile(x, 75))}


# ----------------------------------------------------------------------------------------------------- cgh-net

def accuracy(a: np.ndarray, phi: np.ndarray, setup: Setup = SETUP128) -> float:
    """AC of the mask ``phi`` against the amplitude ``a`` through the engine's FFT model (same definition as the loss)."""
    i = np.abs(fft_focal_field(phi, setup)) ** 2
    i = i / i.sum()
    t = np.asarray(a, dtype=np.float64) ** 2
    t = t / t.sum()
    return float(2.0 * np.sum(t * i) / (np.sum(t**2) + np.sum(i**2)))


def lean_gs(a: np.ndarray, setup: Setup, time_s: float, iterations: int | None = None) -> np.ndarray:
    """Plain Gerchberg-Saxton in numpy with two FFTs per iteration (the same start as M04: ``start_phase_field``), run for
    ``time_s`` seconds or ``iterations`` iterations (at least one)."""
    n = setup.n_pix
    amp_in = input_amplitude(setup)
    t = np.fft.ifftshift(np.asarray(a, dtype=np.float64) / np.sqrt(np.sum(np.asarray(a, dtype=np.float64) ** 2)) * n)
    phi = _gs.start_phase_field(setup, Rng(1), None, _gs.START_WAVES)
    t0, k = time.perf_counter(), 0
    while True:
        e = np.fft.fft2(amp_in * np.exp(1j * phi), norm="ortho")
        mag = np.abs(e)
        e = t * np.where(mag > 1e-300, e / np.maximum(mag, 1e-300), 1.0)
        phi = np.angle(np.fft.ifft2(e, norm="ortho"))
        k += 1
        if (iterations is not None and k >= iterations) or (iterations is None and time.perf_counter() - t0 >= time_s):
            return phi


def _target(a: np.ndarray) -> Target:
    a64 = np.asarray(a, dtype=np.float64)
    return Target.from_field(a64, a64 > 1e-2 * a64.max())


def evaluate_cgh(models_dir: Path, heldout_path: Path) -> tuple[dict, dict]:
    """``(metrics entry of the schema, detail document)``."""
    gen, kinds, bench, bench_names = heldout.load_cgh(heldout_path)
    targets = list(gen) + list(bench)
    names = [f"gen/{k}" for k in kinds] + [f"bench/{b}" for b in bench_names]
    tg = [_target(a) for a in targets]
    # warm-up, then the production path of every target
    for _ in range(3):
        m17_cgh_net.run(SETUP128, tg[0], budget=Budget(1), rng=Rng(1), models_dir=models_dir)
    ac_net, t_net = [], []
    for a, t in zip(targets, tg):
        ts = []
        for _ in range(3):
            r = m17_cgh_net.run(SETUP128, t, budget=Budget(1), rng=Rng(1), models_dir=models_dir)
            ts.append(r.history[0]["time_s"])
        if r.meta["provenance"] != "real":
            raise RuntimeError("the cgh-net slot is not released in " + str(models_dir))
        ac_net.append(accuracy(a, r.phi))
        t_net.append(float(np.median(ts)))
    budget_s = float(np.median(t_net))
    rows = []
    for i, (a, t) in enumerate(zip(targets, tg)):
        gs_t = m04_gs.run(SETUP128, t, budget=Budget(BIG, budget_s), rng=Rng(1))
        gs30 = m04_gs.run(SETUP128, t, budget=Budget(30), rng=Rng(1))
        gs300 = m04_gs.run(SETUP128, t, budget=Budget(300), rng=Rng(1))
        lean = lean_gs(a, SETUP128, budget_s)
        rows.append({"target": names[i], "ac_net": ac_net[i], "time_net_ms": 1000 * t_net[i],
                     "ac_gs_matched": accuracy(a, gs_t.phi), "gs_matched_iterations": gs_t.meta["iterations"],
                     "ac_gs30": accuracy(a, gs30.phi), "ac_gs300": accuracy(a, gs300.phi), "ac_lean_gs_matched": accuracy(a, lean)})
    ratio = np.array([r["ac_net"] / r["ac_gs_matched"] for r in rows])
    entry = {"held_out_n": len(rows), "accuracy_vs_gs": stat(ratio), "time_ms": stat([1000 * x for x in t_net]), "baseline": "M04"}
    col = lambda k: np.array([r[k] for r in rows])  # noqa: E731
    detail = {
        "slot": "cgh-net", "wall_clock_budget_ms": 1000 * budget_s, "accuracy": "AC, unit-sum intensities, 2 sum(TI) / (sum T^2 + sum I^2)",
        "ac_median": {k: float(np.median(col(k))) for k in ("ac_net", "ac_gs_matched", "ac_gs30", "ac_gs300", "ac_lean_gs_matched")},
        "ratio_vs": {k: stat(col("ac_net") / col(k)) for k in ("ac_gs_matched", "ac_gs30", "ac_gs300", "ac_lean_gs_matched")},
        "share_net_above": {k: float(np.mean(col("ac_net") > col(k))) for k in ("ac_gs_matched", "ac_gs30", "ac_gs300", "ac_lean_gs_matched")},
        "gs_matched_iterations_median": float(np.median(col("gs_matched_iterations"))),
        "gs_lean_iterations_per_second_note": "lean GS runs for the same wall-clock as the network's median inference time",
        "rows": rows,
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
