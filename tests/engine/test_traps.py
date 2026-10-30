from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import Setup, focal_bin_m, half_field_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import (
    OutOfFieldError, Trap, TrapSet, check_in_field, hex_lattice, lattice_3d, random_min_spacing, ring,
    snap_to_bins, square_grid,
)

S = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)


def test_square_grid():
    t = square_grid(3, 2, 4.0)
    assert len(t) == 6
    assert [tr.id for tr in t.traps] == list(range(6))
    assert t.x_m.mean() == pytest.approx(0, abs=1e-18) and t.y_m.mean() == pytest.approx(0, abs=1e-18)
    assert np.ptp(t.x_m) == pytest.approx(8e-6)
    assert np.ptp(t.y_m) == pytest.approx(4e-6)
    assert np.all(t.weight == 1.0) and np.all(t.z_m == 0) and np.all(t.charge == 0)


def test_hex_lattice_spacing():
    t = hex_lattice(7, 5.0)
    assert len(t) == 7
    d = np.hypot(t.x_m[:, None] - t.x_m[None], t.y_m[:, None] - t.y_m[None])
    np.fill_diagonal(d, np.inf)
    assert d.min() == pytest.approx(5e-6)
    r = np.hypot(t.x_m, t.y_m)
    assert np.sum(np.isclose(r, 5e-6)) == 6


def test_ring():
    t = ring(8, 10.0)
    assert np.allclose(np.hypot(t.x_m, t.y_m), 10e-6)
    assert len(t) == 8


def test_random_min_spacing_and_determinism():
    a = random_min_spacing(30, 60.0, 4.0, Rng(1))
    b = random_min_spacing(30, 60.0, 4.0, Rng(1))
    c = random_min_spacing(30, 60.0, 4.0, Rng(2))
    assert np.array_equal(a.x_m, b.x_m) and not np.array_equal(a.x_m, c.x_m)
    d = np.hypot(a.x_m[:, None] - a.x_m[None], a.y_m[:, None] - a.y_m[None])
    np.fill_diagonal(d, np.inf)
    assert d.min() >= 4e-6 - 1e-18
    assert np.all(np.abs(a.x_m) <= 30e-6)


def test_random_min_spacing_impossible():
    with pytest.raises(ValueError):
        random_min_spacing(50, 10.0, 5.0, Rng(1))


def test_lattice_3d():
    t = lattice_3d(2, 2, 3, 4.0, 6.0)
    assert len(t) == 12
    assert sorted(set(np.round(t.z_m * 1e6, 6))) == [-6.0, 0.0, 6.0]


def test_validation():
    with pytest.raises(ValueError, match="at least one"):
        TrapSet(())
    with pytest.raises(ValueError, match="duplicate"):
        TrapSet((Trap(1, 0, 0), Trap(1, 1e-6, 0)))
    with pytest.raises(ValueError, match="finite"):
        TrapSet((Trap(1, math.nan, 0),))
    with pytest.raises(ValueError, match="finite"):
        TrapSet((Trap(1, 0, math.inf),))
    with pytest.raises(ValueError, match="weight"):
        TrapSet((Trap(1, 0, 0, weight=0.0),))


def test_out_of_field_names_trap_and_bound():
    half = half_field_m(S)
    t = TrapSet((Trap(0, 0, 0), Trap(7, half * 1.01, 0)))
    with pytest.raises(OutOfFieldError) as e:
        check_in_field(S, t)
    assert "7" in str(e.value) and "bound" in str(e.value)
    assert e.value.trap_id == 7 and e.value.bound_m == pytest.approx(half)
    check_in_field(S, TrapSet((Trap(0, half * 0.99, -half * 0.99),)))
    assert issubclass(OutOfFieldError, ValueError)


def test_snap_to_bins():
    b = focal_bin_m(S)
    t = TrapSet((Trap(0, 3.4 * b, -2.6 * b, z_m=1e-6),))
    s = snap_to_bins(S, t)
    assert s.x_m[0] == pytest.approx(3 * b) and s.y_m[0] == pytest.approx(-3 * b)
    assert s.z_m[0] == 1e-6
