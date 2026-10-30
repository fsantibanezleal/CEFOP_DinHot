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
