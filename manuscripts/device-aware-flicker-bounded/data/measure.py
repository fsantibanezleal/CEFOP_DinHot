#!/usr/bin/env python3
"""Measure the device-aware conjugate-gradient refinement of DinHot (B1) and write ``beyond.json``, ``beyond_numbers.tex`` and the tables.

0.02.004: this script measures the static method only. Its flicker-bounded sibling has its own paper and its own data
(``manuscripts/flicker-bounded-sequences/data/measure.py``). B1 runs here at its default, ``weights=False`` (the weight update
is an option, measured as an ablation row), with the real methods of ``data-pipeline/pipeline/model/holo`` on the task and
the grids of its acceptance test (``tests/methods/beyond/test_b1_device_wgs.py``), over more seeds than the test uses. The
closest published method, the normalized-error loss of Schroff et al. 2023, is B1 run with ``loss='normalized-error'``
(same warm start, device model, conjugate gradient and safeguard) and is measured on the acceptance task, on the full device
and, in ``b1_weights_geo.py``, on the benchmark lattices. The committed baked artifacts (``data/derived/manifests``) and the
benchmark ``data/derived/benchmark/results.json`` (contract benchmark-results 2.0.0, read through ``require_contract``) are
read, never re-run. Nothing in the text of the manuscript is typed: every number comes from ``beyond.json`` through the
macros of ``beyond_numbers.tex`` and the table files.

Outputs, per part: ``bs1`` and ``bs1_full`` (the acceptance task on the crosstalk device and the full device: the default, the
published baselines, the Schroff loss, per-hologram seconds), ``ablation`` (components of B1 including ``weights`` on), and
the benchmark rows (``tab_bench.tex``: n per cell, the win rule of ``extract_methods.cell_result`` at the time row, the
per-hologram time on the device of every method compared; ``tab_schroff.tex``: the closest published method).

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/device-aware-flicker-bounded/data/measure.py [--seeds-b1 5] [--seeds-b1-full 5]

Deterministic: every method takes a seed through the portable generator, so a rerun gives the same numbers up to the
floating point of the machine's FFT (times are wall clock and differ; they are measured on an idle machine).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.model.holo.core.device import Device, device_focal_field  # noqa: E402
from pipeline.model.holo.core.forward import (  # noqa: E402
    fft_focal_field,
    point_trap_backproject,
    point_trap_projection,
    slm_field,
    trap_fields_from_fft,
)
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude  # noqa: E402
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import TrapSet, square_grid  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.baseline import m04_gs, m06_gsw, m07_phase_fixed_wgs  # noqa: E402
from pipeline.model.holo.methods.beyond import b1_device_wgs as B1  # noqa: E402

CROSSTALK_DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)
FULL_DEVICE = Device(bit_depth=4, crosstalk=(1.24, 1.80), upsample=3, fill_factor=0.85)


def make_setup(n_pix: int = 256, pad: int = 2) -> Setup:
    """The setup of the acceptance tests: 12.5 um pitch, f = 250 mm, 850 nm, Gaussian beam of waist 1 (tests e3_helpers)."""
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n_pix, pitch_m=12.5e-6, pad=pad,
                 beam="gaussian")


def bin_grid(setup: Setup, nx: int, ny: int, spacing_bins: float) -> TrapSet:
    return square_grid(nx, ny, spacing_bins * focal_bin_m(setup) * 1e6)


def device_scores(phi: np.ndarray, setup: Setup, traps: TrapSet, device: Device | None) -> tuple[float, float]:
    """Efficiency and relative standard deviation (percent) of a hologram displayed on ``device`` (None: ideal)."""
    if device is None:
        field = fft_focal_field(phi, setup)
    else:
        field = device_focal_field(phi, setup, device, None)
    v = trap_fields_from_fft(field, setup, traps)
    return efficiency(trap_intensities(v)), rel_std(trap_intensities(v, traps.weight))


def trap_ratio(phi: np.ndarray, setup: Setup, traps: TrapSet, device: Device | None) -> list[float]:
    """Intensity of every trap divided by the mean, for the scatter figure."""
    field = fft_focal_field(phi, setup) if device is None else device_focal_field(phi, setup, device, None)
    i = trap_intensities(trap_fields_from_fft(field, setup, traps), traps.weight)
    return [float(x) for x in (i / i.mean())]


def stats(values: list[float]) -> dict:
    return {"median": statistics.median(values), "min": min(values), "max": max(values), "n": len(values)}


# ---------------------------------------------------------------- B1

def measure_b1(seeds: list[int], device: Device, label: str, with_baselines: bool) -> dict:
    setup = make_setup(256)
    traps = bin_grid(setup, 10, 10, 8)
    target = Target.from_traps(traps)
    rows = []
    for seed in seeds:
        t0 = time.perf_counter()
        row: dict = {"seed": seed}
        base = {}
        for mod in (m07_phase_fixed_wgs, m04_gs, m06_gsw):
            name = mod.SPEC.id  # the engine key of the stored baselines (data/derived keys, never printed)
            is_pf = mod is m07_phase_fixed_wgs  # phase-fixed weighted GS, the reference of the study
            if not is_pf and not with_baselines:
                continue
            for its in (30, 100):
                if not is_pf and its == 100:
                    continue
                tb = time.perf_counter()
                res = mod.run(setup, target, budget=Budget(its), rng=Rng(seed))
                sec = time.perf_counter() - tb
                e, s = device_scores(res.phi, setup, traps, device)
                ei, si = device_scores(res.phi, setup, traps, None)
                base[f"{name}_{its}"] = {"eff": e, "sigma": s, "eff_ideal": ei, "sigma_ideal": si, "seconds": sec}
                if is_pf and its == 30 and seed == seeds[0]:
                    row["ratios_M07"] = trap_ratio(res.phi, setup, traps, device)
        row["baselines"] = base
        tb = time.perf_counter()
        res = B1.run(setup, target, device=device, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed))  # the default: weights off
        sec = time.perf_counter() - tb
        e, s = device_scores(res.phi, setup, traps, device)
        ei, si = device_scores(res.phi, setup, traps, None)
        row["B1"] = {"eff": e, "sigma": s, "eff_ideal": ei, "sigma_ideal": si, "seconds": sec}
        # the closest published method: the loss of Schroff et al. 2023 through the same warm start, device model, CG and safeguard
        tb = time.perf_counter()
        resn = B1.run(setup, target, device=device, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed), loss="normalized-error")
        secn = time.perf_counter() - tb
        en, sn = device_scores(resn.phi, setup, traps, device)
        row["B1_schroff"] = {"eff": en, "sigma": sn, "seconds": secn}
        if seed == seeds[0]:
            row["ratios_B1"] = trap_ratio(res.phi, setup, traps, device)
            row["B1_history_sigma"] = [float(h["rel_std"]) for h in res.history]
        # ablation: the same loop with the device model removed (the ideal model in the loop), scored on the device
        res0 = B1.run(setup, target, device=None, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed))
        e0, s0 = device_scores(res0.phi, setup, traps, device)
        row["B1_no_device_model"] = {"eff": e0, "sigma": s0}
        row["seconds"] = time.perf_counter() - t0
        rows.append(row)
        print(f"[B1 {label}] seed {seed}: M07_30 sigma {base['M07_30']['sigma']:.3f}, B1 sigma {s:.4f}, "
              f"Schroff {sn:.4f}, no-model {s0:.3f} ({row['seconds']:.0f} s)", flush=True)
    ref_sigma = [min(r["baselines"]["M07_30"]["sigma"], r["baselines"]["M07_100"]["sigma"]) for r in rows]
    ref_eff = [max(r["baselines"]["M07_30"]["eff"], r["baselines"]["M07_100"]["eff"]) for r in rows]
    ratio = [a / r["B1"]["sigma"] for a, r in zip(ref_sigma, rows)]
    eff_ratio = [r["B1"]["eff"] / e for e, r in zip(ref_eff, rows)]
    return {
        "label": label,
        "device": {"bit_depth": device.bit_depth, "crosstalk": list(device.crosstalk), "upsample": device.upsample,
                   "fill_factor": device.fill_factor, "flicker_rad": 0.0},
        "task": "10 x 10 square lattice, 8 bins apart, 256 x 256 pixels padded 2, Gaussian beam",
        "rows": rows,
        "summary": {
            "sigma_b1": stats([r["B1"]["sigma"] for r in rows]),
            "sigma_m07_30": stats([r["baselines"]["M07_30"]["sigma"] for r in rows]),
            "sigma_m07_100": stats([r["baselines"]["M07_100"]["sigma"] for r in rows]),
            "sigma_no_model": stats([r["B1_no_device_model"]["sigma"] for r in rows]),
            "eff_b1": stats([r["B1"]["eff"] for r in rows]),
            "sigma_schroff": stats([r["B1_schroff"]["sigma"] for r in rows]),
            "eff_schroff": stats([r["B1_schroff"]["eff"] for r in rows]),
            "eff_ratio_schroff": stats([r["B1_schroff"]["eff"] / e for e, r in zip(ref_eff, rows)]),
            "seconds_b1": stats([r["B1"]["seconds"] for r in rows]),
            "seconds_schroff": stats([r["B1_schroff"]["seconds"] for r in rows]),
            "seconds_m07_30": stats([r["baselines"]["M07_30"]["seconds"] for r in rows]),
            "seconds_m07_100": stats([r["baselines"]["M07_100"]["seconds"] for r in rows]),
            "eff_m07_30": stats([r["baselines"]["M07_30"]["eff"] for r in rows]),
            "sigma_ratio": stats(ratio),
            "eff_ratio": stats(eff_ratio),
            "sigma_m07_ideal_30": stats([r["baselines"]["M07_30"]["sigma_ideal"] for r in rows]),
            "sigma_b1_ideal": stats([r["B1"]["sigma_ideal"] for r in rows]),
            **({"sigma_m04_30": stats([r["baselines"]["M04_30"]["sigma"] for r in rows]),
                "sigma_m06_30": stats([r["baselines"]["M06_30"]["sigma"] for r in rows]),
                "seconds_m04_30": stats([r["baselines"]["M04_30"]["seconds"] for r in rows]),
                "seconds_m06_30": stats([r["baselines"]["M06_30"]["seconds"] for r in rows])} if with_baselines else {}),
        },
    }


# ---------------------------------------------------------------- ablation (content bar, 2026-11-03)

T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}  # two-sided 95 percent t quantiles


def stats2(values: list[float]) -> dict:
    """Median, range, mean, sample standard deviation and the two-sided 95 percent t interval of the mean."""
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    half = T95.get(n - 1, 1.96) * sd / n ** 0.5 if n > 1 else float("nan")
    return {"median": statistics.median(values), "min": min(values), "max": max(values), "n": n, "mean": mean, "sd": sd,
            "ci_lo": mean - half, "ci_hi": mean + half}


def geo_ci(values: list[float]) -> dict:
    """Geometric mean of positive ratios with the 95 percent t interval on the log scale (the factor is a ratio)."""
    import math  # noqa: PLC0415

    st = stats2([math.log(v) for v in values])
    return {"gm": math.exp(st["mean"]), "lo": math.exp(st["ci_lo"]), "hi": math.exp(st["ci_hi"]), "n": st["n"]}


def b1_variant(setup: Setup, target: Target, device: Device | None, iters: int, rng: Rng, *, weights: bool = False,
               device_step: bool = True, safeguard: bool = True, steps: int = B1.DEFAULT_STEPS,
               warm: int = B1.DEFAULT_WARM) -> np.ndarray:
    """The loop of ``B1.run`` with its components switchable: ``weights`` (the multiplicative weight update), ``device_step``
    (the conjugate-gradient steps on the device-aware loss; off: the projection of weighted GS, with the weights read on the
    device), ``safeguard`` (the best admissible iterate; off: the last one). The default is ``B1.run`` at its default, ``weights=False`` (checked by the ablation); ``weights=True`` is the 0.02.003 form."""
    from pipeline.model.holo.methods.optim import _common as C  # noqa: PLC0415
    from pipeline.model.holo.methods.optim._gs_family import weighted_gs  # noqa: PLC0415

    traps = target.traps
    phi, _ = weighted_gs(setup, traps, warm, rng, variant="gsw")
    cost = C.TrapCost(setup, traps, device, t=2, efficiency=0.9)
    a = np.sqrt(traps.weight / np.mean(traps.weight))
    w = np.ones(len(traps))
    v, _ = cost.fwd.fields(phi)
    start = C.trap_history(0, v, traps.weight, 0.0)
    floor = B1.EFFICIENCY_FLOOR * start["efficiency"]
    best = (phi.copy(), start["rel_std"])
    for it in range(1, iters + 1):
        v, _ = cost.fwd.fields(phi)
        if weights:
            r = np.maximum(np.abs(v), 1e-300) / a
            w = w * np.mean(r) / r
        if device_step:
            amp2 = (w * a) ** 2
            cost.target = float(np.sum(np.abs(v) ** 2)) * amp2 / amp2.sum()
            phi = C.cg_minimize(cost.value_grad, phi, steps).x
        else:
            phi = np.angle(point_trap_backproject(w * a * np.exp(1j * np.angle(v)), setup, traps))
        v, _ = cost.fwd.fields(phi)
        entry = C.trap_history(it, v, traps.weight, 0.0)
        if entry["efficiency"] >= floor and entry["rel_std"] < best[1]:
            best = (phi.copy(), entry["rel_std"])
    return np.mod(best[0] if safeguard else phi, 2.0 * np.pi)


B1_VARIANTS = {  # key: (label, keyword arguments of b1_variant, device used inside the loop)
    "full": ("device-aware refinement, default (no weight update)", {}, True),
    "weights": ("with the weight update (the 0.02.003 form)", {"weights": True}, True),
    "no_step": ("without the device-aware phase step", {"device_step": False}, True),
    "no_guard": ("without the best-iterate safeguard", {"safeguard": False}, True),
    "no_model": ("device model removed from the loop", {}, False),
    "steps_1": ("1 conjugate-gradient step per iteration", {"steps": 1}, True),
    "steps_6": ("6 conjugate-gradient steps per iteration", {"steps": 6}, True),
}


def ablate_b1(seeds: list[int], device: Device, variants: list[str], label: str) -> dict:
    from pipeline.model.holo.methods.optim._gs_family import weighted_gs  # noqa: PLC0415

    setup = make_setup(256)
    traps = bin_grid(setup, 10, 10, 8)
    target = Target.from_traps(traps)
    rows = []
    for seed in seeds:
        t0 = time.perf_counter()
        row: dict = {"seed": seed}
        for key in variants:
            _, kw, in_loop = B1_VARIANTS[key]
            phi = b1_variant(setup, target, device if in_loop else None, B1.DEFAULT_OUTER, Rng(seed), **kw)
            e, s = device_scores(phi, setup, traps, device)
            row[key] = {"eff": e, "sigma": s}
        p0, _ = weighted_gs(setup, traps, B1.DEFAULT_WARM, Rng(seed), variant="gsw")
        e0, s0 = device_scores(p0, setup, traps, device)
        row["warm_only"] = {"eff": e0, "sigma": s0}
        ref = B1.run(setup, target, device=device, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed))
        row["check_full_vs_b1run"] = abs(device_scores(ref.phi, setup, traps, device)[1] - row["full"]["sigma"])
        if "weights" in variants:
            refw = B1.run(setup, target, device=device, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed), weights=True)
            row["check_weights_vs_b1run"] = abs(device_scores(refw.phi, setup, traps, device)[1] - row["weights"]["sigma"])
        base = {its: device_scores(m07_phase_fixed_wgs.run(setup, target, budget=Budget(its), rng=Rng(seed)).phi, setup, traps, device)
                for its in (30, 100)}
        row["ref_sigma"] = min(base[30][1], base[100][1])
        row["ref_eff"] = max(base[30][0], base[100][0])
        row["seconds"] = time.perf_counter() - t0
        rows.append(row)
        print(f"[ablation B1 {label}] seed {seed}: " + ", ".join(f"{k} {row[k]['sigma']:.3f}" for k in variants)
              + f" ({row['seconds']:.0f} s)", flush=True)
    summary = {}
    for key in [*variants, "warm_only"]:
        fac = [r["ref_sigma"] / r[key]["sigma"] for r in rows]
        summary[key] = {"sigma": stats2([r[key]["sigma"] for r in rows]), "factor": geo_ci(fac),
                        "factor_median": statistics.median(fac),
                        "eff_ratio": stats2([r[key]["eff"] / r["ref_eff"] for r in rows])}
    return {"label": label, "variants": variants, "rows": rows, "summary": summary,
            "max_check_full_vs_b1run": max(r["check_full_vs_b1run"] for r in rows),
            "max_check_weights_vs_b1run": max((r.get("check_weights_vs_b1run", 0.0) for r in rows), default=0.0)}


def measure_ablation(seeds_b1: int, seeds_b1_full: int) -> dict:
    return {"b1_crosstalk": ablate_b1(list(range(1, seeds_b1 + 1)), CROSSTALK_DEVICE, list(B1_VARIANTS), "crosstalk device"),
            "b1_full": ablate_b1(list(range(1, seeds_b1_full + 1)), FULL_DEVICE,
                                 ["full", "weights", "no_step", "no_guard", "no_model"], "full device")}


# ---------------------------------------------------------------- committed artifacts

def read_manifests() -> dict:
    """Per-method scores of the committed bake for the two cases that carry the claims (C08 and C10)."""
    out = {}
    for cid in ("C08_device_limited", "C10_rearrangement"):
        m = json.loads((ROOT / "data" / "derived" / "manifests" / f"{cid}.json").read_text(encoding="utf-8"))
        out[cid] = {
            "engine_version": m["engine"]["version"], "seed": m["seed"],
            "params": {"n_pix": m["params"]["setup"]["n_pix"], "bit_depth": m["params"]["device"] and m["params"]["device"]["bit_depth"],
                       "fill_factor": m["params"]["device"] and m["params"]["device"]["fill_factor"],
                       "flicker_rad": m["params"]["device"] and m["params"]["device"]["flicker_rad"],
                       "budget_iterations": m["params"]["budget"]["iterations"],
                       "n_traps": len(m["params"]["target"]["traps"])},
            "methods": {k: {a: v[a] for a in ("efficiency", "uniformity", "rel_std_pct", "iterations")}
                        for k, v in m["methods"].items()},
        }
    rng = json.loads((ROOT / "data-pipeline" / "pipeline" / "cases" / "measured_ranges.json").read_text(encoding="utf-8"))
    mr = rng["measured"]["C08_device_limited"]
    out["C08_device_limited"]["seeds_ratio"] = [a / b for a, b in zip(mr["M07.rel_std_pct"], mr["B1.rel_std_pct"])]
    out["C08_device_limited"]["seeds_mean_ratio"] = statistics.mean(mr["M07.rel_std_pct"]) / statistics.mean(mr["B1.rel_std_pct"])
    return out


def _studio_rule():
    """The win rule of the benchmark, implemented once in the technical report's ``extract_methods.py`` (``cell_result``, ``require_contract``)."""
    sys.path.insert(0, str(HERE.parents[1] / "holographic-trap-studio" / "data"))
    import extract_methods as X  # noqa: PLC0415

    return X


