from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.forward import fft_focal_field, point_trap_fields, trap_fields_from_fft
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, wrap_phase
from pipeline.model.holo.core.metrics import (
    efficiency, ghost_fraction, power_budget, rel_std, trap_intensities, uniformity, zero_order_fraction,
)
from pipeline.model.holo.core.modes import grating_phase
from pipeline.model.holo.core.traps import Trap, TrapSet


def make(n=32, pad=2, **kw):
    base = dict(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n, pitch_m=12.5e-6, pad=pad,
                beam="flat")
    base.update(kw)
    return Setup(**base)


def test_definitions():
    i = np.array([0.2, 0.3, 0.25])
    assert efficiency(i) == pytest.approx(0.75)
    assert uniformity(i) == pytest.approx(1 - (0.3 - 0.2) / (0.3 + 0.2))
    assert rel_std(i) == pytest.approx(100 * np.std(i) / np.mean(i))
    assert uniformity(np.full(5, 0.1)) == 1.0 and rel_std(np.full(5, 0.1)) == 0.0


def test_trap_intensities_with_weights():
    v = np.array([1.0 + 0j, 1j * 2.0])
    assert trap_intensities(v).tolist() == [1.0, 4.0]
    assert trap_intensities(v, np.array([1.0, 4.0])).tolist() == [1.0, 1.0]


def test_error_cases():
    with pytest.raises(ValueError):
        efficiency(np.array([]))
    with pytest.raises(ValueError):
        uniformity(np.array([0.0, 0.0]))
    with pytest.raises(ValueError):
        rel_std(np.array([0.0, 0.0]))
    with pytest.raises(ValueError):
        efficiency(np.array([1.0, np.nan]))
    with pytest.raises(ValueError):
        trap_intensities(np.array([1.0 + 0j]), np.array([0.0]))
    with pytest.raises(ValueError):
        trap_intensities(np.array([1.0 + 0j, 1.0]), np.array([1.0]))


def test_zero_order_flat_phase_is_everything():
    s = make()
    e = fft_focal_field(np.zeros((32, 32)), s)
    assert zero_order_fraction(e, s) == pytest.approx(1.0, abs=1e-12)


def test_power_budget_sums_to_one_and_finds_trap():
    s = make(32, 2)
    b = focal_bin_m(s)
    tr = TrapSet((Trap(0, 6 * b, -4 * b),))
    phi = wrap_phase(grating_phase(s, 6 * b, -4 * b))
    e = fft_focal_field(phi, s)
    pb = power_budget(e, s, tr, radius_bins=4)
    assert pb["traps"] + pb["zero_order"] + pb["ghosts"] + pb["remainder"] == pytest.approx(1.0, abs=1e-12)
    assert pb["traps"] > 0.9 and pb["zero_order"] < 0.01
    assert pb["remainder"] == pytest.approx(0.0, abs=1e-12)
    assert ghost_fraction(e, s, tr, 4) == pytest.approx(pb["ghosts"])
    # trap light is also the point-trap efficiency within the same order
    v = point_trap_fields(phi, s, tr)
    assert efficiency(trap_intensities(v)) == pytest.approx(1.0, abs=1e-9)
    assert efficiency(trap_intensities(trap_fields_from_fft(e, s, tr))) == pytest.approx(1.0, abs=1e-9)


def test_power_budget_zero_order_visible():
    s = make(32, 2)
    b = focal_bin_m(s)
    tr = TrapSet((Trap(0, 8 * b, 0.0),))
    # half of the pixels flat (zero order), half a grating: both orders carry power
    phi = grating_phase(s, 8 * b, 0.0)
    phi[:, :16] = 0.0
    pb = power_budget(fft_focal_field(phi, s), s, tr, radius_bins=4)
    assert pb["zero_order"] > 0.2 and pb["traps"] > 0.2


def test_budget_radius_validation():
    s = make()
    tr = TrapSet((Trap(0, 0.0, 0.0),))
    e = fft_focal_field(np.zeros((32, 32)), s)
    with pytest.raises(ValueError):
        power_budget(e, s, tr, radius_bins=0)
    with pytest.raises(ValueError):
        power_budget(e[:10, :10], s, tr, radius_bins=2)
    assert math.isfinite(ghost_fraction(e, s, tr, 2))
