"""M10 conjugate-gradient minimization (Harte et al. 2014): acceptance of the SDD ladder row and the invariants.

Acceptance: the analytic gradient matches finite differences (relative error at most 1e-5); a square lattice below 1
percent error. The lattice is 4 x 4 flat-top spots on the 128 x 128 focal grid (64 pixel SLM padded 2).
"""
from __future__ import annotations

import numpy as np
import pytest
from e3_helpers import (
    bin_grid,
    check_finite_difference, disc_target, lattice_target, make_setup, ring_target, signal_error,
)

from pipeline.model.holo.core.forward import fft_focal_field, point_trap_fields
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.optim import _common as C
from pipeline.model.holo.methods.optim import m10_cg as M10


def test_spec():
    assert M10.SPEC.id == "M10" and set(M10.SPEC.targets) == {"traps", "field"} and M10.SPEC.lane in ("live", "both")


@pytest.mark.parametrize("t", [2, 4])
def test_analytic_gradient_matches_finite_differences_on_a_shaped_target(t):
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, guard=2.0)
    cost = C.FieldCost(s, amp, mask, t=t, efficiency=0.4)
    phi = Rng(5).phases(256).reshape(16, 16)
    err = check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(1), n_dirs=6)
    assert err <= 1e-5


@pytest.mark.parametrize("t", [2, 4])
def test_analytic_gradient_matches_finite_differences_on_traps(t):
    s = make_setup(16)
    traps = bin_grid(s, 3, 3, 12)
    cost = C.TrapCost(s, traps, t=t, efficiency=0.8)
    phi = Rng(6).phases(256).reshape(16, 16)
    assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(2), n_dirs=6) <= 1e-5


def test_cost_decreases_monotonically_and_history_is_complete():
    s = make_setup(32)
    amp, mask = disc_target(s, 14.0, guard=3.0)
    res = M10.run(s, Target.from_field(amp, mask), budget=Budget(40), rng=Rng(1))
    for tt in (4, 2):                       # the two stages are different costs: monotone inside each
        c = [h["cost"] for h in res.history if h["t"] == tt]
        assert len(c) >= 2 and all(b <= a * (1 + 1e-9) for a, b in zip(c, c[1:]))
    assert res.history[-1]["error"] < res.history[0]["error"]
    assert res.fields.shape == (64, 64)


def test_sequential_powers_run_t4_then_t2():
    s = make_setup(32)
    amp, mask = ring_target(s, 14.0, 8.0)
    res = M10.run(s, Target.from_field(amp, mask), budget=Budget(30), rng=Rng(1), t=(4, 2))
    assert [h["t"] for h in res.history[:1]] == [4] and res.history[-1]["t"] == 2


def test_trap_target_improves_uniformity_over_a_random_start():
    s = make_setup(64)
    traps = bin_grid(s, 4, 4, 8)
    res = M10.run(s, Target.from_traps(traps), budget=Budget(60), rng=Rng(2), t=2)
    h0, h1 = res.history[0], res.history[-1]
    assert h1["rel_std"] < h0["rel_std"]
    assert np.allclose(point_trap_fields(res.phi, s, traps), res.fields, atol=1e-10)


def test_bad_target_shape_raises():
    s = make_setup(16)
    with pytest.raises(ValueError, match="32"):
        M10.run(s, Target.from_field(np.ones((16, 16)), np.ones((16, 16), dtype=bool)), budget=Budget(1), rng=Rng(1))


def test_deterministic_for_a_seed():
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, guard=2.0)
    a = M10.run(s, Target.from_field(amp, mask), budget=Budget(8), rng=Rng(4))
    b = M10.run(s, Target.from_field(amp, mask), budget=Budget(8), rng=Rng(4))
    assert np.array_equal(a.phi, b.phi)


def test_acceptance_square_lattice_below_one_percent_error():
    s = make_setup(64)
    amp, mask = lattice_target(s, 4, 16.0, 3.0)
    errs = []
    for seed in (1, 2):
        res = M10.run(s, Target.from_field(amp, mask), budget=Budget(M10.DEFAULT_LATTICE_ITERATIONS), rng=Rng(seed),
                    t=2)
        err, eff = signal_error(fft_focal_field(res.phi, s), amp, mask)
        errs.append(err)
    assert max(errs) < 0.01, errs