def read_benchmark(budget: int = 100) -> dict:
    """Device-aware refinement in the studio's benchmark (``data/derived/benchmark/results.json``, contract 2.0.0): on every geometry where
    both ran, the factor of B1 over phase-fixed WGS on the relative standard deviation and the efficiency ratio at ``budget`` iterations
    with the default parameters (each method at its own iterations, never read as a win), the seeds behind each cell, the time per
    hologram of every method the paper compares (median of its iteration rows), and the reading of the cell at the equal-wall-clock
    time row by the rule of ``extract_methods.cell_result`` (at least 5 seeds each side, interquartile ranges that do not overlap, a gap
    of 0.01 percentage points), on the C08 device and on the ideal device."""
    X = _studio_rule()
    r = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    X.require_contract(r, "device-aware measure.py")
    pf = m07_phase_fixed_wgs.SPEC.id  # the engine key of the reference method in the benchmark document
    compared = (m04_gs.SPEC.id, m06_gsw.SPEC.id, pf, "B1")
    cells = {(x["method"], x["geometry"], x["device"]): x for x in r["rows"]
             if x["budget_kind"] == "iterations" and x["budget"] == budget and x["params"] == "default"}
    read_time = max(r["protocol"]["budgets"]["time_s"])
    tcells = {(x["method"], x["geometry"], x["device"]): x for x in r["rows"]
              if x["budget_kind"] == "time" and x["budget"] == read_time and x["params"] == "default"}
    names = {g["id"]: g["name"]["en"] for g in r["geometries"]}
    ntraps = {g["id"]: g["n_traps"] for g in r["geometries"]}
    out = {"budget": budget, "time_budget_s": read_time, "win_min_seeds": X.WIN_MIN_SEEDS, "win_min_diff_pct": X.WIN_MIN_DIFF_PCT,
           "schema": r["schema"], "engine_version": r["engine_version"], "devices": {}}
    for device in ("device", "ideal"):
        rows = []
        for (m, g, d), b1 in sorted(cells.items()):
            if m != "B1" or d != device or (pf, g, d) not in cells:
                continue
            m7 = cells[(pf, g, d)]
            t_b1, t_m7 = tcells.get(("B1", g, d)), tcells.get((pf, g, d))
            reading = (X.cell_result([{**t_b1, "budget_kind": "time"}, {**t_m7, "budget_kind": "time"}])
                       if t_b1 and t_m7 else {"result": "tie", "reason": "a method has no time row in this cell"})
            rows.append({"geometry": g, "name": names[g], "n_traps": ntraps[g],
                         "n_seeds": min(b1["n_seeds"], m7["n_seeds"]), "n_seeds_b1": b1["n_seeds"], "n_seeds_m07": m7["n_seeds"],
                         "sigma_b1": b1["rel_std_pct"]["median"], "sigma_m07": m7["rel_std_pct"]["median"],
                         "sigma_b1_iqr": [b1["rel_std_pct"]["q1"], b1["rel_std_pct"]["q3"]],
                         "sigma_m07_iqr": [m7["rel_std_pct"]["q1"], m7["rel_std_pct"]["q3"]],
                         "factor": m7["rel_std_pct"]["median"] / max(b1["rel_std_pct"]["median"], 1e-6),
                         "eff_ratio": b1["efficiency"]["median"] / m7["efficiency"]["median"],
                         "seconds": {k: cells[(k, g, d)]["time_s"]["median"] for k in compared if (k, g, d) in cells},
                         "n_seeds_by_method": {k: cells[(k, g, d)]["n_seeds"] for k in compared if (k, g, d) in cells},
                         "time_row": {"n_b1": t_b1["n_seeds"] if t_b1 else 0, "n_m07": t_m7["n_seeds"] if t_m7 else 0,
                                      "sigma_b1": t_b1["rel_std_pct"]["median"] if t_b1 else None,
                                      "sigma_m07": t_m7["rel_std_pct"]["median"] if t_m7 else None,
                                      "reading": reading["result"], "reason": reading.get("reason", "")}})
        out["devices"][device] = rows
    return out


