#!/usr/bin/env python3
"""Measure the two proposed methods of DinHot and write ``beyond.json`` and ``beyond_numbers.tex``.

B1 (device-aware weighted GS) and B2 (flicker-bounded phase-continuous sequence) are
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
                res = mod.run(setup, target, budget=Budget(its), rng=Rng(seed))
                e, s = device_scores(res.phi, setup, traps, device)
                ei, si = device_scores(res.phi, setup, traps, None)
                base[f"{name}_{its}"] = {"eff": e, "sigma": s, "eff_ideal": ei, "sigma_ideal": si}
                if is_pf and its == 30 and seed == seeds[0]:
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


# ---------------------------------------------------------------- B2

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
    """Case C10's sort on the rearrangement method's own plan (the flicker-bounded sequence test): the setup, the origin and goal trap sets and the moving mask."""
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
    """The measured limit of the flicker-bounded sequence, as its test runs it on more seeds: (a) longer moves of the acceptance lattice (12 and 20 bins,
    64 pixels), end phases from phase-fixed weighted GS at the destination, at the default frames and at the frames ``frames_for_move`` names; (b)
    case C10's sort on the rearrangement plan (end phases from phase-fixed weighted GS per seed, LPI on the same assignment) at an equal number of frames and at
    the frames of the move, and the held phases at the equal frames for the first seed."""
    out = {"claim_step_fu": float(B2.CLAIM_STEP_FU), "default_frames": int(B2.DEFAULT_FRAMES), "long": {},
           "phase_velocity_max": 1.0, "default_phase_velocity_max": float(B2.DEFAULT_PHASE_VELOCITY_MAX)}
    s256 = make_setup(256)
    a_start, a_dest = task_move(s256)
    out["acceptance_peak_step"] = float(B2.peak_step_fu(s256, a_start, a_dest, B2.DEFAULT_FRAMES))
    out["acceptance_frames_for_move"] = int(B2.frames_for_move(s256, a_start, a_dest))
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
            phis, at = lpi(s, start, dest, Rng(100 + seed), n)
            row["lpi_enough"] = float(B2.transient_min_ratio(s, phis, at)[moving].min())
            if row["enough"] < 0.9:
                res = B2.run(s, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest, frames=2 * n,
                             end_phases=end, phase_velocity_max=1.0)
                row["twice"] = float(res.meta["transient_ratio"][moving].min())
            rows.append(row)
            print(f"[B2 scope] {bins} bins seed {seed}: {B2.DEFAULT_FRAMES} frames {row['default']:.3f}, "
                  f"{n} frames {row['enough']:.3f} (LPI {row['lpi_enough']:.3f})" + (f", {2 * n} frames {row['twice']:.3f}" if "twice" in row else ""), flush=True)
        out["long"][str(bins)] = {"bins": bins, "fourier_units": float(B2.move_fourier_units(s, start, dest)), "frames": int(n),
                                  "peak_step": float(B2.peak_step_fu(s, start, dest, n)), "rows": rows}
    s, origin, goal, moving = c10_plan()
    n = B2.frames_for_move(s, origin, goal)
    c10 = {"moving": int(moving.sum()), "n_traps": len(goal), "fourier_units": float(B2.move_fourier_units(s, origin, goal)),
           "frames": int(n), "equal_frames": c10_equal_frames, "peak_step": float(B2.peak_step_fu(s, origin, goal, n)),
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


def b1_variant(setup: Setup, target: Target, device: Device | None, iters: int, rng: Rng, *, weights: bool = True,
               device_step: bool = True, safeguard: bool = True, steps: int = B1.DEFAULT_STEPS,
               warm: int = B1.DEFAULT_WARM) -> np.ndarray:
    """The loop of ``B1.run`` with its components switchable: ``weights`` (the multiplicative weight update), ``device_step``
    (the conjugate-gradient steps on the device-aware loss; off: the projection of weighted GS, with the weights read on the
    device), ``safeguard`` (the best admissible iterate; off: the last one). All on is ``B1.run`` (checked by the ablation)."""
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
    "full": ("device-aware WGS, all components", {}, True),
    "no_weights": ("without the weight update", {"weights": False}, True),
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
            "max_check_full_vs_b1run": max(r["check_full_vs_b1run"] for r in rows)}


def b2_variant(setup: Setup, start: TrapSet, dest: TrapSet, seed: int, frames: int, *, lock: bool = True,
               frame_iterations: int = B2.DEFAULT_FRAME_ITERATIONS, linear_profile: bool = False) -> dict:
    """The sequence of ``B2.run`` (held phases) with its components switchable: ``lock`` (the trap phases locked to the
    trajectory; off: every iteration takes the trap phases of the current field, as weighted GS does), ``frame_iterations``
    (0: one inversion of the locked field with unit weights per frame, no optimization), ``linear_profile`` (a linear time
    profile for the positions in place of the minimal-jerk one). The defaults are ``B2.run`` (checked by the ablation)."""
    from pipeline.model.holo.methods.optim._gs_family import weighted_gs  # noqa: PLC0415

    at = B2.trajectory(start, dest, frames, profile=(lambda t: min(max(t, 0.0), 1.0)) if linear_profile else B2.min_jerk)
    a = np.sqrt(start.weight / np.mean(start.weight))
    phi0, _ = weighted_gs(setup, start, 30, Rng(seed), variant="pfwgs", n_fix=12)
    v0 = point_trap_projection(slm_field(phi0, setup), setup, start)
    theta0 = np.angle(v0)
    phis, sig = [phi0], [rel_std(trap_intensities(v0, start.weight))]
    w = np.ones(len(start))
    phi = phi0
    for s in range(1, frames):
        traps_s = at(float(s))
        theta = np.exp(1j * theta0)
        if frame_iterations == 0:
            phi = np.angle(point_trap_backproject(a * theta, setup, traps_s))
        for _ in range(frame_iterations):
            v = point_trap_projection(slm_field(phi, setup), setup, traps_s)
            r = np.maximum(np.abs(v), 1e-300) / a
            w = w * np.mean(r) / r
            if not lock:
                theta = np.exp(1j * np.angle(v))
            phi = np.angle(point_trap_backproject(w * a * theta, setup, traps_s))
        v = point_trap_projection(slm_field(phi, setup), setup, traps_s)
        phis.append(np.mod(phi, 2.0 * np.pi))
        sig.append(rel_std(trap_intensities(v, start.weight)))
    mv = np.array([bool(np.hypot(e.x_m - t.x_m, e.y_m - t.y_m) > 0) for t, e in zip(start, dest)])
    ratio = B2.transient_min_ratio(setup, phis, at)[mv]
    return {"min": float(ratio.min()), "mean_of_min": float(ratio.mean()), "sigma_frame_max": float(max(sig))}


B2_VARIANTS = {
    "full": ("flicker-bounded sequence, all components", {}),
    "no_lock": ("without the trajectory lock", {"lock": False}),
    "no_opt": ("without the per-frame optimization", {"frame_iterations": 0}),
    "iters_1": ("1 iteration per frame", {"frame_iterations": 1}),
    "iters_3": ("3 iterations per frame", {"frame_iterations": 3}),
    "linear": ("linear time profile for the positions", {"linear_profile": True}),
}


def ablate_b2(seeds: list[int], frames: int = 13) -> dict:
    setup = make_setup(256)
    start, dest = task_move(setup)
    rows = []
    for seed in seeds:
        t0 = time.perf_counter()
        row: dict = {"seed": seed}
        for key, (_, kw) in B2_VARIANTS.items():
            row[key] = b2_variant(setup, start, dest, seed, frames, **kw)
        ref = B2.run(setup, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest, frames=frames)
        row["check_full_vs_b2run"] = abs(float(ref.meta["transient_ratio"][ref.meta["moving"]].min()) - row["full"]["min"])
        row["seconds"] = time.perf_counter() - t0
        rows.append(row)
        print(f"[ablation B2] seed {seed}: " + ", ".join(f"{k} {row[k]['min']:.3f}" for k in B2_VARIANTS)
              + f" ({row['seconds']:.0f} s)", flush=True)
    summary = {k: {"min": stats2([r[k]["min"] for r in rows]),
                   "sigma_frame_max": stats2([r[k]["sigma_frame_max"] for r in rows])} for k in B2_VARIANTS}
    return {"frames": frames, "task": "4 x 4 lattice at 8 bins, the two right columns move 4 bins in x, held phases",
            "rows": rows, "summary": summary, "max_check_full_vs_b2run": max(r["check_full_vs_b2run"] for r in rows)}


def measure_ablation(seeds_b1: int, seeds_b1_full: int, seeds_b2: int) -> dict:
    return {"b1_crosstalk": ablate_b1(list(range(1, seeds_b1 + 1)), CROSSTALK_DEVICE, list(B1_VARIANTS), "crosstalk device"),
            "b1_full": ablate_b1(list(range(1, seeds_b1_full + 1)), FULL_DEVICE,
                                 ["full", "no_weights", "no_step", "no_guard", "no_model"], "full device"),
            "b2": ablate_b2(list(range(1, seeds_b2 + 1)))}


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


def read_benchmark(budget: int = 100) -> dict:
    """Device-aware WGS in the studio's benchmark (``data/derived/benchmark/results.json``): on every geometry where both ran, the factor of
    device-aware WGS over phase-fixed WGS on the relative standard deviation and the efficiency ratio, at ``budget`` iterations with the
    default parameters, on the C08 device and on the ideal device."""
    r = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    pf = m07_phase_fixed_wgs.SPEC.id  # the engine key of the reference method in the benchmark document
    cells = {(x["method"], x["geometry"], x["device"]): x for x in r["rows"]
             if x["budget_kind"] == "iterations" and x["budget"] == budget and x["params"] == "default"}
    names = {g["id"]: g["name"]["en"] for g in r["geometries"]}
    ntraps = {g["id"]: g["n_traps"] for g in r["geometries"]}
    out = {"budget": budget, "devices": {}}
    for device in ("device", "ideal"):
        rows = []
        for (m, g, d), b1 in sorted(cells.items()):
            if m != "B1" or d != device or (pf, g, d) not in cells:
                continue
            m7 = cells[(pf, g, d)]
            rows.append({"geometry": g, "name": names[g], "n_traps": ntraps[g],
                         "n_seeds": min(b1["n_seeds"], m7["n_seeds"]), "n_seeds_b1": b1["n_seeds"], "n_seeds_m07": m7["n_seeds"],
                         "sigma_b1": b1["rel_std_pct"]["median"], "sigma_m07": m7["rel_std_pct"]["median"],
                         "sigma_b1_iqr": [b1["rel_std_pct"]["q1"], b1["rel_std_pct"]["q3"]],
                         "sigma_m07_iqr": [m7["rel_std_pct"]["q1"], m7["rel_std_pct"]["q3"]],
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
    c8m = man["C08_device_limited"]
    L.append(macro("bakeCeightFlicker", f"{c8m['params']['flicker_rad']:g}"))
    L.append(macro("bakeCeightRatioThree", fmt(c8m["seeds_mean_ratio"], 1)))
    sr = c8m["seeds_ratio"]
    L.append(macro("bakeCeightSeedRatios", ", ".join(fmt(x, 3) for x in sr[:-1]) + f" and {fmt(sr[-1], 3)}"))
    L.append(macro("bakeCeightSeedsTwo", sum(1 for x in sr if x >= 2)))
    L.append(macro("bakeCeightSeedsN", len(sr)))
    # B2
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
    L.append(macro("sigmaFrameFactorLo", fmt(s13["lpi_sigma_frame_max"]["min"] / s13["b2_sigma_frame_max"]["max"], 0)))
    L.append(macro("sigmaFrameFactorHi", fmt(s13["lpi_sigma_frame_max"]["max"] / s13["b2_sigma_frame_max"]["max"], 0)))
    for fr, nm in (("7", "Seven"), ("25", "TwentyFive")):
        if fr in b2:
            L.append(macro(f"bTwoMed{nm}", fmt(b2[fr]["b2_min"]["median"], 3)))
            L.append(macro(f"bTwoMin{nm}", fmt(b2[fr]["b2_min"]["min"], 3)))
            L.append(macro(f"lpiMed{nm}", fmt(b2[fr]["lpi_min"]["median"], 3)))
            L.append(macro(f"lpiMax{nm}", fmt(b2[fr]["lpi_min"]["max"], 3)))
    # B2, the measured scope
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
        lp = [r["lpi_enough"] for r in lg["rows"]]
        L.append(macro(f"long{nm}BLeads", sum(1 for r in lg["rows"] if r["enough"] > r["lpi_enough"])))
        L.append(macro(f"long{nm}LpiMin", fmt(min(lp), 3)))
        L.append(macro(f"long{nm}LpiMax", fmt(max(lp), 3)))
    L.append(macro("longSeeds", len(sc["long"]["12"]["rows"])))
    L.append(macro("longAPeak", fmt(sc["long"]["12"]["peak_step"], 3)))
    L.append(macro("longBPeak", fmt(sc["long"]["20"]["peak_step"], 3)))
    fails = []
    for key in ("12", "20"):
        bad = [r for r in sc["long"][key]["rows"] if r["enough"] < 0.9]
        if bad:
            fails.append(" and ".join(f"{r['enough']:.3f}" for r in bad) + f" at {key} bins")
    twice = []
    for key in ("12", "20"):
        bad = [r for r in sc["long"][key]["rows"] if "twice" in r]
        if bad:
            twice.append(" and ".join(f"{r['twice']:.3f}" for r in bad) + f" at {key} bins")
    L.append(macro("longFailList", "; ".join(fails) if fails else "none"))
    L.append(macro("longTwiceList", "; ".join(twice) if twice else "none"))
    L.append(macro("accPeakStep", fmt(sc["acceptance_peak_step"], 2)))
    L.append(macro("accFramesForMove", sc["acceptance_frames_for_move"]))
    L.append(macro("scopePhaseVel", f"{sc['phase_velocity_max']:g}"))
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
    L.append(macro("cTenPeak", fmt(c["peak_step"], 3)))
    bad = [r for r in rows if r["b2_enough"] < 0.9]
    L.append(macro("cTenFailList", "; ".join(f"seed {r['seed']} at {r['b2_enough']:.3f} against {r['lpi_enough']:.3f} for LPI" for r in bad) or "none"))
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


CAMEL = {"full": "Full", "no_weights": "NoWeights", "no_step": "NoStep", "no_guard": "NoGuard", "no_model": "NoModel",
         "steps_1": "StepsOne", "steps_6": "StepsSix", "warm_only": "Warm", "no_lock": "NoLock", "no_opt": "NoOpt",
         "iters_1": "ItersOne", "iters_3": "ItersThree", "linear": "Linear"}


def write_extra_macros(data: dict, path: Path) -> None:
    """Macros of the intervals of the main results and of the ablation, appended to ``beyond_numbers.tex``."""
    L = ["% Intervals and ablation (data/measure.py, from beyond.json).\n"]
    L.append(macro("engineRelease", data["engine_version"]))
    import math  # noqa: PLC0415

    def sinc2_half(delta: float) -> float:
        x = math.pi * delta / 2.0
        return 1.0 if x == 0 else (math.sin(x) / x) ** 2

    lo, hi = 1e-9, 2.0  # sinc^2(delta / 2) falls from 1 to 0 on (0, 2): bisection for the shift at which it equals 0.9
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if sinc2_half(mid) > 0.9 else (lo, mid)
    L.append(macro("deltaNine", fmt(0.5 * (lo + hi), 3)))
    L.append(macro("sincAcc", fmt(sinc2_half(data["bs2_scope"]["acceptance_peak_step"]), 3)))
    L.append(macro("sincClaim", fmt(sinc2_half(data["bs2_scope"]["claim_step_fu"]), 3)))
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
    s13 = [r for r in data["bs2"]["runs"] if r["frames"] == 13]
    b, l = [r["b2_min"] for r in s13], [r["lpi_min"] for r in s13]
    sb, sl, sd_ = stats2(b), stats2(l), stats2([x - y for x, y in zip(b, l)])
    L.append(macro("bTwoMean", fmt(sb["mean"], 3)))
    L.append(macro("bTwoSd", fmt(sb["sd"], 3)))
    L.append(macro("bTwoCiLo", fmt(sb["ci_lo"], 3)))
    L.append(macro("bTwoCiHi", fmt(sb["ci_hi"], 3)))
    L.append(macro("lpiMean", fmt(sl["mean"], 3)))
    L.append(macro("lpiSd", fmt(sl["sd"], 3)))
    L.append(macro("lpiCiLo", fmt(sl["ci_lo"], 3)))
    L.append(macro("lpiCiHi", fmt(sl["ci_hi"], 3)))
    L.append(macro("diffTwoMean", fmt(sd_["mean"], 3)))
    L.append(macro("diffTwoCiLo", fmt(sd_["ci_lo"], 3)))
    L.append(macro("diffTwoCiHi", fmt(sd_["ci_hi"], 3)))
    L.append(macro("bTwoSigmaFrameMed", fmt(data["bs2"]["summary"]["13"]["b2_sigma_frame_max"]["median"], 2)))
    L.append(macro("lpiSigmaFrameMed", fmt(data["bs2"]["summary"]["13"]["lpi_sigma_frame_max"]["median"], 1)))
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
        for k, v in ab["b2"]["summary"].items():
            n = f"ablT{CAMEL[k]}"
            L.append(macro(n + "Med", fmt(v["min"]["median"], 3)))
            L.append(macro(n + "Min", fmt(v["min"]["min"], 3)))
            L.append(macro(n + "Max", fmt(v["min"]["max"], 3)))
            L.append(macro(n + "Mean", fmt(v["min"]["mean"], 3)))
            L.append(macro(n + "Sd", fmt(v["min"]["sd"], 3)))
            L.append(macro(n + "Sig", fmt(v["sigma_frame_max"]["median"], 2)))
        for tag, key in (("B", "b1_crosstalk"), ("BF", "b1_full")):
            sm = ab[key]["summary"]
            L.append(macro(f"abl{tag}WeightsRatio", fmt(sm["full"]["sigma"]["median"] / sm["no_weights"]["sigma"]["median"], 0)))
            L.append(macro(f"abl{tag}StepRatio", fmt(sm["no_step"]["sigma"]["median"] / sm["full"]["sigma"]["median"], 0)))
            L.append(macro(f"abl{tag}ModelRatio", fmt(sm["no_model"]["sigma"]["median"] / sm["full"]["sigma"]["median"], 0)))
        L.append(macro("ablSeconds", fmt(sum(r["seconds"] for k in ("b1_crosstalk", "b1_full", "b2") for r in ab[k]["rows"]) / 60.0, 0)))
        L.append(macro("ablTN", ab["b2"]["summary"]["full"]["min"]["n"]))
        L.append(macro("ablTCheck", f"{ab['b2']['max_check_full_vs_b2run']:.1e}"))
    main_s = sum(r["seconds"] for k in ("bs1_crosstalk", "bs1_full_device") for r in data[k]["rows"]) + sum(r["seconds"] for r in data["bs2"]["runs"])
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
        d = ab["b2"]
        l13 = [r["lpi_min"] for r in data["bs2"]["runs"] if r["frames"] == d["frames"]]
        sl = stats2(l13)
        L = ["\\begin{tabular}{@{}l r r r r r@{}}\n\\toprule\n",
             row_cells(["Variant", "Minimum ratio, mean $\\pm$ s.d.", "Range", "Seeds at 0.9 or above", "Largest frame $\\sigma$ (\\%)"]),
             "\\midrule\n"]
        for k, (label, _) in B2_VARIANTS.items():
            rows = [r[k]["min"] for r in d["rows"]]
            v = d["summary"][k]
            L.append(row_cells([label, f"{fmt(v['min']['mean'], 3)} $\\pm$ {fmt(v['min']['sd'], 3)}",
                                f"{fmt(v['min']['min'], 3)} to {fmt(v['min']['max'], 3)}",
                                f"{sum(x >= 0.9 for x in rows)} of {len(rows)}", fmt(v["sigma_frame_max"]["median"], 2)]))
        L.append(row_cells(["linear phase interpolation (reference)", f"{fmt(sl['mean'], 3)} $\\pm$ {fmt(sl['sd'], 3)}",
                            f"{fmt(sl['min'], 3)} to {fmt(sl['max'], 3)}", f"{sum(x >= 0.9 for x in l13)} of {len(l13)}",
                            fmt(data['bs2']['summary'][str(d['frames'])]['lpi_sigma_frame_max']['median'], 1)]))
        L.append("\\bottomrule\n\\end{tabular}\n")
        (out / "tab_abl_b2.tex").write_text("".join(L), encoding="utf-8")
    # benchmark, B1 against M07 on the C08 device, then on the ideal device
    bb = data["benchmark_bs1"]
    L = ["\\begin{tabular}{@{}l r r r r r r r@{}}\n\\toprule\n",
         row_cells(["Geometry", "Traps", "Seeds (device-aware, phase-fixed)", "$\\sigma$ phase-fixed WGS (\\%)", "$\\sigma$ device-aware WGS (\\%)", "Factor", "$e$ ratio", "Both thresholds"]),
         "\\midrule\n"]
    for x in bb["devices"]["device"]:
        ok = x["factor"] >= 2 and x["eff_ratio"] >= 0.9
        L.append(row_cells([f"{x['geometry']} {x['name']}", str(x["n_traps"]), f"{x['n_seeds_b1']}, {x['n_seeds_m07']}",
                            f"{fmt(x['sigma_m07'], 2)} ({fmt(x['sigma_m07_iqr'][0], 2)} to {fmt(x['sigma_m07_iqr'][1], 2)})",
                            f"{fmt(x['sigma_b1'], 2)} ({fmt(x['sigma_b1_iqr'][0], 2)} to {fmt(x['sigma_b1_iqr'][1], 2)})",
                            fmt(x["factor"], 2), fmt(x["eff_ratio"], 3), "yes" if ok else "no"]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_bench.tex").write_text("".join(L), encoding="utf-8")
    # B2, the long moves and the rearrangement case
    sc = data["bs2_scope"]
    L = ["\\begin{tabular}{@{}l r r r r r r r@{}}\n\\toprule\n",
         row_cells(["Move", "Frames", "Peak step (Fourier units)", "Sequence median", "Sequence range", "Seeds at 0.9 or above", "Linear phase interpolation range", "Sequence above it"]),
         "\\midrule\n"]
    for key in ("12", "20"):
        lg = sc["long"][key]
        e = [r["enough"] for r in lg["rows"]]
        lp = [r["lpi_enough"] for r in lg["rows"]]
        L.append(row_cells([f"lattice, {lg['bins']} bins", str(lg["frames"]), fmt(lg["peak_step"], 3), fmt(statistics.median(e), 3),
                            f"{fmt(min(e), 3)} to {fmt(max(e), 3)}", f"{sum(x >= 0.9 for x in e)} of {len(e)}",
                            f"{fmt(min(lp), 3)} to {fmt(max(lp), 3)}", f"{sum(1 for r in lg['rows'] if r['enough'] > r['lpi_enough'])} of {len(e)}"]))
    c = sc["c10"]
    for tag, frames, peak in (("equal", c["equal_frames"], c["peak_step_equal"]), ("enough", c["frames"], c["peak_step"])):
        e = [r[f"b2_{tag}"] for r in c["rows"]]
        lp = [r[f"lpi_{tag}"] for r in c["rows"]]
        L.append(row_cells([f"rearrangement C10, {c['moving']} moving traps", str(frames), fmt(peak, 3), fmt(statistics.median(e), 3),
                            f"{fmt(min(e), 3)} to {fmt(max(e), 3)}", f"{sum(x >= 0.9 for x in e)} of {len(e)}",
                            f"{fmt(min(lp), 3)} to {fmt(max(lp), 3)}", f"{sum(1 for a_, b_ in zip(e, lp) if a_ > b_)} of {len(e)}"]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_long.tex").write_text("".join(L), encoding="utf-8")


def write_all(data: dict, out: Path) -> None:
    write_macros(data, out / "beyond_numbers.tex")
    write_extra_macros(data, out / "beyond_numbers.tex")
    write_tables(data, out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds-b1", type=int, default=5)
    ap.add_argument("--seeds-b1-full", type=int, default=3)
    ap.add_argument("--seeds-b2", type=int, default=5)
    ap.add_argument("--frames", type=int, nargs="+", default=[13, 7, 25])
    ap.add_argument("--seeds-long", type=int, default=8, help="seeds of the long lattice moves (B2 scope)")
    ap.add_argument("--seeds-c10", type=int, default=6, help="seeds of the sort of case C10 on the rearrangement plan (flicker-bounded sequence scope)")
    ap.add_argument("--seeds-abl-b1", type=int, default=5)
    ap.add_argument("--seeds-abl-b1-full", type=int, default=3)
    ap.add_argument("--seeds-abl-b2", type=int, default=5)
    ap.add_argument("--parts", default="bs1,bs1_full,bs2,bs2_scope,ablation",
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
    known = {"bs1", "bs1_full", "bs2", "bs2_scope", "ablation"}  # the benchmark and the bake are read every run
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
    if "ablation" in parts:
        data["ablation"] = measure_ablation(a.seeds_abl_b1, a.seeds_abl_b1_full, a.seeds_abl_b2)
    data["bake"] = read_manifests()
    data["benchmark_bs1"] = read_benchmark()
    (out / "beyond.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    write_all(data, out)
    print("wrote", out / "beyond.json", out / "beyond_numbers.tex", "and the tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
