"""M02: random superposition (SDD ladder; Di Leonardo et al. 2007 Table 1: e/u = 0.69/0.01)."""
from __future__ import annotations

import numpy as np

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m02_random_superposition as m

SEEDS = range(6)


def test_acceptance_10x10_over_seeds(setup256, grid10, evaluate):
    vals = np.array([evaluate(m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(s)).phi, grid10)
                     for s in SEEDS])
    e, u = vals[:, 0], vals[:, 1]
    assert np.all(np.abs(e - 0.69) <= 0.10), e   # published 0.69
    assert np.all(u < 0.35), u                   # poor uniformity (published 0.01; DinHot's grid measures about 0.25)
    assert np.median(e) > 0.5 and np.median(u) < 0.5


def test_efficiency_beats_superposition(setup256, grid10, evaluate):
    from pipeline.model.holo.methods.baseline import m01_superposition as m1
    t = Target.from_traps(grid10)
    e1 = evaluate(m1.run(setup256, t, budget=Budget(1), rng=Rng(1)).phi, grid10)[0]
    e2 = evaluate(m.run(setup256, t, budget=Budget(1), rng=Rng(1)).phi, grid10)[0]
    assert e2 > e1 + 0.2


def test_same_seed_same_phase_other_seed_differs(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(1), rng=Rng(7)).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(1), rng=Rng(7)).phi)
    assert not np.array_equal(a, m.run(setup256, t, budget=Budget(1), rng=Rng(8)).phi)


def test_spec():
    assert m.SPEC.id == "M02"
