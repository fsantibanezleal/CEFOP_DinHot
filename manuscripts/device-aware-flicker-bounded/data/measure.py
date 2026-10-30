#!/usr/bin/env python3
"""Measure the two beyond-the-state-of-the-art claims of DinHot and write ``beyond.json`` and ``beyond_numbers.tex``.

BS-1 (device-aware weighted GS, engine id B1) and BS-2 (flicker-bounded phase-continuous sequence, engine id B2) are
run here with the real methods of ``data-pipeline/pipeline/model/holo`` on the task and the grids of their acceptance
tests (``tests/methods/beyond/test_b1_device_wgs.py`` and ``test_b2_flicker_bounded.py``), over more seeds than the
tests use. The committed baked artifacts (``data/derived/manifests``) are read for the second, smaller grid of the
bake. Nothing in the text of the manuscript is typed: every number comes from ``beyond.json`` through the macros of
``beyond_numbers.tex``.

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/device-aware-flicker-bounded/data/measure.py [--seeds-b1 5] [--seeds-b2 5]

Deterministic: every method takes a seed through the portable generator, so a rerun gives the same numbers up to the
floating point of the machine's FFT.
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
from pipeline.model.holo.methods.beyond import b2_flicker_bounded as B2  # noqa: E402

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


# ---------------------------------------------------------------- BS-1

def measure_b1(seeds: list[int], device: Device, label: str, with_baselines: bool) -> dict:
    setup = make_setup(256)
    traps = bin_grid(setup, 10, 10, 8)
    target = Target.from_traps(traps)
    rows = []
    for seed in seeds:
        t0 = time.perf_counter()
        row: dict = {"seed": seed}
        base = {}
        for name, mod in (("M07", m07_phase_fixed_wgs), ("M04", m04_gs), ("M06", m06_gsw)):
            if name != "M07" and not with_baselines:
                continue
            for its in (30, 100):
                if name != "M07" and its == 100:
                    continue
                res = mod.run(setup, target, budget=Budget(its), rng=Rng(seed))
                e, s = device_scores(res.phi, setup, traps, device)
                ei, si = device_scores(res.phi, setup, traps, None)
                base[f"{name}_{its}"] = {"eff": e, "sigma": s, "eff_ideal": ei, "sigma_ideal": si}
                if name == "M07" and its == 30 and seed == seeds[0]:
                    row["ratios_M07"] = trap_ratio(res.phi, setup, traps, device)
        row["baselines"] = base
        res = B1.run(setup, target, device=device, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(seed))
        e, s = device_scores(res.phi, setup, traps, device)
        ei, si = device_scores(res.phi, setup, traps, None)
        row["B1"] = {"eff": e, "sigma": s, "eff_ideal": ei, "sigma_ideal": si}
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
              f"no-model {s0:.3f} ({row['seconds']:.0f} s)", flush=True)
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
            "eff_m07_30": stats([r["baselines"]["M07_30"]["eff"] for r in rows]),
            "sigma_ratio": stats(ratio),
            "eff_ratio": stats(eff_ratio),
            "sigma_m07_ideal_30": stats([r["baselines"]["M07_30"]["sigma_ideal"] for r in rows]),
            "sigma_b1_ideal": stats([r["B1"]["sigma_ideal"] for r in rows]),
            **({"sigma_m04_30": stats([r["baselines"]["M04_30"]["sigma"] for r in rows]),
                "sigma_m06_30": stats([r["baselines"]["M06_30"]["sigma"] for r in rows])} if with_baselines else {}),
        },
    }


# ---------------------------------------------------------------- BS-2

def lpi(setup: Setup, start: TrapSet, dest: TrapSet, rng: Rng, frames: int):
    """Linear phase interpolation as the test of B2 writes it from arXiv 2501.01391 (independent endpoint holograms)."""
    from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: PLC0415

    pi, _ = G.weighted_gs(setup, start, 30, rng, variant="pfwgs")
    pf, _ = G.weighted_gs(setup, dest, 30, rng, variant="pfwgs")
    vi = point_trap_projection(slm_field(pi, setup), setup, start)
    vf = point_trap_projection(slm_field(pf, setup), setup, dest)

    def at(sf):
        f = sf / (frames - 1)
        return TrapSet(replace(t, x_m=t.x_m + (e.x_m - t.x_m) * f, y_m=t.y_m + (e.y_m - t.y_m) * f)
                       for t, e in zip(start, dest))

    phis = []
    for k in range(frames):
        f = k / (frames - 1)
        amp = np.abs(vi) * (1 - f) + np.abs(vf) * f
        th = np.angle(vi) + B2.wrap_pi(np.angle(vf) - np.angle(vi)) * f
        phis.append(np.mod(np.angle(point_trap_backproject(amp * np.exp(1j * th), setup, at(k))), 2 * np.pi))
    return phis, at


def transient_curve(setup: Setup, phis: list, at, substeps: int = 10) -> np.ndarray:
    """Intensity of every trap at every (frame, sub-frame) instant, the series ``transient_min_ratio`` takes its minimum of."""
    amp = input_amplitude(setup)
    e = [np.exp(1j * p) for p in phis]
    out = []
    for s in range(len(phis)):
        out.append(np.abs(point_trap_projection(amp * e[s], setup, at(float(s)))) ** 2)
        if s < len(phis) - 1:
            for j in range(1, substeps):
                a = j / substeps
                out.append(np.abs(point_trap_projection(amp * ((1.0 - a) * e[s] + a * e[s + 1]), setup, at(s + a))) ** 2)
    return np.array(out)


def task_move(setup: Setup):
    start = bin_grid(setup, 4, 4, 8)
    b = focal_bin_m(setup)
    dest = TrapSet(replace(t, x_m=t.x_m + (4 * b if (i % 4) >= 2 else 0.0)) for i, t in enumerate(start))
    return start, dest


def measure_b2(seeds: list[int], frames_list: list[int]) -> dict:
    setup = make_setup(256)
    start, dest = task_move(setup)
    runs = []
    for frames in frames_list:
        for seed in seeds:
            t0 = time.perf_counter()
            res = B2.run(setup, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest,
                         frames=frames)
            mv = res.meta["moving"]
            assert int(mv.sum()) == 8
            b2_ratio = res.meta["transient_ratio"][mv]
            phis, at = lpi(setup, start, dest, Rng(100 + seed), frames)
            lpi_ratio = B2.transient_min_ratio(setup, phis, at)[mv]
            row = {
                "frames": frames, "seed": seed,
                "b2_min": float(b2_ratio.min()), "b2_mean_of_min": float(b2_ratio.mean()),
                "lpi_min": float(lpi_ratio.min()), "lpi_mean_of_min": float(lpi_ratio.mean()),
                "b2_sigma_frame_max": float(max(h["rel_std"] for h in res.history)),
                "lpi_sigma_frame_max": float(max(
                    rel_std(trap_intensities(point_trap_projection(slm_field(p, setup), setup, at(k)), start.weight))
                    for k, p in enumerate(phis))),
            }
            if frames == 13 and seed == seeds[0]:
                frames_b2 = [np.asarray(f) for f in res.meta["frames"]]
                cur_b = transient_curve(setup, frames_b2, B2.trajectory(start, dest, frames))
                cur_l = transient_curve(setup, phis, at)
                # the curve of the moving trap whose minimum is the lowest in each sequence, normalised by its frame mean
                idx = np.where(mv)[0]
                for name, cur, ratio in (("b2", cur_b, b2_ratio), ("lpi", cur_l, lpi_ratio)):
                    m = int(idx[int(np.argmin(ratio))])
                    fr = np.array([cur[s * 10, m] for s in range(frames)])
                    row[f"curve_{name}"] = [float(x) for x in cur[:, m] / fr.mean()]
                    row[f"curve_{name}_trap"] = m
                # the check that the curve reproduces the module's minimum
                row["curve_check_b2"] = float(abs((cur_b / cur_b[::10][:frames].mean(axis=0)).min(axis=0)[mv].min()
                                                  - b2_ratio.min()))
            row["seconds"] = time.perf_counter() - t0
            runs.append(row)
            print(f"[B2] frames {frames} seed {seed}: B2 {row['b2_min']:.3f}, LPI {row['lpi_min']:.3f} "
                  f"({row['seconds']:.0f} s)", flush=True)
    summary = {}
    for frames in frames_list:
        sel = [r for r in runs if r["frames"] == frames]
        summary[str(frames)] = {
            "b2_min": stats([r["b2_min"] for r in sel]), "lpi_min": stats([r["lpi_min"] for r in sel]),
            "b2_sigma_frame_max": stats([r["b2_sigma_frame_max"] for r in sel]),
            "lpi_sigma_frame_max": stats([r["lpi_sigma_frame_max"] for r in sel]),
        }
    return {
        "task": "4 x 4 lattice at 8 bins, the two right columns move 4 bins in x, 256 x 256 pixels padded 2",
        "moving_traps": 8, "runs": runs, "summary": summary,
    }


def long_move(setup: Setup, bins: int):
    """The acceptance lattice with its two right columns moved ``bins`` focal bins in x, and the moving mask (B2 test)."""
    start = bin_grid(setup, 4, 4, 8)
    b = focal_bin_m(setup)
    dest = TrapSet(replace(t, x_m=t.x_m + (bins * b if (i % 4) >= 2 else 0.0)) for i, t in enumerate(start))
    return start, dest, np.array([(i % 4) >= 2 for i in range(16)])


def c10_plan():
    """Case C10's sort on M16's own plan (the B2 test): the setup, the origin and goal trap sets and the moving mask."""
    from pipeline.cases import build, library  # noqa: PLC0415
    from pipeline.io.contract import read_cases  # noqa: PLC0415
    from pipeline.model.holo.methods.control import m16_rearrangement as M16  # noqa: PLC0415

    rec = next(c for c in read_cases(ROOT / "data" / "examples" / "cases.json") if c["case_id"].startswith("C10"))
    s = build.setup_of(rec)
    sites = {t["id"]: t for t in rec["target"]["traps"]}
    loaded, wanted = library.random_loading(rec), rec["rearrangement"]["target_ids"]
    atoms = build.trapset_of([sites[i] for i in loaded])
    goal = build.trapset_of([sites[i] for i in wanted])
    pick = M16.run(s, Target.from_traps(goal), budget=Budget(30), rng=Rng(1), atoms=atoms, alpha=1.0,
                   max_step_bins=1.25).meta["assignment"]
    origin = TrapSet(replace(t, x_m=atoms.x_m[pick[i]], y_m=atoms.y_m[pick[i]]) for i, t in enumerate(goal))
    moving = np.array([np.hypot(a.x_m - g.x_m, a.y_m - g.y_m) > 0 for a, g in zip(origin, goal)])
    return s, origin, goal, moving


def measure_b2_scope(seeds_long: list[int], seeds_c10: list[int], c10_equal_frames: int = 25) -> dict:
    """The measured limit of BS-2, as its test runs it on more seeds: (a) longer moves of the acceptance lattice (12 and 20 bins,
    64 pixels), end phases from M07 at the destination, at the default frames and at the frames ``frames_for_move`` names; (b)
    case C10's sort on M16's plan (end phases from M07 per seed, LPI on the same assignment) at an equal number of frames and at
    the frames of the move, and the held phases at the equal frames for the first seed."""
    out = {"claim_step_fu": float(B2.CLAIM_STEP_FU), "default_frames": int(B2.DEFAULT_FRAMES), "long": {}}
    s = make_setup(64)
    for bins in (12, 20):
        start, dest, moving = long_move(s, bins)
        n = B2.frames_for_move(s, start, dest)
        rows = []
        for seed in seeds_long:
            end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(dest), budget=Budget(30), rng=Rng(seed)).fields)
            row = {"seed": seed}
            for key, frames in (("default", B2.DEFAULT_FRAMES), ("enough", n)):
                res = B2.run(s, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest, frames=frames,
                             end_phases=end, phase_velocity_max=1.0)
                row[key] = float(res.meta["transient_ratio"][moving].min())
            rows.append(row)
            print(f"[B2 scope] {bins} bins seed {seed}: {B2.DEFAULT_FRAMES} frames {row['default']:.3f}, "
                  f"{n} frames {row['enough']:.3f}", flush=True)
        out["long"][str(bins)] = {"bins": bins, "fourier_units": float(B2.move_fourier_units(s, start, dest)), "frames": int(n),
                                  "rows": rows}
    s, origin, goal, moving = c10_plan()
    n = B2.frames_for_move(s, origin, goal)
    c10 = {"moving": int(moving.sum()), "n_traps": len(goal), "fourier_units": float(B2.move_fourier_units(s, origin, goal)),
           "frames": int(n), "equal_frames": c10_equal_frames,
           "peak_step_equal": float(B2.peak_step_fu(s, origin, goal, c10_equal_frames)), "rows": []}
    held = B2.run(s, Target.from_traps(origin), budget=Budget(30), rng=Rng(seeds_c10[0]), destination=goal,
                  frames=c10_equal_frames)
    c10["held_equal_first_seed"] = float(held.meta["transient_ratio"][moving].min())
    for seed in seeds_c10:
        end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(goal), budget=Budget(30), rng=Rng(seed)).fields)
        row = {"seed": seed}
        for key, frames in (("equal", c10_equal_frames), ("enough", n)):
            res = B2.run(s, Target.from_traps(origin), budget=Budget(30), rng=Rng(seed), destination=goal, frames=frames,
                         end_phases=end, phase_velocity_max=1.0)
            phis, at = lpi(s, origin, goal, Rng(100 + seed), frames)
            row[f"b2_{key}"] = float(res.meta["transient_ratio"][moving].min())
            row[f"lpi_{key}"] = float(B2.transient_min_ratio(s, phis, at)[moving].min())
        c10["rows"].append(row)
        print(f"[B2 scope] C10 seed {seed}: {c10_equal_frames} frames B2 {row['b2_equal']:.3f} LPI {row['lpi_equal']:.3f}; "
              f"{n} frames B2 {row['b2_enough']:.3f} LPI {row['lpi_enough']:.3f}", flush=True)
    out["c10"] = c10
    return out


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
    return out


def read_benchmark(budget: int = 100) -> dict:
    """BS-1 in the studio's benchmark (``data/derived/benchmark/results.json``): on every geometry where both ran, the factor of
    B1 over phase-fixed WGS (M07) on the relative standard deviation and the efficiency ratio, at ``budget`` iterations with the
    default parameters, on the C08 device and on the ideal device."""
    r = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    cells = {(x["method"], x["geometry"], x["device"]): x for x in r["rows"]
             if x["budget_kind"] == "iterations" and x["budget"] == budget and x["params"] == "default"}
    out = {"budget": budget, "devices": {}}
    for device in ("device", "ideal"):
        rows = []
        for (m, g, d), b1 in sorted(cells.items()):
            if m != "B1" or d != device or ("M07", g, d) not in cells:
                continue
            m7 = cells[("M07", g, d)]
            rows.append({"geometry": g, "n_seeds": min(b1["n_seeds"], m7["n_seeds"]),
                         "sigma_b1": b1["rel_std_pct"]["median"], "sigma_m07": m7["rel_std_pct"]["median"],
                         "factor": m7["rel_std_pct"]["median"] / max(b1["rel_std_pct"]["median"], 1e-6),
                         "eff_ratio": b1["efficiency"]["median"] / m7["efficiency"]["median"]})
        out["devices"][device] = rows
    return out


def macro(name: str, value: str) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def fmt(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def write_macros(data: dict, path: Path) -> None:
    b1 = data["bs1_crosstalk"]["summary"]
    b1f = data["bs1_full_device"]["summary"]
    b2 = data["bs2"]["summary"]
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
    L.append(macro("parFrames", B2.DEFAULT_FRAMES))
    L.append(macro("parFrameIters", B2.DEFAULT_FRAME_ITERATIONS))
    L.append(macro("parPhaseVel", f"{B2.DEFAULT_PHASE_VELOCITY_MAX:g}"))
    L.append(macro("parSubsteps", 10))
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
    # BS-2
    s13 = b2["13"]
    L.append(macro("nSeedsTwo", str(s13["b2_min"]["n"])))
    L.append(macro("bTwoMin", fmt(s13["b2_min"]["min"], 3)))
    L.append(macro("bTwoMed", fmt(s13["b2_min"]["median"], 3)))
    L.append(macro("bTwoMax", fmt(s13["b2_min"]["max"], 3)))
    L.append(macro("lpiMin", fmt(s13["lpi_min"]["min"], 3)))
    L.append(macro("lpiMed", fmt(s13["lpi_min"]["median"], 3)))
    L.append(macro("lpiMax", fmt(s13["lpi_min"]["max"], 3)))
    L.append(macro("bTwoSigmaFrame", fmt(s13["b2_sigma_frame_max"]["max"], 2)))
    L.append(macro("lpiSigmaFrameMin", fmt(s13["lpi_sigma_frame_max"]["min"], 0)))
    L.append(macro("lpiSigmaFrameMax", fmt(s13["lpi_sigma_frame_max"]["max"], 0)))
    for fr, nm in (("7", "Seven"), ("25", "TwentyFive")):
        if fr in b2:
            L.append(macro(f"bTwoMed{nm}", fmt(b2[fr]["b2_min"]["median"], 3)))
            L.append(macro(f"bTwoMin{nm}", fmt(b2[fr]["b2_min"]["min"], 3)))
            L.append(macro(f"lpiMed{nm}", fmt(b2[fr]["lpi_min"]["median"], 3)))
            L.append(macro(f"lpiMax{nm}", fmt(b2[fr]["lpi_min"]["max"], 3)))
    # BS-2, the measured scope
    sc = data["bs2_scope"]
    L.append(macro("claimStepFu", f"{sc['claim_step_fu']:g}"))
    L.append(macro("scopeDefaultFrames", sc["default_frames"]))
    shorts = []
    for key, nm in (("12", "A"), ("20", "B")):
        lg = sc["long"][key]
        enough = [r["enough"] for r in lg["rows"]]
        shorts += [r["default"] for r in lg["rows"]]
        L.append(macro(f"long{nm}Bins", lg["bins"]))
        L.append(macro(f"long{nm}Fu", f"{lg['fourier_units']:g}"))
        L.append(macro(f"long{nm}Frames", lg["frames"]))
        L.append(macro(f"long{nm}Med", fmt(statistics.median(enough), 3)))
        L.append(macro(f"long{nm}Met", sum(x >= 0.9 for x in enough)))
        L.append(macro(f"long{nm}Low", fmt(min(enough), 3)))
    L.append(macro("longSeeds", len(sc["long"]["12"]["rows"])))
    L.append(macro("longDefaultMax", fmt(max(shorts), 3)))
    c = sc["c10"]
    rows = c["rows"]
    met = [r["b2_enough"] for r in rows if r["b2_enough"] >= 0.9]
    L.append(macro("cTenMoving", c["moving"]))
    L.append(macro("cTenTraps", c["n_traps"]))
    L.append(macro("cTenFu", fmt(c["fourier_units"], 1)))
    L.append(macro("cTenFrames", c["frames"]))
    L.append(macro("cTenEqual", c["equal_frames"]))
    L.append(macro("cTenPeakEqual", fmt(c["peak_step_equal"], 2)))
    L.append(macro("cTenHeld", fmt(c["held_equal_first_seed"], 3)))
    L.append(macro("cTenSeeds", len(rows)))
    L.append(macro("cTenLpiLeads", sum(r["lpi_equal"] > r["b2_equal"] for r in rows)))
    L.append(macro("cTenBEqualMax", fmt(max(r["b2_equal"] for r in rows), 3)))
    L.append(macro("cTenLEqualMin", fmt(min(r["lpi_equal"] for r in rows), 3)))
    L.append(macro("cTenLEqualMax", fmt(max(r["lpi_equal"] for r in rows), 3)))
    L.append(macro("cTenMet", len(met)))
    L.append(macro("cTenMetMin", fmt(min(met), 3) if met else "n/a"))
    L.append(macro("cTenMetMax", fmt(max(met), 3) if met else "n/a"))
    L.append(macro("cTenMetMed", fmt(statistics.median(met), 3) if met else "n/a"))
    L.append(macro("cTenLowest", fmt(min(r["b2_enough"] for r in rows), 3)))
    L.append(macro("cTenLpiMin", fmt(min(r["lpi_enough"] for r in rows), 3)))
    L.append(macro("cTenLpiMax", fmt(max(r["lpi_enough"] for r in rows), 3)))
    L.append(macro("cTenBLeads", sum(r["b2_enough"] > r["lpi_enough"] for r in rows)))
    # BS-1 in the studio's benchmark, on the C08 device
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
        lo, hi = min(x["n_seeds"] for x in dev), max(x["n_seeds"] for x in dev)
        L.append(macro("benchOneDevSeeds", str(lo) if lo == hi else f"{lo} to {hi}"))
    path.write_text("".join(L), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds-b1", type=int, default=5)
    ap.add_argument("--seeds-b1-full", type=int, default=3)
    ap.add_argument("--seeds-b2", type=int, default=5)
    ap.add_argument("--frames", type=int, nargs="+", default=[13, 7, 25])
    ap.add_argument("--seeds-long", type=int, default=8, help="seeds of the long lattice moves (BS-2 scope)")
    ap.add_argument("--seeds-c10", type=int, default=6, help="seeds of C10's sort on M16's plan (BS-2 scope)")
    ap.add_argument("--parts", default="bs1,bs1_full,bs2,bs2_scope",
                    help="comma-separated parts to measure; the others are kept from the existing beyond.json")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--macros-only", action="store_true", help="rewrite the macro file from an existing beyond.json")
    a = ap.parse_args()
    out = Path(a.out)
    if a.macros_only:
        write_macros(json.loads((out / "beyond.json").read_text(encoding="utf-8")), out / "beyond_numbers.tex")
        print("rewrote", out / "beyond_numbers.tex")
        return 0
    parts = {x for x in a.parts.split(",") if x}  # --parts "" re-reads the bake and the benchmark only
    known = {"bs1", "bs1_full", "bs2", "bs2_scope"}  # the benchmark and the bake are read every run
    if parts - known:
        ap.error(f"unknown parts {sorted(parts - known)}; known: {sorted(known)}")
    data = {} if parts == known else json.loads((out / "beyond.json").read_text(encoding="utf-8"))
    data["engine_version"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if "bs1" in parts:
        data["bs1_crosstalk"] = measure_b1(list(range(1, a.seeds_b1 + 1)), CROSSTALK_DEVICE, "crosstalk device", True)
    if "bs1_full" in parts:
        data["bs1_full_device"] = measure_b1(list(range(1, a.seeds_b1_full + 1)), FULL_DEVICE, "4-bit, crosstalk, fill 0.85", False)
    if "bs2" in parts:
        data["bs2"] = measure_b2(list(range(1, a.seeds_b2 + 1)), a.frames)
    if "bs2_scope" in parts:
        data["bs2_scope"] = measure_b2_scope(list(range(1, a.seeds_long + 1)), list(range(1, a.seeds_c10 + 1)))
    data["bake"] = read_manifests()
    data["benchmark_bs1"] = read_benchmark()
    (out / "beyond.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    write_macros(data, out / "beyond_numbers.tex")
    print("wrote", out / "beyond.json", out / "beyond_numbers.tex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
