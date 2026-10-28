"""M07: phase-fixed weighted GS (SDD ladder; Kim et al. 2019: 50x30 foci, 12 iterations before fixing, 91.2 percent efficiency)."""
from __future__ import annotations

import inspect

import numpy as np

from pipeline.model.holo.core.geometry import focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import square_grid
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m06_gsw
from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs as m


def _first_below(history, pct):
    for h in history:
        if h["rel_std"] <= pct:
            return h["iteration"]
    return None


def test_acceptance_fewer_iterations_than_gsw_on_50x30(setup256):
    """Iterations to a relative standard deviation of 0.5 percent, both methods in the FFT form, 2 seeds.

    On this crowded grid (44 pixels per trap against Kim's much larger SLM) freezing the phase after Kim's 12 iterations
    saturates near 5 percent; freezing after 60 iterations converges (next test pins the measured saturation).
    """
    tr = square_grid(50, 30, 8 * focal_bin_m(setup256) * 1e6)
    t = Target.from_traps(tr)
    for s in (1, 2):
        a = m.run(setup256, t, budget=Budget(150), rng=Rng(s), n_fix=60)
        b = m06_gsw.run(setup256, t, budget=Budget(150), rng=Rng(s), form="fft")
        ia, ib = _first_below(a.history, 0.5), _first_below(b.history, 0.5)
        assert ia is not None, (s, [round(h["rel_std"], 3) for h in a.history[-5:]])
        assert ib is None or ia < ib, (s, ia, ib)
        assert a.history[-1]["efficiency"] > 0.6


def test_kim_n_fix_12_saturates_on_the_crowded_grid(setup256):
    """Measured limit of the literal Kim setting on DinHot's 256-pixel grid: the phase frozen at 12 stalls above 0.5 percent."""
    tr = square_grid(50, 30, 8 * focal_bin_m(setup256) * 1e6)
    a = m.run(setup256, Target.from_traps(tr), budget=Budget(40), rng=Rng(1))
    assert min(h["rel_std"] for h in a.history) > 0.5
    assert a.history[-1]["rel_std"] < 10


def test_n_fix_default_is_kim_12():
    assert inspect.signature(m.run).parameters["n_fix"].default == 12


def test_phase_is_fixed_after_n_fix(setup256, grid10):
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(20), rng=Rng(4), n_fix=5)
    assert r.meta["n_fix"] == 5 and len(r.meta["psi"]) == 100


def test_both_forms_agree_on_2d_grid(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(16), rng=Rng(5), form="point")
    b = m.run(setup256, t, budget=Budget(16), rng=Rng(5), form="fft")
    assert np.abs(np.angle(np.exp(1j * (a.phi - b.phi)))).max() < 1e-5


def test_10x10_uniform_and_deterministic(setup256, ceiling, grid10, evaluate):
    t = Target.from_traps(grid10)
    r = m.run(setup256, t, budget=Budget(30), rng=Rng(6))
    e, u, _ = evaluate(r.phi, grid10)
    assert e > 0.9 * ceiling and u > 0.95
    assert np.array_equal(r.phi, m.run(setup256, t, budget=Budget(30), rng=Rng(6)).phi)
