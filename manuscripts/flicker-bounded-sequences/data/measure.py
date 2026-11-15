#!/usr/bin/env python3
"""Measure the flicker-bounded phase-continuous sequence (B2) against its published baselines and write ``flicker.json``,
``flicker_numbers.tex`` and the table files of the paper ``manuscripts/flicker-bounded-sequences``.

The sequence of the engine module ``methods/beyond/b2_flicker_bounded.py`` is compared, on the same trajectories and the same
frame counts, with the two published sequences of ``methods/control/m16_rearrangement.py``:

  * ``lpi``: linear phase interpolation of Knottnerus et al. 2025 (arXiv 2501.01391), ``sequence='lpi'``;
  * ``kim``: the per-frame Gerchberg-Saxton sequence with phase induction of Kim, Kim, Lee and Ahn 2019 (Opt. Express 27, 2184),
    ``sequence='per-frame-gs'``, run at two counts of iterations per frame, ``kim5`` (``FRAME_ITERATIONS``, the default of the
    method and the count of Kim et al.'s Fig. 3, i = 5) and ``kim10`` (the 10 iterations per frame of the flicker-bounded sequence,
    so that the two are compared at equal work per frame).

Every run is scored by one function (``score_sequence``): the per-frame minimum intensity ratio along the move (the lowest
intensity of a moving trap over the frames divided by its mean), the transient minimum ratio of the blend model of the paper
(``B2.transient_min_ratio``, the minimum over the frames and over the instants between two frames), the transient between the
frames alone, the largest phase step between two consecutive frames of any moving trap (``arg V_m``), the largest per-frame
relative standard deviation, the number of frames against the bound of the frame-count equation
(``B2.frames_for_move``, Eq. frames of the paper) and the seconds of the run. Wins are read by the rule of the benchmark
(``extract_methods.cell_result`` of the technical report): at least five seeds, interquartile ranges that do not overlap and a
gap of at least 0.01 percentage points of the dip below the mean (the lowest intensity is read as a dip, ``100 (1 - ratio)``,
lower is better) or of the per-frame spread, otherwise a tie.

Experiments (parts of ``--parts``):

  * ``accept`` (the acceptance task of the engine test: a 4 x 4 lattice at 8 bins, the two right columns move 4 bins in x, 256 x 256
    pixels padded 2) at 7, 13 and 25 frames, ``--seeds`` seeds each;
  * ``long`` (the same lattice moved 12 and 20 bins on 64 pixels) at the frames of the bound and at twice that count where the
    sequence misses 0.9, ``--seeds-long`` seeds;
  * ``c10`` (the sort of case C10 on the rearrangement plan, 25 frames and the frames of the bound), ``--seeds-c10`` seeds;
  * ``ablation`` (``ablate_b2``: the sequence without the lock, without the per-frame optimization, with 1 or 3 iterations per frame
    and with a linear profile) on the acceptance task, ``--seeds-abl`` seeds;
  * ``curves`` (the transient intensity of the worst moving trap along the acceptance move, first seed, every method).

Six figure series and five tables come out of ``flicker.json`` (each named here with what it shows; the ``.tex`` figures are drawn
by the paper's own figure scripts, never here):

  F1 ``figures.transient_curves``: the intensity of the worst moving trap at every frame and blend instant, normalised by its frame
     mean, for the four methods (the flicker, drawn);
  F2 ``figures.ratio_vs_frames``: the per-frame minimum ratio against the number of frames (7, 13, 25), median and range per method;
  F3 ``figures.phase_steps``: the largest phase step between frames of every moving trap, per method, first seed (the phase
     continuity that Kim et al. induce and the lock guarantees);
  F4 ``figures.frames_vs_move``: the frames used and the bound of the frame-count equation against the length of the move
     (4, 12, 20 bins and C10), with the peak step per frame in Fourier units;
  F5 ``figures.long_and_sort``: the transient minimum ratio per seed on the long moves and the C10 sort, every method;
  F6 ``figures.ablation``: the transient minimum ratio per seed of each variant of the ablation;
  F7 ``figures.seconds``: seconds per sequence against the number of frames (the cost in time of every method).

  T1 ``tab_main.tex``: the acceptance task at 13 frames, every method, mean, interval and the reading against each baseline;
  T2 ``tab_frames.tex``: the three frame counts of the acceptance task;
  T3 ``tab_long.tex``: the long moves and the C10 sort at the frames of the bound;
  T4 ``tab_bound.tex``: the frame-count equation against the frames used, the peak step in Fourier units and the ratio reached;
  T5 ``tab_abl_b2.tex``: the ablation of the sequence, with linear phase interpolation and per-frame GS as references.

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/flicker-bounded-sequences/data/measure.py [--seeds 6] [--seeds-long 8] [--seeds-c10 6]

Deterministic: every method takes a seed through the portable generator (the baselines take ``100 + seed``, a stream of their own), so a
rerun gives the same numbers up to the floating point of the machine's FFT; the seconds differ between runs.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.model.holo.core.forward import point_trap_backproject, point_trap_fields, point_trap_projection, slm_field  # noqa: E402
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude  # noqa: E402
from pipeline.model.holo.core.metrics import rel_std, trap_intensities  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import TrapSet  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs  # noqa: E402
from pipeline.model.holo.methods.beyond import b2_flicker_bounded as B2  # noqa: E402
from pipeline.model.holo.methods.control import m16_rearrangement as M16  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# the helpers shared with the device-aware paper's script (setup, lattices, statistics, macros): one definition, never a copy
DA = _load("da_measure", HERE.parents[1] / "device-aware-flicker-bounded" / "data" / "measure.py")
make_setup, bin_grid, stats, stats2, geo_ci, macro, fmt, row_cells = (DA.make_setup, DA.bin_grid, DA.stats, DA.stats2, DA.geo_ci,
                                                                        DA.macro, DA.fmt, DA.row_cells)
X = DA._studio_rule()  # extract_methods: the win rule, once

METHODS = ("b2", "lpi", "kim5", "kim10")
LABEL = {"b2": "flicker-bounded sequence", "lpi": "linear phase interpolation", "kim5": "per-frame GS with phase induction, 5 iterations",
         "kim10": "per-frame GS with phase induction, 10 iterations"}
KIM10 = B2.DEFAULT_FRAME_ITERATIONS
# how each method is told apart by the rule of the benchmark: B2 is the proposed method, the others are published ones
RULE_ID = {"b2": "B2", "lpi": "M16-lpi", "kim5": "M16-kim5", "kim10": "M16-kim10"}


# ------------------------------------------------------------------------------------------------ trajectories and the scoring

def task_move(setup: Setup, bins: float = 4.0):
    """The acceptance lattice (4 x 4, 8 bins) with its two right columns moved ``bins`` focal bins in x; the moving mask."""
    start = bin_grid(setup, 4, 4, 8)
    b = focal_bin_m(setup)
    dest = TrapSet(replace(t, x_m=t.x_m + (bins * b if (i % 4) >= 2 else 0.0)) for i, t in enumerate(start))
    return start, dest, np.array([(i % 4) >= 2 for i in range(16)])


def c10_plan():
    """Case C10's sort on the rearrangement plan: the setup, the origin and goal trap sets and the moving mask (the engine test's plan)."""
    from pipeline.cases import build, library  # noqa: PLC0415
    from pipeline.io.contract import read_cases  # noqa: PLC0415

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


def aligned_plan(setup: Setup, start: TrapSet, dest: TrapSet, alpha: float) -> tuple[TrapSet, np.ndarray, list]:
    """The origin traps in the order of the destination under the Hungarian assignment of M16 itself, the moving mask and the assignment.

    With ties in the cost the assignment of the plan and the one M16 returns may differ, so every sequence is run on the assignment M16
    returns for the loaded atoms ``start`` (target ``k`` takes atom ``f[k]``); the flicker-bounded sequence and the baselines then move
    the same traps along the same paths."""
    b = focal_bin_m(setup)
    f = list(M16.assign(np.c_[dest.x_m, dest.y_m] / b, np.c_[start.x_m, start.y_m] / b, alpha))
    st, gl = list(start), list(dest)
    aligned = TrapSet(replace(gl[k], x_m=st[i].x_m, y_m=st[i].y_m) for k, i in enumerate(f))
    moving = np.array([np.hypot(a.x_m - g.x_m, a.y_m - g.y_m) > 0 for a, g in zip(aligned, dest)])
    return aligned, moving, f


def linear_at(start: TrapSet, end: TrapSet, n_steps: int):
    """The linear trajectory of the rearrangement method (``M16``): the trap set at the fractional frame ``s`` of ``n_steps`` steps."""
    def at(s: float) -> TrapSet:
        f = s / n_steps
        return TrapSet(replace(t, x_m=t.x_m + (e.x_m - t.x_m) * f, y_m=t.y_m + (e.y_m - t.y_m) * f) for t, e in zip(start, end))
    return at


def transient_curve(setup: Setup, phis: list, at, substeps: int = 10) -> np.ndarray:
    """Intensity of every trap at every (frame, sub-frame) instant: row ``s * substeps`` is frame ``s``, the rows between are the blend."""
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


def _wrap(x):
    return np.angle(np.exp(1j * x))


def score_sequence(setup: Setup, phis: list, at, traps0: TrapSet, moving: np.ndarray, *, substeps: int = 10) -> dict:
    """The metrics of one sequence of holograms on its own trajectory ``at`` (the same function for every method)."""
    cur = transient_curve(setup, phis, at, substeps)
    n = len(phis)
    frame_rows = cur[::substeps][:n]
    mean = frame_rows.mean(axis=0)
    blend_rows = np.array([r for k, r in enumerate(cur) if k % substeps != 0]) if n > 1 else cur[:0]
    v = np.array([point_trap_projection(slm_field(p, setup), setup, at(float(s))) for s, p in enumerate(phis)])
    steps = np.abs(_wrap(np.diff(np.angle(v), axis=0))) if n > 1 else np.zeros((1, v.shape[1]))
    sig = [rel_std(trap_intensities(v[s], traps0.weight)) for s in range(n)]
    return {
        "frame_min_ratio": float((frame_rows.min(axis=0) / mean)[moving].min()),
        "transient_min_ratio": float((cur.min(axis=0) / mean)[moving].min()),
        "blend_min_ratio": float((blend_rows.min(axis=0) / mean)[moving].min()) if len(blend_rows) else float("nan"),
        "phase_step_max": float(steps[:, moving].max()),
        "phase_step_median": float(np.median(steps[:, moving].max(axis=0))),
        "phase_step_per_trap": [float(x) for x in steps[:, moving].max(axis=0)],
        "sigma_frame_max": float(max(sig)),
        "n_frames": n,
    }


def bound_of(setup: Setup, start: TrapSet, dest: TrapSet, frames: int) -> dict:
    """The frame-count equation of the paper (``B2.frames_for_move``) and the peak step of ``frames`` frames, in Fourier units."""
    return {"fourier_units": float(B2.move_fourier_units(setup, start, dest)), "frames_bound": int(B2.frames_for_move(setup, start, dest)),
            "frames_bound_minimum": int(B2.frames_for_move(setup, start, dest, minimum=2)),
            "peak_step_fu": float(B2.peak_step_fu(setup, start, dest, frames)), "claim_step_fu": float(B2.CLAIM_STEP_FU)}


def run_b2(setup, start, dest, moving, seed, frames, *, end_phases=None, phase_velocity_max=None) -> tuple[dict, list, object]:
    kw = {} if end_phases is None else {"end_phases": end_phases, "phase_velocity_max": phase_velocity_max}
    t0 = time.perf_counter()
    res = B2.run(setup, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest, frames=frames, **kw)
    sec = time.perf_counter() - t0
    phis = [np.asarray(f) for f in res.meta["frames"]]
    at = B2.trajectory(start, dest, frames)
    out = score_sequence(setup, phis, at, start, moving)
    out["seconds"] = sec
    out["transient_ratio_engine"] = float(res.meta["transient_ratio"][moving].min())
    out["iterations"] = int(res.meta["iterations"])
    return out, phis, at


def run_m16(setup, start, dest, moving, seed, frames, sequence, frame_iterations=M16.FRAME_ITERATIONS, alpha=1.5, atoms=None,
            assignment=None) -> tuple[dict, list, object]:
    """The published sequences of M16 on the same traps and the same number of frames (``max_step_bins`` from the longest move)."""
    b = focal_bin_m(setup)
    longest = max(math.hypot(e.x_m - t.x_m, e.y_m - t.y_m) for t, e in zip(start, dest)) / b
    step = longest / (frames - 1) * (1.0 + 1e-9)
    t0 = time.perf_counter()
    res = M16.run(setup, Target.from_traps(dest), budget=Budget(30), rng=Rng(100 + seed), atoms=start if atoms is None else atoms, alpha=alpha, max_step_bins=step,
                  sequence=sequence, frame_iterations=frame_iterations)
    sec = time.perf_counter() - t0
    assert res.meta["n_steps"] == frames - 1, (res.meta["n_steps"], frames)
    assert list(res.meta["assignment"]) == (list(range(len(start))) if assignment is None else list(assignment)), "the assignment of M16 changed"
    assert int(res.meta["moved"].sum()) == int(moving.sum()), "the assignment moved a different set of traps"
    phis = [np.asarray(f) for f in res.meta["frames"]]
    seq = res.meta["trap_sequence"]
    # the traps of the engine's frames are in the order of the targets; moving is read in the same order
    at = linear_at(seq[0], seq[-1], frames - 1)
    out = score_sequence(setup, phis, at, dest, moving)
    out["seconds"] = sec
    out["iterations"] = int(res.meta.get("iterations", 0))
    out["max_phase_step_engine"] = float(res.meta["max_phase_step"][moving].max())
    return out, phis, at


def run_all(setup, start, dest, moving, seed, frames, alpha=1.5, atoms=None, assignment=None, **b2kw) -> tuple[dict, dict]:
    """The four sequences on one trajectory and one seed: the scores and (for the curves) the holograms."""
    rows, held = {}, {}
    rows["b2"], phis, at = run_b2(setup, start, dest, moving, seed, frames, **b2kw)
    held["b2"] = (phis, at)
    for key, seq, its in (("lpi", "lpi", M16.FRAME_ITERATIONS), ("kim5", "per-frame-gs", M16.FRAME_ITERATIONS), ("kim10", "per-frame-gs", KIM10)):
        rows[key], phis, at = run_m16(setup, start, dest, moving, seed, frames, seq, its, alpha, atoms, assignment)
        held[key] = (phis, at)
    return rows, held


# ------------------------------------------------------------------------------------------------ the experiments

def measure_accept(seeds: list[int], frames_list: list[int]) -> dict:
    setup = make_setup(256)
    start, dest, moving = task_move(setup)
    assert int(moving.sum()) == 8
    runs, curves = [], {}
    for frames in frames_list:
        for seed in seeds:
            rows, held = run_all(setup, start, dest, moving, seed, frames)
            runs.append({"frames": frames, "seed": seed, **{k: v for k, v in rows.items()}})
            if frames == 13 and seed == seeds[0]:
                for k, (phis, at) in held.items():
                    cur = transient_curve(setup, phis, at)
                    fr = cur[::10][:frames]
                    ratio = cur.min(axis=0) / fr.mean(axis=0)
                    m = int(np.where(moving)[0][int(np.argmin(ratio[moving]))])
                    curves[k] = {"trap": m, "curve": [float(x) for x in cur[:, m] / fr[:, m].mean()], "frames": frames, "substeps": 10}
            print(f"[accept] frames {frames} seed {seed}: " + ", ".join(f"{k} {rows[k]['transient_min_ratio']:.3f}" for k in METHODS), flush=True)
    return {"task": "4 x 4 lattice at 8 bins, the two right columns move 4 bins in x, 256 x 256 pixels padded 2", "moving_traps": 8,
            "frames_list": frames_list, "runs": runs, "curves": curves, "bound": bound_of(setup, start, dest, 13),
            "seeds": list(seeds)}


def measure_long(seeds: list[int]) -> dict:
    """Longer moves on 64 pixels, end phases from phase-fixed WGS at the destination (the held phases cannot reach them): every method at
    the frames of the bound; the flicker-bounded sequence also at the default 13 frames and, where it misses 0.9, at twice the bound."""
    s = make_setup(64)
    out = {"claim_step_fu": float(B2.CLAIM_STEP_FU), "default_frames": int(B2.DEFAULT_FRAMES), "moves": {}}
    for bins in (12, 20):
        start, dest, moving = task_move(s, float(bins))
        n = B2.frames_for_move(s, start, dest)
        rows = []
        for seed in seeds:
            end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(dest), budget=Budget(30), rng=Rng(seed)).fields)
            scored, _ = run_all(s, start, dest, moving, seed, n, end_phases=end, phase_velocity_max=1.0)
            row = {"seed": seed, "frames": n, **scored}
            d13, _, _ = run_b2(s, start, dest, moving, seed, B2.DEFAULT_FRAMES, end_phases=end, phase_velocity_max=1.0)
            row["b2_default_frames"] = d13
            if scored["b2"]["transient_min_ratio"] < 0.9:
                tw, _, _ = run_b2(s, start, dest, moving, seed, 2 * n, end_phases=end, phase_velocity_max=1.0)
                row["b2_twice"] = tw
            rows.append(row)
            print(f"[long] {bins} bins seed {seed}: " + ", ".join(f"{k} {scored[k]['transient_min_ratio']:.3f}" for k in METHODS), flush=True)
        out["moves"][str(bins)] = {"bins": bins, **bound_of(s, start, dest, n), "frames": int(n), "rows": rows}
    return out


def measure_c10(seeds: list[int], equal_frames: int = 25) -> dict:
    s, origin, goal, moving = c10_plan()
    atoms = origin  # the loaded atoms the sort starts from; M16 assigns them to the targets itself
    origin, moving, f = aligned_plan(s, atoms, goal, 1.0)
    n = B2.frames_for_move(s, origin, goal)
    out = {"moving": int(moving.sum()), "n_traps": len(goal), "frames_bound": int(n), "equal_frames": equal_frames,
           **bound_of(s, origin, goal, n), "peak_step_equal": float(B2.peak_step_fu(s, origin, goal, equal_frames)), "rows": []}
    held, _, _ = run_b2(s, origin, goal, moving, seeds[0], equal_frames)
    out["held_equal_first_seed"] = held["transient_min_ratio"]
    for seed in seeds:
        end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(goal), budget=Budget(30), rng=Rng(seed)).fields)
        row = {"seed": seed}
        for tag, frames in (("equal", equal_frames), ("bound", n)):
            scored, _ = run_all(s, origin, goal, moving, seed, frames, alpha=1.0, atoms=atoms, assignment=f, end_phases=end, phase_velocity_max=1.0)
            row[tag] = {"frames": frames, **scored}
        out["rows"].append(row)
        print(f"[c10] seed {seed}: bound {n} frames " + ", ".join(f"{k} {row['bound'][k]['transient_min_ratio']:.3f}" for k in METHODS), flush=True)
    return out


# ablation (content bar, 2026-11-03): the sequence with its components switchable

def b2_variant(setup: Setup, start: TrapSet, dest: TrapSet, seed: int, frames: int, *, lock: bool = True,
               frame_iterations: int = B2.DEFAULT_FRAME_ITERATIONS, linear_profile: bool = False) -> dict:
    """The sequence of ``B2.run`` (held phases) with its components switchable: ``lock`` (the trap phases locked to the trajectory; off:
    every iteration takes the trap phases of the current field, as weighted GS does), ``frame_iterations`` (0: one inversion of the locked
    field with unit weights per frame, no optimization), ``linear_profile`` (a linear time profile for the positions in place of the
    minimal-jerk one). The defaults are ``B2.run`` (checked by the ablation)."""
    at = B2.trajectory(start, dest, frames, profile=(lambda t: min(max(t, 0.0), 1.0)) if linear_profile else B2.min_jerk)
    a = np.sqrt(start.weight / np.mean(start.weight))
    phi0, _ = G.weighted_gs(setup, start, 30, Rng(seed), variant="pfwgs", n_fix=12)
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
    return {"min": float(ratio.min()), "mean_of_min": float(ratio.mean()), "sigma_frame_max": float(max(sig)),
            "phase_step_max": float(score_sequence(setup, phis, at, start, mv)["phase_step_max"])}


B2_VARIANTS = {
    "full": ("flicker-bounded sequence, all components", {}),
    "no_lock": ("without the trajectory lock", {"lock": False}),
    "no_opt": ("without the per-frame optimization", {"frame_iterations": 0}),
    "iters_1": ("1 iteration per frame", {"frame_iterations": 1}),
    "iters_3": ("3 iterations per frame", {"frame_iterations": 3}),
    "linear": ("linear time profile for the positions", {"linear_profile": True}),
}


def measure_ablation(seeds: list[int], frames: int = 13) -> dict:
    setup = make_setup(256)
    start, dest, moving = task_move(setup)
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
        print(f"[ablation] seed {seed}: " + ", ".join(f"{k} {row[k]['min']:.3f}" for k in B2_VARIANTS), flush=True)
    summary = {k: {"min": stats2([r[k]["min"] for r in rows]), "sigma_frame_max": stats2([r[k]["sigma_frame_max"] for r in rows]),
                   "phase_step_max": stats2([r[k]["phase_step_max"] for r in rows])} for k in B2_VARIANTS}
    return {"frames": frames, "task": "4 x 4 lattice at 8 bins, the two right columns move 4 bins in x, held phases", "rows": rows,
            "summary": summary, "max_check_full_vs_b2run": max(r["check_full_vs_b2run"] for r in rows)}


# ------------------------------------------------------------------------------------------------ reading by the benchmark's rule

def _quartiles(v: list[float]) -> dict:
    q = np.percentile(np.asarray(v, dtype=np.float64), [25, 50, 75])
    return {"q1": float(q[0]), "median": float(q[1]), "q3": float(q[2])}


def read_pair(proposed: list[float], published: list[float]) -> dict:
    """The reading of two samples of a lower-is-better percentage (a dip below the mean, a spread) by ``extract_methods.cell_result``:
    ``proposed``, ``published`` or ``tie``, with the seeds behind each side. The rule is the benchmark's, imported once."""
    def row(method, v):
        return {"method": method, "n_seeds": len(v), "efficiency": {"median": 1.0}, "rel_std_pct": _quartiles(v), "budget_kind": "time"}
    r = X.cell_result([row("B2", proposed), row("M16", published)])
    return {"result": r["result"], "reason": r["reason"], "n_proposed": len(proposed), "n_published": len(published)}


