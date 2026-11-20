"""M16: Hungarian assignment and linear phase interpolation (SDD ladder; Lee, Kim and Ahn 2017; arXiv 2501.01391)."""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.control import m16_rearrangement as m


def brute_force(cost):
    n, k = cost.shape
    best = min(itertools.permutations(range(k), n), key=lambda p: sum(cost[i, c] for i, c in enumerate(p)))
    return list(best), float(sum(cost[i, c] for i, c in enumerate(best)))


@pytest.mark.parametrize("n,k", [(1, 1), (2, 2), (3, 5), (4, 4), (5, 7), (6, 6), (7, 7), (3, 7)])
def test_hungarian_matches_brute_force(n, k):
    rg = np.random.default_rng(100 * n + k)
    for _ in range(12):
        cost = rg.random((n, k)) * 10
        cols, total = m.hungarian(cost)
        _, ref = brute_force(cost)
        assert len(set(cols)) == n and abs(total - ref) < 1e-9, (cols, total, ref)
        assert abs(sum(cost[i, c] for i, c in enumerate(cols)) - total) < 1e-9


def test_hungarian_ties_integer_costs_and_validation():
    cost = np.array([[1.0, 1.0], [1.0, 1.0]])
    cols, total = m.hungarian(cost)
    assert sorted(cols) == [0, 1] and total == 2.0
    with pytest.raises(ValueError):
        m.hungarian(np.ones((3, 2)))            # more rows than columns
    with pytest.raises(ValueError):
        m.hungarian(np.array([[np.nan, 1.0]]))


def lattice_sites(setup, n=7, spacing_bins=8):
    b = focal_bin_m(setup)
    return [((i - (n - 1) / 2) * spacing_bins * b, (j - (n - 1) / 2) * spacing_bins * b) for j in range(n) for i in range(n)]


def central_3x3(setup, spacing_bins=8):
    b = focal_bin_m(setup)
    return TrapSet(Trap(k, (i - 1) * spacing_bins * b, (j - 1) * spacing_bins * b)
                   for k, (j, i) in enumerate(itertools.product(range(3), range(3))))


def loading(setup, seed):
    sites = lattice_sites(setup)
    rg = np.random.default_rng(seed)
    pick = rg.choice(len(sites), size=21, replace=False)
    return TrapSet(Trap(k, *sites[p]) for k, p in enumerate(sorted(pick)))


def test_no_crossing_moves_for_alpha_1_5_on_7x7_to_3x3(setup256):
    """SDD: no crossing moves for alpha 1.5 on a 7x7 to 3x3 sort (21 atoms), over 60 random loadings."""
    targets = central_3x3(setup256)
    b = focal_bin_m(setup256)
    for seed in range(60):
        atoms = loading(setup256, seed)
        f = m.assign(np.c_[targets.x_m, targets.y_m] / b, np.c_[atoms.x_m, atoms.y_m] / b, alpha=1.5)
        starts = np.c_[atoms.x_m, atoms.y_m][f] / b
        ends = np.c_[targets.x_m, targets.y_m] / b
        assert m.count_crossings(starts, ends) == 0, seed


def test_crossing_counter_detects_crossings():
    assert m.count_crossings(np.array([[0.0, 0.0], [1.0, 0.0]]), np.array([[1.0, 1.0], [0.0, 1.0]])) == 1
    assert m.count_crossings(np.array([[0.0, 0.0], [0.0, 1.0]]), np.array([[1.0, 0.0], [1.0, 1.0]])) == 0
    assert m.count_crossings(np.array([[0.0, 0.0], [1.0, 0.0]]), np.array([[3.0, 0.0], [2.0, 0.0]])) == 1   # overlap


def test_lpi_keeps_moving_traps_above_70_percent(setup256):
    """SDD: a moving trap stays above 70 percent of its mean intensity (min over the steps / mean over the steps)."""
    targets = central_3x3(setup256)
    worst, n_moving = 1.0, 0
    for seed in range(5):
        atoms = loading(setup256, seed)
        r = m.run(setup256, Target.from_traps(targets), budget=Budget(30), rng=Rng(seed + 1), atoms=atoms)
        moving = r.meta["moved"]
        n_moving += int(moving.sum())
        assert r.meta["crossings"] == 0
        worst = min(worst, float(r.meta["min_ratio"][moving].min()))
        n_steps = r.meta["n_steps"]
        assert r.meta["frames"].shape == (n_steps + 1, 256, 256) and len(r.history) == n_steps + 1
        assert np.array_equal(r.phi, r.meta["frames"][-1])
    assert n_moving >= 15
    assert worst >= 0.70, worst


