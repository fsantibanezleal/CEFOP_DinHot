"""M13 device-aware CG with pixel crosstalk (Schroff et al. 2023).

Acceptance: on the crosstalk device (sigma 1.24 per pixel, q 1.80, 3x3 upsampling), lower error than M10 without the
model on a large disc. Both methods get the same start, the same budget and the same cost (t = 2); the error is
measured on the device's focal field (``core.device.device_focal_field``). The disc has a 24 bin radius on the 128 x 128
focal grid (64 pixel SLM padded 2). Seeds: 1 (benchmark: 20); 100 iterations each.
"""
from __future__ import annotations

import numpy as np
import pytest
from e3_helpers import check_finite_difference, disc_target, make_setup, signal_error

from pipeline.model.holo.core.device import Device, device_focal_field
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.optim import _common as C
from pipeline.model.holo.methods.optim import m10_cg as M10
from pipeline.model.holo.methods.optim import m13_crosstalk_cg as M13

DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)
ITERATIONS = 100


def test_spec_and_the_paper_device():
    assert M13.SPEC.id == "M13" and "field" in M13.SPEC.targets
    assert M13.SCHROFF_DEVICE.crosstalk == (1.24, 1.80) and M13.SCHROFF_DEVICE.upsample == 3


@pytest.mark.parametrize("t", [2, 4])
def test_gradient_through_the_crosstalk_operator_matches_finite_differences(t):
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, 2.0)
    cost = C.FieldCost(s, amp, mask, DEVICE, t=t, efficiency=0.4)
    phi = Rng(5).phases(256).reshape(16, 16)
    assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(t), n_dirs=6) <= 1e-5


def test_without_a_device_m13_is_m10():
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, 2.0)
    a = M13.run(s, Target.from_field(amp, mask), budget=Budget(10), rng=Rng(2), t=2)
    b = M10.run(s, Target.from_field(amp, mask), budget=Budget(10), rng=Rng(2), t=2)
    assert np.array_equal(a.phi, b.phi)


def test_vortex_trap_on_a_device_is_refused():
    s = make_setup(16)
    traps = TrapSet([Trap(0, 3.3e-5, 0.0, 0.0, charge=1)])
    with pytest.raises(ValueError, match="z = 0"):
        M13.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(1), rng=Rng(1))


def test_crosstalk_run_decreases_the_device_cost_and_records_history():
    s = make_setup(32)
    amp, mask = disc_target(s, 14.0, 3.0)
    res = M13.run(s, Target.from_field(amp, mask), device=DEVICE, budget=Budget(30), rng=Rng(1), t=2)
    c = [h["cost"] for h in res.history]
    assert all(b <= a * (1 + 1e-9) for a, b in zip(c, c[1:])) and c[-1] < c[0]
    assert np.allclose(res.fields, device_focal_field(res.phi, s, DEVICE, None), atol=1e-9)
    assert res.meta["device_aware"]


def test_deterministic_for_a_seed():
    s = make_setup(16)
    amp, mask = disc_target(s, 8.0, 2.0)
    a = M13.run(s, Target.from_field(amp, mask), device=DEVICE, budget=Budget(6), rng=Rng(4), t=2)
    b = M13.run(s, Target.from_field(amp, mask), device=DEVICE, budget=Budget(6), rng=Rng(4), t=2)
    assert np.array_equal(a.phi, b.phi)


def test_acceptance_lower_error_than_m10_on_the_crosstalk_device_for_a_large_disc():
    s = make_setup(64)
    amp, mask = disc_target(s, 24.0, 3.0)
    for seed in (1,):
        out = {}
        for name, mod, dev in (("m10", M10, None), ("m13", M13, DEVICE)):
            res = mod.run(s, Target.from_field(amp, mask), device=dev, budget=Budget(ITERATIONS), rng=Rng(seed), t=2)
            out[name] = signal_error(device_focal_field(res.phi, s, DEVICE, None), amp, mask)
        assert out["m13"][0] < out["m10"][0], (seed, out)