def dip_pct(ratio: float) -> float:
    """The lowest intensity as a dip below the mean, in percent (lower is better): ``100 (1 - ratio)``."""
    return 100.0 * (1.0 - ratio)


def readings(rows: list[dict], key=lambda r: r, metric: str = "transient_min_ratio") -> dict:
    """B2 against each published sequence over the seeds of ``rows``, on the dip of ``metric`` and on the per-frame spread."""
    out = {}
    for other in ("lpi", "kim5", "kim10"):
        out[other] = {"dip": read_pair([dip_pct(key(r)["b2"][metric]) for r in rows], [dip_pct(key(r)[other][metric]) for r in rows]),
                      "sigma": read_pair([key(r)["b2"]["sigma_frame_max"] for r in rows], [key(r)[other]["sigma_frame_max"] for r in rows])}
    return out


# ------------------------------------------------------------------------------------------------ outputs

def accept_summary(data: dict) -> dict:
    out = {}
    for frames in data["frames_list"]:
        sel = [r for r in data["runs"] if r["frames"] == frames]
        out[str(frames)] = {"readings": readings(sel), "n": len(sel)}
        for k in METHODS:
            out[str(frames)][k] = {m: stats2([r[k][m] for r in sel]) for m in
                                   ("frame_min_ratio", "transient_min_ratio", "blend_min_ratio", "phase_step_max", "sigma_frame_max", "seconds")}
    return out