def test_deterministic_and_validation(setup256):
    targets = central_3x3(setup256)
    atoms = loading(setup256, 5)
    a = m.run(setup256, Target.from_traps(targets), budget=Budget(8), rng=Rng(2), atoms=atoms).phi
    assert np.array_equal(a, m.run(setup256, Target.from_traps(targets), budget=Budget(8), rng=Rng(2), atoms=atoms).phi)
    with pytest.raises(ValueError, match="atoms"):
        m.run(setup256, Target.from_traps(targets), budget=Budget(1), rng=Rng(1))
    few = TrapSet(list(atoms)[:4])
    with pytest.raises(ValueError, match="fewer"):
        m.run(setup256, Target.from_traps(targets), budget=Budget(1), rng=Rng(1), atoms=few)
    n = setup256.n_fft
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(np.ones((n, n)), np.ones((n, n), bool)), budget=Budget(1), rng=Rng(1), atoms=atoms)


# ------------------------------------------------------------------ the hologram-sequence option (MD-025)
# Kim, Kim, Lee and Ahn 2019, Opt. Express 27(3), 2184: weighted GS per frame, the previous frame's phase as the initial phase
# of the next ("induction GS", section 3.3, p. 2188), a fixed number of iterations per frame (5 in the Monte-Carlo of Fig. 3, p. 2190).
import time  # noqa: E402

from pipeline.model.holo.core import forward as F  # noqa: E402
from pipeline.model.holo.core.forward import point_trap_fields  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402


def _seq(setup, seed=2, atoms_seed=3, **kw):
    return m.run(setup, Target.from_traps(central_3x3(setup)), budget=Budget(12), rng=Rng(seed),
                 atoms=loading(setup, atoms_seed), **kw)


def _trap_phase_steps(r, setup):
    """Largest wrapped step of arg V_m between consecutive frames, per trap (the trap fields at that frame's positions)."""
    psi = np.array([np.angle(point_trap_fields(phi, setup, ts)) for phi, ts in zip(r.meta["frames"], r.meta["trap_sequence"])])
    return np.abs(np.angle(np.exp(1j * np.diff(psi, axis=0)))).max(axis=0)


def test_sequence_option_defaults_to_lpi_and_is_validated(setup256):
    a = _seq(setup256)
    b = _seq(setup256, sequence="lpi")
    assert np.array_equal(a.phi, b.phi) and a.meta["sequence"] == b.meta["sequence"] == "lpi"
    with pytest.raises(ValueError, match="sequence"):
        _seq(setup256, sequence="gs")
    with pytest.raises(ValueError, match="frame_iterations"):
        _seq(setup256, sequence="per-frame-gs", frame_iterations=0)
    assert m.FRAME_ITERATIONS == 5          # Kim et al. 2019, Fig. 3 caption (p. 2190): i = 5


def test_per_frame_gs_has_the_frame_count_of_lpi_for_the_same_trajectory(setup256):
    for seed in range(3):
        lpi = _seq(setup256, atoms_seed=seed)
        kim = _seq(setup256, atoms_seed=seed, sequence="per-frame-gs")
        assert kim.meta["n_steps"] == lpi.meta["n_steps"]
        assert kim.meta["frames"].shape == lpi.meta["frames"].shape and len(kim.history) == len(lpi.history)
        assert kim.meta["assignment"] == lpi.meta["assignment"] and kim.meta["crossings"] == lpi.meta["crossings"]
        assert np.array_equal(kim.phi, kim.meta["frames"][-1]) and kim.meta["sequence"] == "per-frame-gs"
        assert not kim.meta["truncated"] and kim.meta["frames_done"] == kim.meta["n_steps"] + 1


