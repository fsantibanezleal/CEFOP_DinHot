"""M09 direct search (Polin et al. 2005): acceptance of the SDD ladder row and the invariants of the brief.

Acceptance: uniformity at least 0.98 on the 10x10 task; under 5 percent rms variation on a quasi-periodic set.
Seeds: 2 for the 10x10 task and 1 for the 119-trap set (the benchmark protocol runs 20; test time budget 120 s).
"""
from __future__ import annotations

import numpy as np
import pytest
from e3_helpers import bin_grid, make_setup, quasi_periodic_119, task_10x10, trap_stats

from pipeline.model.holo.core.forward import point_trap_fields
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.optim import m09_direct_search as M09


def test_polin_cost_matches_the_equations():
    i = np.array([[0.2, 0.3, 0.5], [0.1, 0.1, 0.1]])
    design = np.array([1.0, 1.0, 2.0])
    f = 0.5
    got = M09.polin_cost(i, design, f)
    for k in range(2):
        gamma = np.sum(i[k] * design) / np.sum(design**2)
        sigma = np.sqrt(np.mean((i[k] - gamma * design) ** 2))
        assert got[k] == pytest.approx(-np.mean(i[k]) + f * sigma, rel=1e-12)


def test_spec():
    assert M09.SPEC.id == "M09" and M09.SPEC.targets == ("traps",) and "baked" in M09.SPEC.lane


def test_unsupported_target_names_the_supported_kinds():
    s = make_setup(32)
    t = Target.from_field(np.ones((64, 64)), np.ones((64, 64), dtype=bool))
    with pytest.raises(ValueError, match="traps"):
        M09.run(s, t, budget=Budget(1), rng=Rng(1))


def test_incremental_fields_equal_a_full_evaluation_and_cost_never_rises():
    s = make_setup(32)
    traps = bin_grid(s, 4, 4, 16)
    res = M09.run(s, Target.from_traps(traps), budget=Budget(2), rng=Rng(3), levels=8)
    v = point_trap_fields(res.phi, s, traps)
    assert np.allclose(v, res.fields, atol=1e-10)
    cost = [h["cost"] for h in res.history]
    assert all(b <= a + 1e-15 for a, b in zip(cost, cost[1:]))
    assert len(res.history) == 2
    assert set(np.unique(np.round(res.phi / (2 * np.pi) * 8, 9) % 8)) <= set(range(8))   # only the 8 trial levels


def test_trial_budget_is_honoured():
    s = make_setup(32)
    traps = bin_grid(s, 2, 2, 8)
    res = M09.run(s, Target.from_traps(traps), budget=Budget(50), rng=Rng(3), max_trials=500)
    assert res.meta["trials"] <= 500


def test_vortex_and_axial_traps_are_supported_by_the_point_trap_form():
    s = make_setup(32)
    traps = TrapSet([Trap(0, 3.3e-5, 0.0, 0.0), Trap(1, -3.3e-5, 0.0, 1e-5, charge=1), Trap(2, 0.0, 3.3e-5, -1e-5)])
    res = M09.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(3))
    assert np.allclose(point_trap_fields(res.phi, s, traps), res.fields, atol=1e-10)


def test_deterministic_for_a_seed():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 16)
    a = M09.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(7))
    b = M09.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(7))
    c = M09.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(8))
    assert np.array_equal(a.phi, b.phi) and not np.array_equal(a.phi, c.phi)


def test_acceptance_uniformity_on_the_10x10_task():
    s = make_setup(256)
    traps = task_10x10(s)
    us = []
    for seed in (1, 2):
        res = M09.run(s, Target.from_traps(traps), budget=Budget(M09.DEFAULT_SWEEPS), rng=Rng(seed))
        e, u, sig = trap_stats(res.phi, s, traps)
        us.append(u)
        assert e > 0.3
    assert min(us) >= 0.98, us


def test_acceptance_rms_variation_on_the_quasi_periodic_set():
    s = make_setup(256)
    traps = quasi_periodic_119(s)
    assert len(traps) == 119
    res = M09.run(s, Target.from_traps(traps), budget=Budget(M09.DEFAULT_SWEEPS), rng=Rng(1))
    e, u, sig = trap_stats(res.phi, s, traps)
    assert sig < 5.0, sig