def figures(data: dict) -> dict:
    ac, summ = data["accept"], data["accept_summary"]
    f = {"transient_curves": ac["curves"]}
    f["ratio_vs_frames"] = {k: [{"frames": fr, **{m: summ[str(fr)][k][m]["median"] for m in ("frame_min_ratio", "transient_min_ratio")},
                                "min": summ[str(fr)][k]["transient_min_ratio"]["min"], "max": summ[str(fr)][k]["transient_min_ratio"]["max"]}
                               for fr in ac["frames_list"]] for k in METHODS}
    first = [r for r in ac["runs"] if r["frames"] == 13 and r["seed"] == ac["seeds"][0]][0]
    f["phase_steps"] = {k: first[k]["phase_step_per_trap"] for k in METHODS}
    mv = data["long"]["moves"]
    pts = [{"move": "4 bins", "fourier_units": ac["bound"]["fourier_units"], "frames_bound": ac["bound"]["frames_bound"], "frames_used": 13,
            "peak_step_fu": ac["bound"]["peak_step_fu"]}]
    for key in ("12", "20"):
        pts.append({"move": f"{key} bins", "fourier_units": mv[key]["fourier_units"], "frames_bound": mv[key]["frames_bound"],
                    "frames_used": mv[key]["frames"], "peak_step_fu": mv[key]["peak_step_fu"]})
    c = data["c10"]
    pts.append({"move": "C10 sort", "fourier_units": c["fourier_units"], "frames_bound": c["frames_bound"], "frames_used": c["frames_bound"],
                "peak_step_fu": c["peak_step_fu"]})
    f["frames_vs_move"] = pts
    f["long_and_sort"] = {"12": [{"seed": r["seed"], **{k: r[k]["transient_min_ratio"] for k in METHODS}} for r in mv["12"]["rows"]],
                          "20": [{"seed": r["seed"], **{k: r[k]["transient_min_ratio"] for k in METHODS}} for r in mv["20"]["rows"]],
                          "c10": [{"seed": r["seed"], **{k: r["bound"][k]["transient_min_ratio"] for k in METHODS}} for r in c["rows"]]}
    f["ablation"] = {k: [r[k]["min"] for r in data["ablation"]["rows"]] for k in B2_VARIANTS}
    f["seconds"] = {k: [{"frames": fr, "seconds": summ[str(fr)][k]["seconds"]["median"]} for fr in ac["frames_list"]] for k in METHODS}
    return f