def test_per_frame_gs_trap_phases_do_not_jump_between_frames(setup256):
    """Must refute: a per-frame sequence whose trap phases jump between frames. The same frames from independent starts
    (no induction) are the control: their trap phases are free and jump by about pi (measured: median over traps of the
    largest step 2.6 to 2.9 rad, against 0.3 to 0.5 with induction)."""
    for seed in range(3):
        kim = _seq(setup256, atoms_seed=seed, sequence="per-frame-gs")
        steps = _trap_phase_steps(kim, setup256)
        rg, free = Rng(9), []
        for ts in kim.meta["trap_sequence"]:
            phi, _ = G.weighted_gs(setup256, ts, m.FRAME_ITERATIONS, rg, variant="gsw")
            free.append(np.angle(point_trap_fields(phi, setup256, ts)))
        free_steps = np.abs(np.angle(np.exp(1j * np.diff(np.array(free), axis=0)))).max(axis=0)
        assert steps.max() < 1.5, (seed, steps.max())
        assert np.median(free_steps) > 2.0 and np.median(steps) < 0.3 * np.median(free_steps), (seed, np.median(steps), np.median(free_steps))
        assert np.array_equal(kim.meta["max_phase_step"], steps)


def test_per_frame_gs_keeps_the_moving_traps_lit(setup256):
    worst = 1.0
    for seed in range(3):
        r = _seq(setup256, atoms_seed=seed, sequence="per-frame-gs")
        moved = r.meta["moved"]
        if moved.any():
            worst = min(worst, float(r.meta["min_ratio"][moved].min()))
    assert worst >= 0.7, worst          # Kim et al. 2019 Fig. 3(c): an average transient minimum above 0.8 with induction


def test_a_static_trajectory_gives_the_same_hologram_on_every_frame(setup256):
    """No atom moves: both frames are GS iterates of the same target, so their trap intensities agree to the GS tolerance."""
    t = central_3x3(setup256)
    r = m.run(setup256, Target.from_traps(t), budget=Budget(12), rng=Rng(1), atoms=t, sequence="per-frame-gs")
    assert r.meta["n_steps"] == 1 and not r.meta["moved"].any()
    i0, i1 = (np.abs(point_trap_fields(phi, setup256, t)) ** 2 for phi in r.meta["frames"])
    assert np.max(np.abs(i1 - i0)) <= 0.02 * i0.mean(), (i0, i1)
    assert _trap_phase_steps(r, setup256).max() < 0.2


def test_per_frame_gs_counts_its_iterations_and_evaluations(setup256):
    F.reset_evaluations()
    r = _seq(setup256, sequence="per-frame-gs")
    n_eval = F.evaluations()
    total = 12 + r.meta["n_steps"] * m.FRAME_ITERATIONS          # frame 0 runs budget.iterations, each later frame frame_iterations
    assert r.meta["iterations"] == total
    assert n_eval >= 2 * total
    r2 = _seq(setup256, sequence="per-frame-gs", frame_iterations=2)
    assert r2.meta["iterations"] == 12 + r2.meta["n_steps"] * 2


def test_per_frame_gs_honours_the_deadline(setup256):
    """Must refute: a new option that overruns the deadline. A cut run keeps the frames it reached and says so."""
    full = _seq(setup256, sequence="per-frame-gs")
    t0 = time.perf_counter()
    _seq(setup256, sequence="per-frame-gs")
    per_run = time.perf_counter() - t0
    budget_s = per_run / 4.0
    t0 = time.perf_counter()
    cut = m.run(setup256, Target.from_traps(central_3x3(setup256)), budget=Budget(12, budget_s), rng=Rng(2),
                atoms=loading(setup256, 3), sequence="per-frame-gs")
    took = time.perf_counter() - t0
    assert cut.meta["truncated"] and 1 <= cut.meta["frames_done"] < full.meta["n_steps"] + 1
    assert cut.meta["frames"].shape[0] == cut.meta["frames_done"] == len(cut.history)
    assert cut.meta["n_steps"] == full.meta["n_steps"]
    assert cut.meta["iterations"] < full.meta["iterations"]
    assert took <= budget_s + 0.5 * per_run + 0.2, (took, budget_s, per_run)
    assert np.array_equal(cut.phi, cut.meta["frames"][-1])
