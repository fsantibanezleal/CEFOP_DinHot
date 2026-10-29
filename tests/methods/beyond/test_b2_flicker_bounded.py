"""B2 flicker-bounded phase-continuous sequence.

Acceptance (SDD): minimum transient intensity of a moving trap at least 0.9 of its mean, against LPI. The baseline LPI
(linear phase interpolation, arXiv 2501.01391 as the dossier D3.2 transcribes it) is written here from that text because
unit E2's M16 is not on this branch: two independently computed endpoint holograms (phase-fixed WGS, 30 iterations),
each trap's position, amplitude and optical phase read from them (point-trap fields), linearly interpolated over the
same 13 steps (phase by the wrapped difference), and the Fourier transform inverted at every step (the superposition of
the interpolated spots; no per-frame optimization). Both sequences are scored by ``transient_min_ratio`` (the module's
documented blend model). Task: 4 x 4 lattice at 8 bins, the two right columns move 4 bins in x. Seeds: 3.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "optim"))
from e3_helpers import bin_grid, make_setup  # noqa: E402

from pipeline.model.holo.core.forward import point_trap_backproject, point_trap_projection, slm_field  # noqa: E402
from pipeline.model.holo.core.geometry import focal_bin_m  # noqa: E402
from pipeline.model.holo.core.metrics import rel_std, trap_intensities  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import TrapSet  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs  # noqa: E402
from pipeline.model.holo.methods.beyond import b2_flicker_bounded as B2  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402


def task(setup):
    start = bin_grid(setup, 4, 4, 8)
    b = focal_bin_m(setup)
    dest = TrapSet(replace(t, x_m=t.x_m + (4 * b if (i % 4) >= 2 else 0.0)) for i, t in enumerate(start))
    return start, dest


def lpi(setup, start, dest, rng, frames=13):
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


def test_spec():
    assert B2.SPEC.id == "B2" and B2.SPEC.targets == ("traps",)


def test_minimal_jerk_profile():
    t = np.linspace(0, 1, 11)
    h = B2.min_jerk(t)
    assert h[0] == 0 and h[-1] == 1 and np.all(np.diff(h) > 0) and B2.min_jerk(0.5) == pytest.approx(0.5)
    eps = 1e-5
    assert (B2.min_jerk(eps) - B2.min_jerk(0)) / eps < 1e-3      # zero velocity at the start


def test_wrap_pi_and_trajectory_endpoints():
    assert B2.wrap_pi(np.array([0.1, 3.5, -3.5])) == pytest.approx([0.1, 3.5 - 2 * np.pi, -3.5 + 2 * np.pi])
    s = make_setup(64)
    start, dest = task(s)
    at = B2.trajectory(start, dest, 13)
    assert np.allclose(at(0).x_m, start.x_m) and np.allclose(at(12).x_m, dest.x_m)
    with pytest.raises(ValueError, match="same trap ids"):
        B2.trajectory(start, TrapSet(list(dest)[:3]), 13)


def test_phase_velocity_bound_is_enforced():
    s = make_setup(64)
    start, _ = task(s)
    with pytest.raises(ValueError, match="phase_velocity_max"):
        B2.run(s, Target.from_traps(start), budget=Budget(12), rng=Rng(1), frames=13,
               end_phases=np.full(16, 3.0) + np.angle(np.exp(1j * np.arange(16))), phase_velocity_max=0.05)


def test_static_sequence_and_trap_phases_stay_locked():
    s = make_setup(64)
    start, _ = task(s)
    res = B2.run(s, Target.from_traps(start), budget=Budget(25), rng=Rng(2), frames=5)
    th0 = res.meta["theta0"]
    v = point_trap_projection(slm_field(res.phi, s), s, start)
    assert np.abs(B2.wrap_pi(np.angle(v) - th0)).max() < 0.1       # locked to the held phases
    assert res.meta["n_frames"] == 5 and res.meta["frames"].shape == (5, 64, 64)


def test_field_target_is_refused():
    s = make_setup(16)
    with pytest.raises(ValueError, match="traps"):
        B2.run(s, Target.from_field(np.ones((32, 32)), np.ones((32, 32), dtype=bool)), budget=Budget(1), rng=Rng(1))


def test_deterministic_for_a_seed():
    s = make_setup(64)
    start, dest = task(s)
    a = B2.run(s, Target.from_traps(start), budget=Budget(10), rng=Rng(3), destination=dest, frames=4)
    b = B2.run(s, Target.from_traps(start), budget=Budget(10), rng=Rng(3), destination=dest, frames=4)
    assert np.array_equal(a.meta["frames"], b.meta["frames"])


def test_acceptance_transient_intensity_at_least_0_9_and_above_lpi():
    s = make_setup(256)
    start, dest = task(s)
    for seed in (1, 2, 3):
        res = B2.run(s, Target.from_traps(start), budget=Budget(30), rng=Rng(seed), destination=dest)
        mv = res.meta["moving"]
        assert mv.sum() == 8
        b2 = res.meta["transient_ratio"][mv].min()
        phis, at = lpi(s, start, dest, Rng(100 + seed))
        base = B2.transient_min_ratio(s, phis, at)[mv].min()
        assert b2 >= 0.9, (seed, b2, base)
        assert b2 > base, (seed, b2, base)
        # per-hologram uniformity not worse than LPI, and 13 holograms (the 6x6 -> 4x4 sort of the dossier)
        assert res.meta["n_frames"] == 13
        lpi_sigma = max(rel_std(trap_intensities(point_trap_projection(slm_field(p, s), s, at(k)), start.weight))
                        for k, p in enumerate(phis))
        assert max(h["rel_std"] for h in res.history) <= lpi_sigma


# ---- the limit of the claim on long moves (I3) ----------------------------------------------------------------

def long_move(setup, bins):
    """The acceptance lattice with its two right columns moved ``bins`` focal bins in x, and the moving mask."""
    start = bin_grid(setup, 4, 4, 8)
    b = focal_bin_m(setup)
    dest = TrapSet(replace(t, x_m=t.x_m + (bins * b if (i % 4) >= 2 else 0.0)) for i, t in enumerate(start))
    return start, dest, np.array([(i % 4) >= 2 for i in range(16)])


def test_frames_for_move_is_the_fewest_frames_under_the_peak_step():
    s = make_setup(64)
    start, dest, _ = long_move(s, 12)                      # 12 bins at padding 2 = 6 Fourier units
    assert B2.move_fourier_units(s, start, dest) == pytest.approx(6.0)
    assert B2.move_fourier_units(s, start, None) == 0.0
    assert B2.peak_step_fu(s, start, dest, 13) == pytest.approx(B2.PEAK_JERK * 6.0 / 12)
    n = B2.frames_for_move(s, start, dest)
    assert n == int(np.ceil(1.875 * 6.0 / B2.CLAIM_STEP_FU)) + 1 == 58
    assert B2.peak_step_fu(s, start, dest, n) <= B2.CLAIM_STEP_FU < B2.peak_step_fu(s, start, dest, n - 1)
    assert B2.frames_for_move(s, start, None) == B2.DEFAULT_FRAMES            # a static sequence needs no more
    assert B2.frames_for_move(s, start, dest, step_fu=0.4) < n                # a looser step needs fewer frames
    with pytest.raises(ValueError, match="step_fu"):
        B2.frames_for_move(s, start, dest, step_fu=0.0)


def test_the_peak_velocity_constant_is_that_of_the_minimal_jerk_profile():
    eps = 1e-6
    assert (B2.min_jerk(0.5 + eps) - B2.min_jerk(0.5 - eps)) / (2 * eps) == pytest.approx(B2.PEAK_JERK, rel=1e-6)


@pytest.mark.parametrize("bins", [12, 20])
def test_long_moves_meet_the_claim_with_the_frames_of_the_move_and_not_with_the_default(bins):
    """BS-2 on moves longer than the acceptance task's: the 13 default frames leave a peak step of several Fourier units and the
    lowest moving trap falls far below 0.9; the frames ``frames_for_move`` names (end phases given) bring it back above."""
    s = make_setup(64)
    start, dest, moving = long_move(s, bins)
    end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(dest), budget=Budget(30), rng=Rng(1)).fields)
    lowest = {}
    for frames in (B2.DEFAULT_FRAMES, B2.frames_for_move(s, start, dest)):
        res = B2.run(s, Target.from_traps(start), budget=Budget(30), rng=Rng(1), destination=dest, frames=frames,
                     end_phases=end, phase_velocity_max=1.0)
        assert res.meta["n_frames"] == frames
        lowest[frames] = res.meta["transient_ratio"][moving].min()
    short, enough = lowest[B2.DEFAULT_FRAMES], lowest[max(lowest)]
    assert short < 0.7, lowest
    assert enough >= 0.9, lowest


def test_the_sort_of_c10_the_limit_stated_in_the_docstring():
    """Case C10's sort (17 of 36 traps move, the longest by 29 bins) at the optical setup of the case: the held phases collapse,
    the end phases at 25 frames leave the lowest moving trap far under 0.9, and ``frames_for_move`` frames meet it."""
    from pipeline.cases import build, library
    from pipeline.io.contract import read_cases
    from pipeline.model.holo.methods.control.m16_rearrangement import assign
    rec = next(c for c in read_cases(ROOT / "data" / "examples" / "cases.json") if c["case_id"].startswith("C10"))
    s = build.setup_of(rec)
    sites = {t["id"]: t for t in rec["target"]["traps"]}
    loaded, wanted = library.random_loading(rec), rec["rearrangement"]["target_ids"]
    atoms = build.trapset_of([sites[i] for i in loaded])
    goal = build.trapset_of([sites[i] for i in wanted])
    pick = assign(np.c_[goal.x_m, goal.y_m], np.c_[atoms.x_m, atoms.y_m], 1.0)
    origin = TrapSet(replace(t, x_m=atoms.x_m[pick[i]], y_m=atoms.y_m[pick[i]]) for i, t in enumerate(goal))
    moving = np.array([np.hypot(a.x_m - g.x_m, a.y_m - g.y_m) > 0 for a, g in zip(origin, goal)])
    assert moving.sum() == 17 and B2.move_fourier_units(s, origin, goal) == pytest.approx(14.48, abs=0.01)
    end = np.angle(m07_phase_fixed_wgs.run(s, Target.from_traps(goal), budget=Budget(30), rng=Rng(1)).fields)

    def lowest(frames, phases):
        kw = {} if phases is None else {"end_phases": phases, "phase_velocity_max": 1.0}
        res = B2.run(s, Target.from_traps(origin), budget=Budget(30), rng=Rng(1), destination=goal, frames=frames, **kw)
        return res.meta["transient_ratio"][moving].min()

    def lpi_lowest(frames):
        """LPI on the SAME assignment (origin to goal) and scored by the same transient model."""
        phis, at = lpi(s, origin, goal, Rng(101), frames)
        return B2.transient_min_ratio(s, phis, at)[moving].min()

    assert lowest(25, None) < 0.1                                  # held phases: the traps go dark
    b25, l25 = lowest(25, end), lpi_lowest(25)
    assert b25 < 0.5                                               # end phases, peak step 1.1 Fourier units
    assert l25 > b25, (l25, b25)                                   # at 25 frames LPI leads B2 on this sort (measured 0.531 against 0.379)
    n = B2.frames_for_move(s, origin, goal)
    assert n == 137
    b137, l137 = lowest(n, end), lpi_lowest(n)
    assert b137 >= 0.9 and b137 > l137, (b137, l137)               # at 137 frames B2 meets BS-2 and leads LPI (0.904 against 0.691)