CAMEL = {"b2": "B", "lpi": "Lpi", "kim5": "KimFive", "kim10": "KimTen"}
ABL_CAMEL = {"full": "Full", "no_lock": "NoLock", "no_opt": "NoOpt", "iters_1": "ItersOne", "iters_3": "ItersThree", "linear": "Linear"}


def write_macros(data: dict, path: Path) -> None:
    ac, sm = data["accept"], data["accept_summary"]
    L = ["% Generated by data/measure.py from flicker.json. Do not edit.\n"]
    L.append(macro("engineRelease", data["engine_version"]))
    L.append(macro("parFrames", B2.DEFAULT_FRAMES))
    L.append(macro("parFrameIters", B2.DEFAULT_FRAME_ITERATIONS))
    L.append(macro("parKimIters", M16.FRAME_ITERATIONS))
    L.append(macro("parPhaseVel", f"{B2.DEFAULT_PHASE_VELOCITY_MAX:g}"))
    L.append(macro("parSubsteps", 10))
    L.append(macro("claimStepFu", f"{B2.CLAIM_STEP_FU:g}"))
    L.append(macro("scopeDefaultFrames", B2.DEFAULT_FRAMES))
    L.append(macro("scopePhaseVel", "1"))
    L.append(macro("winMinSeeds", X.WIN_MIN_SEEDS))
    L.append(macro("winMinDiff", f"{X.WIN_MIN_DIFF_PCT:g}"))
    s13 = sm["13"]
    n = s13["n"]
    L.append(macro("nSeedsTwo", n))
    for k in METHODS:
        c = CAMEL[k]
        for m, nm in (("transient_min_ratio", "Trans"), ("frame_min_ratio", "Frame"), ("blend_min_ratio", "Blend"), ("phase_step_max", "Step"),
                      ("sigma_frame_max", "Sigma"), ("seconds", "Sec")):
            v = s13[k][m]
            d = 3 if m != "seconds" else 2
            L += [macro(f"acc{c}{nm}Med", fmt(v["median"], d)), macro(f"acc{c}{nm}Min", fmt(v["min"], d)), macro(f"acc{c}{nm}Max", fmt(v["max"], d)),
                  macro(f"acc{c}{nm}Mean", fmt(v["mean"], d)), macro(f"acc{c}{nm}CiLo", fmt(v["ci_lo"], d)), macro(f"acc{c}{nm}CiHi", fmt(v["ci_hi"], d))]
    # the names the device-aware paper's text used for the same quantities (0.02.003), kept so a moved sentence still reads its macros
    b, l = s13["b2"]["transient_min_ratio"], s13["lpi"]["transient_min_ratio"]
    L += [macro("bTwoMin", fmt(b["min"], 3)), macro("bTwoMed", fmt(b["median"], 3)), macro("bTwoMax", fmt(b["max"], 3)),
          macro("lpiMin", fmt(l["min"], 3)), macro("lpiMed", fmt(l["median"], 3)), macro("lpiMax", fmt(l["max"], 3)),
          macro("bTwoSigmaFrame", fmt(s13["b2"]["sigma_frame_max"]["max"], 2)),
          macro("lpiSigmaFrameMin", fmt(s13["lpi"]["sigma_frame_max"]["min"], 0)), macro("lpiSigmaFrameMax", fmt(s13["lpi"]["sigma_frame_max"]["max"], 0)),
          macro("bTwoSigmaFrameMed", fmt(s13["b2"]["sigma_frame_max"]["median"], 2)), macro("lpiSigmaFrameMed", fmt(s13["lpi"]["sigma_frame_max"]["median"], 1)),
          macro("sigmaFrameFactorLo", fmt(s13["lpi"]["sigma_frame_max"]["min"] / s13["b2"]["sigma_frame_max"]["max"], 0)),
          macro("sigmaFrameFactorHi", fmt(s13["lpi"]["sigma_frame_max"]["max"] / s13["b2"]["sigma_frame_max"]["max"], 0)),
          macro("bTwoMean", fmt(b["mean"], 3)), macro("bTwoSd", fmt(b["sd"], 3)), macro("bTwoCiLo", fmt(b["ci_lo"], 3)), macro("bTwoCiHi", fmt(b["ci_hi"], 3)),
          macro("lpiMean", fmt(l["mean"], 3)), macro("lpiSd", fmt(l["sd"], 3)), macro("lpiCiLo", fmt(l["ci_lo"], 3)), macro("lpiCiHi", fmt(l["ci_hi"], 3))]
    diff = stats2([r["b2"]["transient_min_ratio"] - r["lpi"]["transient_min_ratio"] for r in ac["runs"] if r["frames"] == 13])
    L += [macro("diffTwoMean", fmt(diff["mean"], 3)), macro("diffTwoCiLo", fmt(diff["ci_lo"], 3)), macro("diffTwoCiHi", fmt(diff["ci_hi"], 3))]
    for fr, nm in (("7", "Seven"), ("25", "TwentyFive")):
        if fr in sm:
            L += [macro(f"bTwoMed{nm}", fmt(sm[fr]["b2"]["transient_min_ratio"]["median"], 3)), macro(f"bTwoMin{nm}", fmt(sm[fr]["b2"]["transient_min_ratio"]["min"], 3)),
                  macro(f"lpiMed{nm}", fmt(sm[fr]["lpi"]["transient_min_ratio"]["median"], 3)), macro(f"lpiMax{nm}", fmt(sm[fr]["lpi"]["transient_min_ratio"]["max"], 3))]
    # the reading of each comparison by the benchmark's rule, with its seeds
    for fr in sm:
        tag = {"7": "Seven", "13": "Thirteen", "25": "TwentyFive"}.get(fr, fr)
        for other in ("lpi", "kim5", "kim10"):
            for kind, kn in (("dip", "Dip"), ("sigma", "Sigma")):
                rd = sm[fr]["readings"][other][kind]
                L.append(macro(f"read{tag}{CAMEL[other]}{kn}", rd["result"]))
                L.append(macro(f"read{tag}{CAMEL[other]}{kn}N", f"{rd['n_proposed']} and {rd['n_published']}"))
    bnd = ac["bound"]
    L += [macro("accFu", fmt(bnd["fourier_units"], 2)), macro("accPeakStep", fmt(bnd["peak_step_fu"], 2)),
          macro("accFramesForMove", bnd["frames_bound"]), macro("accFramesBoundMinimum", bnd["frames_bound_minimum"])]
    import math as _m  # noqa: PLC0415

    def sinc2_half(delta: float) -> float:
        x = _m.pi * delta / 2.0
        return 1.0 if x == 0 else (_m.sin(x) / x) ** 2

    lo, hi = 1e-9, 2.0  # sinc^2(delta / 2) falls from 1 to 0 on (0, 2): bisection for the shift at which it equals 0.9
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if sinc2_half(mid) > 0.9 else (lo, mid)
    L += [macro("deltaNine", fmt(0.5 * (lo + hi), 3)), macro("sincAcc", fmt(sinc2_half(bnd["peak_step_fu"]), 3)),
          macro("sincClaim", fmt(sinc2_half(B2.CLAIM_STEP_FU), 3))]
    # the long moves
    mv, shorts = data["long"]["moves"], []
    for key, nm in (("12", "A"), ("20", "B")):
        lg = mv[key]
        enough = [r["b2"]["transient_min_ratio"] for r in lg["rows"]]
        shorts += [r["b2_default_frames"]["transient_min_ratio"] for r in lg["rows"]]
        L += [macro(f"long{nm}Bins", lg["bins"]), macro(f"long{nm}Fu", f"{lg['fourier_units']:g}"), macro(f"long{nm}Frames", lg["frames"]),
              macro(f"long{nm}Med", fmt(statistics.median(enough), 3)), macro(f"long{nm}Met", sum(x >= 0.9 for x in enough)),
              macro(f"long{nm}Low", fmt(min(enough), 3)), macro(f"long{nm}PeakStep", fmt(lg["peak_step_fu"], 3)),
              macro(f"long{nm}Bound", lg["frames_bound"])]
        for k in ("lpi", "kim5", "kim10"):
            v = [r[k]["transient_min_ratio"] for r in lg["rows"]]
            L += [macro(f"long{nm}{CAMEL[k]}Min", fmt(min(v), 3)), macro(f"long{nm}{CAMEL[k]}Max", fmt(max(v), 3)),
                  macro(f"long{nm}BLeads{CAMEL[k]}", sum(1 for r in lg["rows"] if r["b2"]["transient_min_ratio"] > r[k]["transient_min_ratio"]))]
        L += [macro(f"long{nm}BLeads", sum(1 for r in lg["rows"] if r["b2"]["transient_min_ratio"] > r["lpi"]["transient_min_ratio"])),
              macro(f"long{nm}LpiMin", fmt(min(r["lpi"]["transient_min_ratio"] for r in lg["rows"]), 3)),
              macro(f"long{nm}LpiMax", fmt(max(r["lpi"]["transient_min_ratio"] for r in lg["rows"]), 3))]
        rd = readings(lg["rows"])
        for k in ("lpi", "kim5", "kim10"):
            L.append(macro(f"long{nm}Read{CAMEL[k]}", rd[k]["dip"]["result"]))
    L += [macro("longSeeds", len(mv["12"]["rows"])), macro("longAPeak", fmt(mv["12"]["peak_step_fu"], 3)), macro("longBPeak", fmt(mv["20"]["peak_step_fu"], 3))]
    fails, twice = [], []
    for key in ("12", "20"):
        bad = [r for r in mv[key]["rows"] if r["b2"]["transient_min_ratio"] < 0.9]
        if bad:
            fails.append(" and ".join(f"{r['b2']['transient_min_ratio']:.3f}" for r in bad) + f" at {key} bins")
        bt = [r for r in mv[key]["rows"] if "b2_twice" in r]
        if bt:
            twice.append(" and ".join(f"{r['b2_twice']['transient_min_ratio']:.3f}" for r in bt) + f" at {key} bins")
    L += [macro("longFailList", "; ".join(fails) if fails else "none"), macro("longTwiceList", "; ".join(twice) if twice else "none"),
          macro("longDefaultMax", fmt(max(shorts), 3))]
    # C10
    c = data["c10"]
    rows = c["rows"]
    eq = lambda k: [r["equal"][k]["transient_min_ratio"] for r in rows]  # noqa: E731
    bd = lambda k: [r["bound"][k]["transient_min_ratio"] for r in rows]  # noqa: E731
    met = [x for x in bd("b2") if x >= 0.9]
    L += [macro("cTenMoving", c["moving"]), macro("cTenTraps", c["n_traps"]), macro("cTenFu", fmt(c["fourier_units"], 1)),
          macro("cTenFrames", c["frames_bound"]), macro("cTenEqual", c["equal_frames"]), macro("cTenPeakEqual", fmt(c["peak_step_equal"], 2)),
          macro("cTenPeak", fmt(c["peak_step_fu"], 3)), macro("cTenHeld", fmt(c["held_equal_first_seed"], 3)), macro("cTenSeeds", len(rows)),
          macro("cTenLpiLeads", sum(a > b_ for a, b_ in zip(eq("lpi"), eq("b2")))), macro("cTenBEqualMax", fmt(max(eq("b2")), 3)),
          macro("cTenLEqualMin", fmt(min(eq("lpi")), 3)), macro("cTenLEqualMax", fmt(max(eq("lpi")), 3)),
          macro("cTenMet", len(met)), macro("cTenMetMin", fmt(min(met), 3) if met else "n/a"), macro("cTenMetMax", fmt(max(met), 3) if met else "n/a"),
          macro("cTenMetMed", fmt(statistics.median(met), 3) if met else "n/a"), macro("cTenLowest", fmt(min(bd("b2")), 3)),
          macro("cTenLpiMin", fmt(min(bd("lpi")), 3)), macro("cTenLpiMax", fmt(max(bd("lpi")), 3)),
          macro("cTenBLeads", sum(a > b_ for a, b_ in zip(bd("b2"), bd("lpi"))))]
    for k in ("kim5", "kim10"):
        L += [macro(f"cTen{CAMEL[k]}Min", fmt(min(bd(k)), 3)), macro(f"cTen{CAMEL[k]}Max", fmt(max(bd(k)), 3)),
              macro(f"cTenBLeads{CAMEL[k]}", sum(a > b_ for a, b_ in zip(bd("b2"), bd(k))))]
    bad = [r for r in rows if r["bound"]["b2"]["transient_min_ratio"] < 0.9]
    L.append(macro("cTenFailList", "; ".join(f"seed {r['seed']} at {r['bound']['b2']['transient_min_ratio']:.3f} against {r['bound']['lpi']['transient_min_ratio']:.3f} for LPI" for r in bad) or "none"))
    rdc = readings([r["bound"] for r in rows])
    for k in ("lpi", "kim5", "kim10"):
        L += [macro(f"cTenRead{CAMEL[k]}", rdc[k]["dip"]["result"]), macro(f"cTenRead{CAMEL[k]}N", f"{rdc[k]['dip']['n_proposed']} and {rdc[k]['dip']['n_published']}")]
    # phase continuity: the per-frame GS never jumps, linear phase interpolation and the lock stay below the bound
    L += [macro("phaseStepBMax", fmt(max(r["b2"]["phase_step_max"] for r in ac["runs"] if r["frames"] == 13), 3)),
          macro("phaseStepKimFiveMax", fmt(max(r["kim5"]["phase_step_max"] for r in ac["runs"] if r["frames"] == 13), 3)),
          macro("phaseStepKimTenMax", fmt(max(r["kim10"]["phase_step_max"] for r in ac["runs"] if r["frames"] == 13), 3)),
          macro("phaseStepLpiMax", fmt(max(r["lpi"]["phase_step_max"] for r in ac["runs"] if r["frames"] == 13), 3))]
    ab = data["ablation"]
    for k, v in ab["summary"].items():
        nm = f"ablT{ABL_CAMEL[k]}"
        L += [macro(nm + "Med", fmt(v["min"]["median"], 3)), macro(nm + "Min", fmt(v["min"]["min"], 3)), macro(nm + "Max", fmt(v["min"]["max"], 3)),
              macro(nm + "Mean", fmt(v["min"]["mean"], 3)), macro(nm + "Sd", fmt(v["min"]["sd"], 3)),
              macro(nm + "Sig", fmt(v["sigma_frame_max"]["median"], 2)), macro(nm + "Step", fmt(v["phase_step_max"]["median"], 3))]
    L += [macro("ablTN", ab["summary"]["full"]["min"]["n"]), macro("ablTCheck", f"{ab['max_check_full_vs_b2run']:.1e}"),
          macro("ablSeconds", fmt(sum(r["seconds"] for r in ab["rows"]) / 60.0, 0))]
    total = sum(r[k]["seconds"] for r in ac["runs"] for k in METHODS) + sum(ab_r["seconds"] for ab_r in ab["rows"])
    L.append(macro("mainMinutes", fmt(total / 60.0, 0)))
    path.write_text("".join(L), encoding="utf-8")


