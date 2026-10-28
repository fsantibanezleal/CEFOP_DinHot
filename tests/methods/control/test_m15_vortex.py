"""M15: Laguerre-Gaussian vortex traps (SDD ladder: the ring phase winds by 2 pi l with an error under 0.1 rad)."""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet, square_grid
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.control import m15_vortex as m


def vortex_set(setup, charges):
    b = focal_bin_m(setup)
    return TrapSet(Trap(i, (i - (len(charges) - 1) / 2) * 24 * b, 0.0, 0.0, 1.0, int(c)) for i, c in enumerate(charges))


@pytest.mark.parametrize("charge", [1, 2, 3, -2])
def test_isolated_vortex_ring_phase_within_0_1_rad(setup256, charge):
    """SDD: the ring phase winds by 2 pi l with an error under 0.1 rad (maximum deviation from the l theta line)."""
    tr = TrapSet([Trap(0, 0.0, 0.0, 0.0, 1.0, charge)])
    for seed in (1, 2):
        r = m.run(setup256, Target.from_traps(tr), budget=Budget(5), rng=Rng(seed))
        prof = m.ring_phase_profile(r.phi, setup256, tr.traps[0])
        assert abs(prof["winding"] - 2 * math.pi * charge) < 1e-6, prof          # signed winding 2 pi l
        assert prof["max_error"] < 0.1, (seed, charge, prof)


@pytest.mark.parametrize("seed", [1, 2])
def test_vortex_array_ring_phase(setup256, seed):
    """Four vortices (l = 1, 2, 3, -2) in one weighted-GS hologram: exact integer winding for each; rms error under 0.1 rad.

    The maximum deviation of an array member reaches 0.12 rad (l = 2, off axis) because the hologram is shared; the rms
    stays under 0.1 and the maximum under 0.2.
    """
    charges = [1, 2, 3, -2]
    tr = vortex_set(setup256, charges)
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(20), rng=Rng(seed))
    for t, l in zip(tr, charges):
        prof = m.ring_phase_profile(r.phi, setup256, t)
        assert abs(prof["winding"] - 2 * math.pi * l) < 1e-6, (l, prof)
        assert prof["rms_error"] < 0.1 and prof["max_error"] < 0.2, (seed, l, prof)


def test_winding_sign_convention_is_the_same_for_every_charge(setup256):
    tr = vortex_set(setup256, [1, 2, -1])
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(10), rng=Rng(3))
    signs = [m.ring_phase_profile(r.phi, setup256, t)["sign"] * np.sign(t.charge) for t in tr]
    assert len(set(signs)) == 1


def test_charge_keyword_overrides_and_equalises_power(setup256):
    base = square_grid(3, 3, 24 * focal_bin_m(setup256) * 1e6)
    r = m.run(setup256, Target.from_traps(base), budget=Budget(30), rng=Rng(1), charge=2)
    assert all(t.charge == 2 for t in r.meta["traps"])
    assert r.history[-1]["uniformity"] > 0.9


def test_no_vortex_is_rejected_and_deterministic(setup256):
    plain = square_grid(2, 2, 24 * focal_bin_m(setup256) * 1e6)
    with pytest.raises(ValueError, match="charge"):
        m.run(setup256, Target.from_traps(plain), budget=Budget(1), rng=Rng(1))
    tr = vortex_set(setup256, [1, 2])
    a = m.run(setup256, Target.from_traps(tr), budget=Budget(3), rng=Rng(4)).phi
    assert np.array_equal(a, m.run(setup256, Target.from_traps(tr), budget=Budget(3), rng=Rng(4)).phi)
    n = setup256.n_fft
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(np.ones((n, n)), np.ones((n, n), bool)), budget=Budget(1), rng=Rng(1))


def test_charged_trap_has_a_dark_centre(setup256):
    """The intensity at the centre of an l = 2 trap is far below its ring maximum (the vortex signature)."""
    from pipeline.model.holo.core.forward import point_trap_fields
    tr = vortex_set(setup256, [2])
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(20), rng=Rng(1))
    centre = replace(tr.traps[0], charge=0)
    c = abs(point_trap_fields(r.phi, setup256, TrapSet([centre]))[0]) ** 2
    prof = m.ring_phase_profile(r.phi, setup256, tr.traps[0])
    assert c < 0.05 * prof["ring_intensity"]
