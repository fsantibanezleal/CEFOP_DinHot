"""M05: generalized adaptive additive GS (SDD ladder; Di Leonardo 2007: alpha = 0.5 gives e/u = 0.93/0.79 at 30 iterations)."""
from __future__ import annotations

import numpy as np

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m04_gs
from pipeline.model.holo.methods.baseline import m05_gaa as m

SEEDS = (1, 2, 3, 4, 5)


def test_uniformity_above_gs_at_equal_iterations(setup256, grid10, evaluate):
    t = Target.from_traps(grid10)
    gs, gaa = [], []
    for s in SEEDS:
        a = m04_gs.run(setup256, t, budget=Budget(30), rng=Rng(s))
        b = m.run(setup256, t, budget=Budget(30), rng=Rng(s))
        gs.append(evaluate(a.phi, grid10))
        gaa.append(evaluate(b.phi, grid10))
    gs, gaa = np.array(gs), np.array(gaa)
    assert np.all(gaa[:, 1] > gs[:, 1]), (gs[:, 1], gaa[:, 1])      # per seed
    assert np.median(gaa[:, 1]) > np.median(gs[:, 1]) + 0.05
    assert np.all(gaa[:, 0] > 0.95 * gs[:, 0])                        # efficiency close to GS (published 0.93 vs 0.94)


def test_alpha_zero_is_gs(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(6), rng=Rng(3), alpha=0.0)
    b = m04_gs.run(setup256, t, budget=Budget(6), rng=Rng(3))
    assert np.abs(np.angle(np.exp(1j * (a.phi - b.phi)))).max() < 1e-9


def test_alpha_default_is_half_and_deterministic(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(4), rng=Rng(3))
    b = m.run(setup256, t, budget=Budget(4), rng=Rng(3), alpha=0.5)
    assert np.array_equal(a.phi, b.phi)


def test_printed_absolute_bracket_runs_and_differs(setup256, grid10):
    """The bracket exactly as printed is scale dependent (see the module docstring); it is selectable and deterministic."""
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(4), rng=Rng(3), scale="absolute")
    assert np.array_equal(a.phi, m.run(setup256, t, budget=Budget(4), rng=Rng(3), scale="absolute").phi)
    assert not np.array_equal(a.phi, m.run(setup256, t, budget=Budget(4), rng=Rng(3)).phi)
