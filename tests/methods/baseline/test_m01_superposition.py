"""M01: superposition of prisms and lenses (SDD ladder; Di Leonardo et al. 2007 Table 1: e/u = 0.29/0.01)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods import baseline  # noqa: F401
from pipeline.model.holo.methods.baseline import m01_superposition as m


def test_acceptance_10x10_matches_published_trend(setup256, grid10, evaluate):
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(1))
    e, u, _ = evaluate(r.phi, grid10)
    assert abs(e - 0.29) <= 0.10, e          # published 0.29 (768 x 768); analytic, no seed spread
    assert u <= 0.05, u                      # published 0.01: a near-zero uniformity is the method's signature
    assert len(r.history) == 1 and r.history[0]["iteration"] == 1


def test_deterministic_and_independent_of_rng(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(1), rng=Rng(1)).phi
    b = m.run(setup256, t, budget=Budget(1), rng=Rng(99)).phi
    assert np.array_equal(a, b)


def test_single_trap_is_a_grating_with_unit_field(setup256, grid10):
    from pipeline.model.holo.core.traps import Trap, TrapSet
    from pipeline.model.holo.core.forward import point_trap_fields
    from pipeline.model.holo.core.geometry import focal_bin_m
    tr = TrapSet([Trap(0, 5 * focal_bin_m(setup256), 3 * focal_bin_m(setup256))])
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(1), rng=Rng(1))
    v = point_trap_fields(r.phi, setup256, tr)
    assert abs(abs(v[0]) ** 2 - 0.75) < 0.2  # Gaussian beam: |V|^2 below 1 by the sampled envelope, but one trap takes all


def test_field_target_raises_naming_supported_kinds(setup256):
    amp = np.ones((setup256.n_fft, setup256.n_fft))
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(amp, amp > 0), budget=Budget(1), rng=Rng(1))


def test_spec():
    assert m.SPEC.id == "M01" and m.SPEC.targets == ("traps",)