def macro(name: str, value: str) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def fmt(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def write_macros(data: dict, path: Path) -> None:
    b1 = data["bs1_crosstalk"]["summary"]
    b1f = data["bs1_full_device"]["summary"]
    man = data["bake"]
    L = ["% Generated by data/measure.py from beyond.json. Do not edit.\n"]
    L.append(macro("nSeedsOne", str(b1["sigma_b1"]["n"])))
    L.append(macro("nSeedsOneFull", str(b1f["sigma_b1"]["n"])))
    L.append(macro("sigmaBOne", fmt(b1["sigma_b1"]["median"], 3)))
    L.append(macro("sigmaBOneMax", fmt(b1["sigma_b1"]["max"], 3)))
    L.append(macro("sigmaMsevenThirty", fmt(b1["sigma_m07_30"]["median"], 2)))
    L.append(macro("sigmaMsevenHundred", fmt(b1["sigma_m07_100"]["median"], 2)))
    L.append(macro("sigmaNoModel", fmt(b1["sigma_no_model"]["median"], 2)))
    L.append(macro("sigmaMfour", fmt(b1["sigma_m04_30"]["median"], 1)))
    L.append(macro("sigmaMsix", fmt(b1["sigma_m06_30"]["median"], 1)))
    L.append(macro("sigmaMsevenIdeal", fmt(b1["sigma_m07_ideal_30"]["median"], 3)))
    L.append(macro("costXtalk", fmt(b1["sigma_m07_30"]["median"] / b1["sigma_m07_ideal_30"]["median"], 0)))
    L.append(macro("sigmaBOneIdeal", fmt(b1["sigma_b1_ideal"]["median"], 2)))
    L.append(macro("ratioOneMed", fmt(b1["sigma_ratio"]["median"], 0)))
    L.append(macro("ratioOneMin", fmt(b1["sigma_ratio"]["min"], 0)))
    L.append(macro("ratioOneMax", fmt(b1["sigma_ratio"]["max"], 0)))
    L.append(macro("effBOne", fmt(b1["eff_b1"]["median"], 3)))
    L.append(macro("effMseven", fmt(b1["eff_m07_30"]["median"], 3)))
    L.append(macro("effRatioOne", fmt(b1["eff_ratio"]["median"], 3)))
    L.append(macro("effRatioOneMin", fmt(b1["eff_ratio"]["min"], 3)))
    st = make_setup(256)
    L.append(macro("parLambda", f"{st.wavelength_m * 1e9:.0f}"))
    L.append(macro("parFocal", f"{st.focal_m * 1e3:.0f}"))
    L.append(macro("parPitch", f"{st.pitch_m * 1e6:.1f}"))
    L.append(macro("parNpix", st.n_pix))
    L.append(macro("parPad", st.pad))
    L.append(macro("parNa", f"{st.na:g}"))
    L.append(macro("parXtSigma", f"{CROSSTALK_DEVICE.crosstalk[0]:.2f}"))
    L.append(macro("parXtQ", f"{CROSSTALK_DEVICE.crosstalk[1]:.2f}"))
    L.append(macro("parUp", CROSSTALK_DEVICE.upsample))
    L.append(macro("parBits", FULL_DEVICE.bit_depth))
    L.append(macro("parFill", f"{FULL_DEVICE.fill_factor:g}"))
    L.append(macro("parCgSteps", B1.DEFAULT_STEPS))
    L.append(macro("parWarm", B1.DEFAULT_WARM))
    L.append(macro("parOuter", B1.DEFAULT_OUTER))
    L.append(macro("parFloor", f"{B1.EFFICIENCY_FLOOR:g}"))
    L.append(macro("parColdIters", 30))
    L.append(macro("parBaseIters", "30 and 100"))
    r1 = data["bs1_crosstalk"]["rows"][0]
    L.append(macro("seedOneSigmaB", fmt(r1["B1"]["sigma"], 4)))
    L.append(macro("seedOneSigmaM", fmt(r1["baselines"]["M07_30"]["sigma"], 3)))
    L.append(macro("seedOneRatio", fmt(min(r1["baselines"]["M07_30"]["sigma"], r1["baselines"]["M07_100"]["sigma"]) / r1["B1"]["sigma"], 0)))
    L.append(macro("seedOneEffB", fmt(r1["B1"]["eff"], 4)))
    L.append(macro("seedOneEffM", fmt(r1["baselines"]["M07_30"]["eff"], 4)))
    L.append(macro("sigmaBOneFull", fmt(b1f["sigma_b1"]["median"], 2)))
    L.append(macro("sigmaMsevenFull", fmt(b1f["sigma_m07_30"]["median"], 2)))
    L.append(macro("sigmaNoModelFull", fmt(b1f["sigma_no_model"]["median"], 2)))
    L.append(macro("ratioOneFullMed", fmt(b1f["sigma_ratio"]["median"], 1)))
    L.append(macro("ratioOneFullMin", fmt(b1f["sigma_ratio"]["min"], 1)))
    L.append(macro("ratioOneFullMax", fmt(b1f["sigma_ratio"]["max"], 1)))
    L.append(macro("effRatioOneFull", fmt(b1f["eff_ratio"]["median"], 3)))
    # bake
    c8 = man["C08_device_limited"]["methods"]
    L.append(macro("bakeCeightBOneSigma", fmt(c8["B1"]["rel_std_pct"], 2)))
    L.append(macro("bakeCeightMsevenSigma", fmt(c8["M07"]["rel_std_pct"], 2)))
    L.append(macro("bakeCeightRatio", fmt(c8["M07"]["rel_std_pct"] / c8["B1"]["rel_std_pct"], 1)))
    L.append(macro("bakeCeightBOneEff", fmt(c8["B1"]["efficiency"], 3)))
    L.append(macro("bakeCeightMsevenEff", fmt(c8["M07"]["efficiency"], 3)))
    L.append(macro("bakeCeightEffRatio", fmt(c8["B1"]["efficiency"] / c8["M07"]["efficiency"], 3)))
    L.append(macro("bakeCeightIters", str(man["C08_device_limited"]["params"]["budget_iterations"])))
    L.append(macro("bakeCeightTraps", str(man["C08_device_limited"]["params"]["n_traps"])))
    L.append(macro("bakeCeightPix", str(man["C08_device_limited"]["params"]["n_pix"])))
    c8m = man["C08_device_limited"]
    L.append(macro("bakeCeightFlicker", f"{c8m['params']['flicker_rad']:g}"))
    L.append(macro("bakeCeightRatioThree", fmt(c8m["seeds_mean_ratio"], 1)))
    sr = c8m["seeds_ratio"]
    L.append(macro("bakeCeightSeedRatios", ", ".join(fmt(x, 3) for x in sr[:-1]) + f" and {fmt(sr[-1], 3)}"))
    L.append(macro("bakeCeightSeedsTwo", sum(1 for x in sr if x >= 2)))
    L.append(macro("bakeCeightSeedsN", len(sr)))
    # B1 in the studio's benchmark, on the C08 device
    bb = data["benchmark_bs1"]
    dev = bb["devices"]["device"]
    L.append(macro("benchOneBudget", bb["budget"]))
    L.append(macro("benchOneDevN", len(dev)))
    if dev:
        fac = [x["factor"] for x in dev]
        eff = [x["eff_ratio"] for x in dev]
        L.append(macro("benchOneDevMed", fmt(statistics.median(fac), 2)))
        L.append(macro("benchOneDevMin", fmt(min(fac), 2)))
        L.append(macro("benchOneDevMax", fmt(max(fac), 2)))
        L.append(macro("benchOneDevEff", fmt(statistics.median(eff), 3)))
        L.append(macro("benchOneDevPass", sum(1 for x in dev if x["factor"] >= 2 and x["eff_ratio"] >= 0.9)))
        lo, hi = min(x["n_seeds_b1"] for x in dev), max(x["n_seeds_b1"] for x in dev)
        L.append(macro("benchOneDevSeeds", str(lo) if lo == hi else f"{lo} to {hi}"))
        m7 = sorted({x["n_seeds_m07"] for x in dev})
        common = max(m7, key=lambda s: sum(1 for x in dev if x["n_seeds_m07"] == s))
        other = [f"{x['n_seeds_m07']} on {x['geometry']}" for x in dev if x["n_seeds_m07"] != common]
        L.append(macro("benchOneDevSeedsMseven", f"{common}" + (f" ({', '.join(other)})" if other else "")))
        items = [f"{x['geometry']} {fmt(x['factor'], 2)}" for x in dev]
        L.append(macro("benchOneDevList", ", ".join(items[:-1]) + f" and {items[-1]}"))
        L.append(macro("benchOneDevLastFactor", f"a factor of {fmt(dev[-1]['factor'], 2)}"))  # the large set is the last geometry
    path.write_text("".join(L), encoding="utf-8")


CAMEL = {"full": "Full", "weights": "Weights", "no_step": "NoStep", "no_guard": "NoGuard", "no_model": "NoModel",
         "steps_1": "StepsOne", "steps_6": "StepsSix", "warm_only": "Warm", "no_lock": "NoLock", "no_opt": "NoOpt",
         "iters_1": "ItersOne", "iters_3": "ItersThree", "linear": "Linear"}


def write_extra_macros(data: dict, path: Path) -> None:
    """Macros of the intervals of the main results and of the ablation, appended to ``beyond_numbers.tex``."""
    L = ["% Intervals and ablation (data/measure.py, from beyond.json).\n"]
    L.append(macro("engineRelease", data["engine_version"]))
    # B1 main result with its interval: the factor of each seed is the baseline's best spread over B1's, geometric mean
    for key, pre in (("bs1_crosstalk", "ratioOne"), ("bs1_full_device", "ratioOneFull")):
        rows = data[key]["rows"]
        fac = [min(r["baselines"]["M07_30"]["sigma"], r["baselines"]["M07_100"]["sigma"]) / r["B1"]["sigma"] for r in rows]
        g = geo_ci(fac)
        L.append(macro(pre + "Gm", fmt(g["gm"], 1)))
        L.append(macro(pre + "CiLo", fmt(g["lo"], 1)))
        L.append(macro(pre + "CiHi", fmt(g["hi"], 1)))
        sg = stats2([r["B1"]["sigma"] for r in rows])
        L.append(macro(pre.replace("ratio", "sigma") + "Sd", fmt(sg["sd"], 3)))
        L.append(macro(pre.replace("ratio", "sigma") + "Mean", fmt(sg["mean"], 3)))
    # the closest published method (Schroff et al. 2023: B1 with loss='normalized-error') and the cost in time, per device
    for key, pre in (("bs1_crosstalk", "schroffX"), ("bs1_full_device", "schroffF")):
        sm = data[key]["summary"]
        rows = data[key]["rows"]
        fac = [min(r["baselines"]["M07_30"]["sigma"], r["baselines"]["M07_100"]["sigma"]) / r["B1_schroff"]["sigma"] for r in rows]
        g = geo_ci(fac)
        L.append(macro(pre + "N", len(rows)))
        L.append(macro(pre + "Sig", fmt(sm["sigma_schroff"]["median"], 3)))
        L.append(macro(pre + "SigMin", fmt(sm["sigma_schroff"]["min"], 3)))
        L.append(macro(pre + "SigMax", fmt(sm["sigma_schroff"]["max"], 3)))
        L.append(macro(pre + "Fac", fmt(g["gm"], 1)))
        L.append(macro(pre + "FacLo", fmt(g["lo"], 1)))
        L.append(macro(pre + "FacHi", fmt(g["hi"], 1)))
        L.append(macro(pre + "EffRatio", fmt(sm["eff_ratio_schroff"]["median"], 3)))
        L.append(macro(pre + "EffRatioMin", fmt(sm["eff_ratio_schroff"]["min"], 3)))
        L.append(macro(pre + "Seconds", fmt(sm["seconds_schroff"]["median"], 0)))
        L.append(macro(pre + "BeatsDefault", sum(1 for r in rows if r["B1_schroff"]["sigma"] < r["B1"]["sigma"])))
        L.append(macro(pre + "DefaultBeats", sum(1 for r in rows if r["B1"]["sigma"] < r["B1_schroff"]["sigma"])))
        L.append(macro(pre + "Ratio", fmt(sm["sigma_schroff"]["median"] / sm["sigma_b1"]["median"], 1)))  # Schroff spread over the default's
        L.append(macro(pre.replace("schroff", "secB") + "Median", fmt(sm["seconds_b1"]["median"], 0)))
        L.append(macro(pre.replace("schroff", "secM") + "SevenHundred", fmt(sm["seconds_m07_100"]["median"], 2)))
    sm = data["bs1_crosstalk"]["summary"]
    L.append(macro("secMfourThirty", fmt(sm["seconds_m04_30"]["median"], 2)))
    L.append(macro("secMsixThirty", fmt(sm["seconds_m06_30"]["median"], 2)))
    L.append(macro("secMsevenThirty", fmt(sm["seconds_m07_30"]["median"], 2)))
    bb = data["benchmark_bs1"]
    L.append(macro("benchOneWinMinSeeds", bb["win_min_seeds"]))
    L.append(macro("benchOneWinMinDiff", f"{bb['win_min_diff_pct']:g}"))
    L.append(macro("benchOneTimeBudget", f"{bb['time_budget_s']:g}"))
    for dev_key, nm in (("device", "Dev"), ("ideal", "Ideal")):
        rows = bb["devices"][dev_key]
        L.append(macro(f"benchOne{nm}IterBelowFive", sum(1 for x in rows if x["n_seeds"] < bb["win_min_seeds"])))
        L.append(macro(f"benchOne{nm}Cells", len(rows)))
        for rd in ("proposed", "published", "tie"):
            L.append(macro(f"benchOne{nm}Time{rd.capitalize()}", sum(1 for x in rows if x["time_row"]["reading"] == rd)))
    for x in bb["devices"]["device"]:
        g = "Geo" + {"1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6a": "SixA", "6b": "SixB", "7": "Seven"}[x["geometry"][1:]]
        for k, nm in (("B1", "BOne"), (m07_phase_fixed_wgs.SPEC.id, "Mseven"), (m04_gs.SPEC.id, "Mfour"), (m06_gsw.SPEC.id, "Msix")):
            if k in x["seconds"]:
                L.append(macro(f"benchSec{g}{nm}", fmt(x["seconds"][k], 3 if x["seconds"][k] < 10 else 0)))
        L.append(macro(f"benchTime{g}Reading", x["time_row"]["reading"]))
        L.append(macro(f"benchTime{g}N", f"{x['time_row']['n_b1']} and {x['time_row']['n_m07']}"))
    # the ablation
    ab = data.get("ablation")
    if ab:
        for tag, key in (("B", "b1_crosstalk"), ("BF", "b1_full")):
            for k, v in ab[key]["summary"].items():
                n = f"abl{tag}{CAMEL[k]}"
                L.append(macro(n + "Sig", fmt(v["sigma"]["median"], 3)))
                L.append(macro(n + "SigMin", fmt(v["sigma"]["min"], 3)))
                L.append(macro(n + "SigMax", fmt(v["sigma"]["max"], 3)))
                L.append(macro(n + "Fac", fmt(v["factor"]["gm"], 1)))
                L.append(macro(n + "FacLo", fmt(v["factor"]["lo"], 1)))
                L.append(macro(n + "FacHi", fmt(v["factor"]["hi"], 1)))
                L.append(macro(n + "Eff", fmt(v["eff_ratio"]["median"], 3)))
            L.append(macro(f"abl{tag}N", ab[key]["summary"]["full"]["sigma"]["n"]))
            L.append(macro(f"abl{tag}Check", f"{ab[key]['max_check_full_vs_b1run']:.1e}"))
        for tag, key in (("B", "b1_crosstalk"), ("BF", "b1_full")):
            sm = ab[key]["summary"]
            L.append(macro(f"abl{tag}WeightsRatio", fmt(sm["weights"]["sigma"]["median"] / sm["full"]["sigma"]["median"], 0)))  # spread with the update over the default
            L.append(macro(f"abl{tag}WeightsCheck", f"{ab[key]['max_check_weights_vs_b1run']:.1e}"))
            full = sm["full"]  # 0.02.003 name of the default row: the variant without the update (the paper's text reads these names until it is revised)
            for suf, val in (("Sig", fmt(full["sigma"]["median"], 3)), ("SigMin", fmt(full["sigma"]["min"], 3)),
                             ("SigMax", fmt(full["sigma"]["max"], 3)), ("Fac", fmt(full["factor"]["gm"], 1)),
                             ("FacLo", fmt(full["factor"]["lo"], 1)), ("FacHi", fmt(full["factor"]["hi"], 1)),
                             ("Eff", fmt(full["eff_ratio"]["median"], 3))):
                L.append(macro(f"abl{tag}NoWeights{suf}", val))
            L.append(macro(f"abl{tag}StepRatio", fmt(sm["no_step"]["sigma"]["median"] / sm["full"]["sigma"]["median"], 0)))
            L.append(macro(f"abl{tag}ModelRatio", fmt(sm["no_model"]["sigma"]["median"] / sm["full"]["sigma"]["median"], 0)))
        L.append(macro("ablSeconds", fmt(sum(r["seconds"] for k in ("b1_crosstalk", "b1_full") for r in ab[k]["rows"]) / 60.0, 0)))
    main_s = sum(r["seconds"] for k in ("bs1_crosstalk", "bs1_full_device") for r in data[k]["rows"])
    L.append(macro("mainMinutes", fmt(main_s / 60.0, 0)))  # wall-clock of the main measurements, without the long moves and the ablation
    path.open("a", encoding="utf-8").write("".join(L))


def row_cells(cells: list[str]) -> str:
    return " & ".join(cells) + " \\\\\n"


def write_tables(data: dict, out: Path) -> None:
    """The result tables of the manuscript as ``tabular`` files, written from ``beyond.json``."""
    ab = data.get("ablation")
    if ab:
        for tag, key, fname in (("", "b1_crosstalk", "tab_abl_b1.tex"), ("F", "b1_full", "tab_abl_b1_full.tex")):
            d = ab[key]
            L = ["\\begin{tabular}{@{}l r r r r@{}}\n\\toprule\n",
                 row_cells(["Variant", "$\\sigma$ median (\\%)", "$\\sigma$ range (\\%)", "Factor over phase-fixed WGS, 95\\% interval", "$e$ ratio"]),
                 "\\midrule\n"]
            for k in [*d["variants"], "warm_only"]:
                v = d["summary"][k]
                label = "warm start only (no iteration)" if k == "warm_only" else B1_VARIANTS[k][0]
                L.append(row_cells([label, fmt(v["sigma"]["median"], 3), f"{fmt(v['sigma']['min'], 3)} to {fmt(v['sigma']['max'], 3)}",
                                    f"{fmt(v['factor']['gm'], 1)} ({fmt(v['factor']['lo'], 1)} to {fmt(v['factor']['hi'], 1)})",
                                    fmt(v["eff_ratio"]["median"], 3)]))
            L.append("\\bottomrule\n\\end{tabular}\n")
            (out / fname).write_text("".join(L), encoding="utf-8")
    # benchmark, B1 against M07 on the C08 device: n per cell, the factor at each method's own 100 iterations (never a win), the time
    # per hologram of every method compared, and the reading at the equal-wall-clock row by the rule of extract_methods.cell_result
    bb = data["benchmark_bs1"]
    L = ["\\begin{tabular}{@{}l r r r r r r r r r r@{}}\n\\toprule\n",
         row_cells(["Geometry", "Traps", "$n$ device-aware, phase-fixed (100 it.)", "$\\sigma$ phase-fixed WGS (\\%)", "$\\sigma$ device-aware (\\%)",
                    "Factor", "$e$ ratio", "Time per hologram (s): GS, WGS, phase-fixed, device-aware",
                    f"$n$ at {bb['time_budget_s']:g}~s", "Reading at equal time", "Both thresholds"]),
         "\\midrule\n"]
    for x in bb["devices"]["device"]:
        ok = x["factor"] >= 2 and x["eff_ratio"] >= 0.9
        sec = x["seconds"]
        ids = (m04_gs.SPEC.id, m06_gsw.SPEC.id, m07_phase_fixed_wgs.SPEC.id, "B1")
        secs = ", ".join((f"{sec[k]:.3g}" if sec[k] < 100 else f"{sec[k]:.0f}") if k in sec else "n/a" for k in ids)
        L.append(row_cells([f"{x['geometry']} {x['name']}", str(x["n_traps"]), f"{x['n_seeds_b1']}, {x['n_seeds_m07']}",
                            f"{fmt(x['sigma_m07'], 2)} ({fmt(x['sigma_m07_iqr'][0], 2)} to {fmt(x['sigma_m07_iqr'][1], 2)})",
                            f"{fmt(x['sigma_b1'], 2)} ({fmt(x['sigma_b1_iqr'][0], 2)} to {fmt(x['sigma_b1_iqr'][1], 2)})",
                            fmt(x["factor"], 2), fmt(x["eff_ratio"], 3), secs,
                            f"{x['time_row']['n_b1']}, {x['time_row']['n_m07']}", x["time_row"]["reading"], "yes" if ok else "no"]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_bench.tex").write_text("".join(L), encoding="utf-8")
    # the closest published method on the acceptance task and the full device
    L = ["\\begin{tabular}{@{}l l r r r r r@{}}\n\\toprule\n",
         row_cells(["Task", "Method", "$n$", "$\\sigma$ median (range) (\\%)", "Factor over phase-fixed WGS, 95\\% interval", "$e$ ratio",
                    "Seconds per hologram"]),
         "\\midrule\n"]
    for key, task in (("bs1_crosstalk", "crosstalk device"), ("bs1_full_device", "4-bit device")):
        rows = data[key]["rows"]
        sm = data[key]["summary"]
        for label, name, sg, ef, sec in (
                ("device-aware refinement (default)", "B1", sm["sigma_b1"], sm["eff_ratio"], sm["seconds_b1"]),
                ("normalized-error loss of Schroff et al.", "B1_schroff", sm["sigma_schroff"], sm["eff_ratio_schroff"], sm["seconds_schroff"])):
            fac = geo_ci([min(r["baselines"]["M07_30"]["sigma"], r["baselines"]["M07_100"]["sigma"]) / r[name]["sigma"] for r in rows])
            L.append(row_cells([task, label, str(len(rows)), f"{fmt(sg['median'], 3)} ({fmt(sg['min'], 3)} to {fmt(sg['max'], 3)})",
                                f"{fmt(fac['gm'], 1)} ({fmt(fac['lo'], 1)} to {fmt(fac['hi'], 1)})", fmt(ef["median"], 3), fmt(sec["median"], 0)]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_schroff.tex").write_text("".join(L), encoding="utf-8")


def write_all(data: dict, out: Path) -> None:
    write_macros(data, out / "beyond_numbers.tex")
    write_extra_macros(data, out / "beyond_numbers.tex")
    write_tables(data, out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds-b1", type=int, default=5)
    ap.add_argument("--seeds-b1-full", type=int, default=5)
    ap.add_argument("--seeds-abl-b1", type=int, default=5)
    ap.add_argument("--seeds-abl-b1-full", type=int, default=5)
    ap.add_argument("--parts", default="bs1,bs1_full,ablation",
                    help="comma-separated parts to measure; the others are kept from the existing beyond.json")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--macros-only", action="store_true", help="rewrite the macro file from an existing beyond.json")
    a = ap.parse_args()
    out = Path(a.out)
    if a.macros_only:
        write_all(json.loads((out / "beyond.json").read_text(encoding="utf-8")), out)
        print("rewrote", out / "beyond_numbers.tex", "and the tables")
        return 0
    parts = {x for x in a.parts.split(",") if x}  # --parts "" re-reads the bake and the benchmark only
    known = {"bs1", "bs1_full", "ablation"}  # the benchmark and the bake are read every run
    if parts - known:
        ap.error(f"unknown parts {sorted(parts - known)}; known: {sorted(known)}")
    data = {} if parts == known else json.loads((out / "beyond.json").read_text(encoding="utf-8"))
    data["engine_version"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if "bs1" in parts:
        data["bs1_crosstalk"] = measure_b1(list(range(1, a.seeds_b1 + 1)), CROSSTALK_DEVICE, "crosstalk device", True)
    if "bs1_full" in parts:
        data["bs1_full_device"] = measure_b1(list(range(1, a.seeds_b1_full + 1)), FULL_DEVICE, "4-bit, crosstalk, fill 0.85", False)
    if "ablation" in parts:
        data["ablation"] = measure_ablation(a.seeds_abl_b1, a.seeds_abl_b1_full)
    data["bake"] = read_manifests()
    data["benchmark_bs1"] = read_benchmark()
    (out / "beyond.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    write_all(data, out)
    print("wrote", out / "beyond.json", out / "beyond_numbers.tex", "and the tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