def write_tables(data: dict, out: Path) -> None:
    sm = data["accept_summary"]
    # T1 the acceptance task at 13 frames
    s13 = sm["13"]
    L = ["\\begin{tabular}{@{}l r r r r r r@{}}\n\\toprule\n",
         row_cells(["Sequence", "Transient minimum ratio, mean (95\\% interval)", "Per-frame minimum ratio", "Largest phase step (rad)",
                    "Largest frame $\\sigma$ (\\%)", "Seconds", "Reading against the flicker-bounded sequence"]),
         "\\midrule\n"]
    for k in METHODS:
        t = s13[k]["transient_min_ratio"]
        rd = "" if k == "b2" else f"{s13['readings'][k]['dip']['result']} ($n$ = {s13['readings'][k]['dip']['n_proposed']}, {s13['readings'][k]['dip']['n_published']})"
        L.append(row_cells([LABEL[k], f"{fmt(t['mean'], 3)} ({fmt(t['ci_lo'], 3)} to {fmt(t['ci_hi'], 3)})", fmt(s13[k]["frame_min_ratio"]["median"], 3),
                            fmt(s13[k]["phase_step_max"]["max"], 3), fmt(s13[k]["sigma_frame_max"]["median"], 2),
                            fmt(s13[k]["seconds"]["median"], 2), rd]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_main.tex").write_text("".join(L), encoding="utf-8")
    # T2 the frame counts
    L = ["\\begin{tabular}{@{}l l r r r r@{}}\n\\toprule\n", row_cells(["Frames", "Sequence", "Transient minimum ratio, median", "Range", "Per-frame minimum ratio, median", "$n$"]),
         "\\midrule\n"]
    for fr in data["accept"]["frames_list"]:
        for k in METHODS:
            t = sm[str(fr)][k]["transient_min_ratio"]
            L.append(row_cells([str(fr), LABEL[k], fmt(t["median"], 3), f"{fmt(t['min'], 3)} to {fmt(t['max'], 3)}",
                                fmt(sm[str(fr)][k]["frame_min_ratio"]["median"], 3), str(t["n"])]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_frames.tex").write_text("".join(L), encoding="utf-8")
    # T3 long moves and the sort
    L = ["\\begin{tabular}{@{}l r l r r r r@{}}\n\\toprule\n", row_cells(["Move", "Frames", "Sequence", "Median", "Range", "Seeds at 0.9 or above", "Reading against the flicker-bounded sequence"]),
         "\\midrule\n"]
    blocks = [(f"lattice, {k} bins", data["long"]["moves"][k]["frames"], data["long"]["moves"][k]["rows"], lambda r: r) for k in ("12", "20")]
    blocks.append((f"rearrangement C10, {data['c10']['moving']} moving traps", data["c10"]["frames_bound"], data["c10"]["rows"], lambda r: r["bound"]))
    for name, frames, rows, key in blocks:
        rd = readings(rows, key)
        for k in METHODS:
            v = [key(r)[k]["transient_min_ratio"] for r in rows]
            L.append(row_cells([name, str(frames), LABEL[k], fmt(statistics.median(v), 3), f"{fmt(min(v), 3)} to {fmt(max(v), 3)}",
                                f"{sum(x >= 0.9 for x in v)} of {len(v)}", "" if k == "b2" else f"{rd[k]['dip']['result']} ($n$ = {len(v)})"]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_long.tex").write_text("".join(L), encoding="utf-8")
    # T4 the bound
    L = ["\\begin{tabular}{@{}l r r r r r r@{}}\n\\toprule\n", row_cells(["Move", "Longest move (Fourier units)", "Frames of the bound", "Frames used", "Peak step (Fourier units)", "Ratio reached, median", "Seeds at 0.9 or above"]),
         "\\midrule\n"]
    ac = data["accept"]["bound"]
    v13 = [r["b2"]["transient_min_ratio"] for r in data["accept"]["runs"] if r["frames"] == 13]
    L.append(row_cells(["lattice, 4 bins", fmt(ac["fourier_units"], 2), str(ac["frames_bound"]), "13", fmt(ac["peak_step_fu"], 3), fmt(statistics.median(v13), 3),
                        f"{sum(x >= 0.9 for x in v13)} of {len(v13)}"]))
    for key in ("12", "20"):
        lg = data["long"]["moves"][key]
        v = [r["b2"]["transient_min_ratio"] for r in lg["rows"]]
        L.append(row_cells([f"lattice, {key} bins", fmt(lg["fourier_units"], 2), str(lg["frames_bound"]), str(lg["frames"]), fmt(lg["peak_step_fu"], 3),
                            fmt(statistics.median(v), 3), f"{sum(x >= 0.9 for x in v)} of {len(v)}"]))
    c = data["c10"]
    for tag, frames, peak in (("equal", c["equal_frames"], c["peak_step_equal"]), ("bound", c["frames_bound"], c["peak_step_fu"])):
        v = [r[tag]["b2"]["transient_min_ratio"] for r in c["rows"]]
        L.append(row_cells([f"C10 sort, {frames} frames", fmt(c["fourier_units"], 2), str(c["frames_bound"]), str(frames), fmt(peak, 3), fmt(statistics.median(v), 3),
                            f"{sum(x >= 0.9 for x in v)} of {len(v)}"]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_bound.tex").write_text("".join(L), encoding="utf-8")
    # T5 the ablation
    ab = data["ablation"]
    L = ["\\begin{tabular}{@{}l r r r r r@{}}\n\\toprule\n",
         row_cells(["Variant", "Minimum ratio, mean $\\pm$ s.d.", "Range", "Seeds at 0.9 or above", "Largest frame $\\sigma$ (\\%)", "Largest phase step (rad)"]),
         "\\midrule\n"]
    for k, (label, _) in B2_VARIANTS.items():
        v, vals = ab["summary"][k], [r[k]["min"] for r in ab["rows"]]
        L.append(row_cells([label, f"{fmt(v['min']['mean'], 3)} $\\pm$ {fmt(v['min']['sd'], 3)}", f"{fmt(v['min']['min'], 3)} to {fmt(v['min']['max'], 3)}",
                            f"{sum(x >= 0.9 for x in vals)} of {len(vals)}", fmt(v["sigma_frame_max"]["median"], 2), fmt(v["phase_step_max"]["median"], 3)]))
    s = sm[str(ab["frames"])]
    for k in ("lpi", "kim5", "kim10"):
        t = s[k]["transient_min_ratio"]
        vals = [r[k]["transient_min_ratio"] for r in data["accept"]["runs"] if r["frames"] == ab["frames"]]
        L.append(row_cells([LABEL[k] + " (reference)", f"{fmt(t['mean'], 3)} $\\pm$ {fmt(t['sd'], 3)}", f"{fmt(t['min'], 3)} to {fmt(t['max'], 3)}",
                            f"{sum(x >= 0.9 for x in vals)} of {len(vals)}", fmt(s[k]["sigma_frame_max"]["median"], 2), fmt(s[k]["phase_step_max"]["median"], 3)]))
    L.append("\\bottomrule\n\\end{tabular}\n")
    (out / "tab_abl_b2.tex").write_text("".join(L), encoding="utf-8")


def write_all(data: dict, out: Path) -> None:
    data["accept_summary"] = accept_summary(data["accept"])
    data["figures"] = figures(data)
    write_macros(data, out / "flicker_numbers.tex")
    write_tables(data, out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seeds", type=int, default=6, help="seeds of the acceptance task")
    ap.add_argument("--frames", type=int, nargs="+", default=[13, 7, 25])
    ap.add_argument("--seeds-long", type=int, default=8)
    ap.add_argument("--seeds-c10", type=int, default=6)
    ap.add_argument("--seeds-abl", type=int, default=6)
    ap.add_argument("--parts", default="accept,long,c10,ablation", help="comma-separated parts to measure; the others are kept from the existing flicker.json")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--macros-only", action="store_true", help="rewrite the macros and tables from an existing flicker.json")
    a = ap.parse_args()
    out = Path(a.out)
    known = {"accept", "long", "c10", "ablation"}
    if a.macros_only:
        data = json.loads((out / "flicker.json").read_text(encoding="utf-8"))
        write_all(data, out)
        print("rewrote the macros and tables in", out)
        return 0
    parts = {x for x in a.parts.split(",") if x}
    if parts - known:
        ap.error(f"unknown parts {sorted(parts - known)}; known: {sorted(known)}")
    if min(a.seeds, a.seeds_long, a.seeds_c10, a.seeds_abl) < X.WIN_MIN_SEEDS:
        ap.error(f"every comparison needs at least {X.WIN_MIN_SEEDS} seeds (the rule of the benchmark)")
    data = {} if parts == known else json.loads((out / "flicker.json").read_text(encoding="utf-8"))
    data["engine_version"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if "accept" in parts:
        data["accept"] = measure_accept(list(range(1, a.seeds + 1)), a.frames)
    if "long" in parts:
        data["long"] = measure_long(list(range(1, a.seeds_long + 1)))
    if "c10" in parts:
        data["c10"] = measure_c10(list(range(1, a.seeds_c10 + 1)))
    if "ablation" in parts:
        data["ablation"] = measure_ablation(list(range(1, a.seeds_abl + 1)))
    write_all(data, out)
    (out / "flicker.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print("wrote", out / "flicker.json", out / "flicker_numbers.tex", "and the tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
