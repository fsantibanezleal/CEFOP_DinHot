from __future__ import annotations

import math
import tracemalloc

import numpy as np
import pytest

from pipeline.model.holo.core.forward import (
    angular_spectrum, axial_cut, fft_focal_field, fft_inverse, point_trap_backproject, point_trap_fields,
    point_trap_projection, slm_field, trap_fields_from_fft,
)
from pipeline.model.holo.core.geometry import (
    Setup, focal_bin_m, half_field_m, input_amplitude, slm_grid, wrap_phase,
)
from pipeline.model.holo.core.modes import grating_phase, lens_phase
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import OutOfFieldError, Trap, TrapSet


def make(n=32, pad=2, **kw):
    base = dict(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n, pitch_m=12.5e-6, pad=pad)
    base.update(kw)
    return Setup(**base)


def bin_traps(setup, bins, **kw):
    b = focal_bin_m(setup)
    return TrapSet(Trap(i, kx * b, ky * b, **kw) for i, (kx, ky) in enumerate(bins))


def brute_force(phi, setup, traps):
    """Direct evaluation of the point-trap formula of algorithms D1.0, one trap at a time, no separability."""
    x, y = slm_grid(setup)
    a = input_amplitude(setup)
    lam, f = setup.wavelength_m, setup.focal_m
    out = []
    for t in traps:
        d = (math.pi * t.z_m / (lam * f**2)) * (x**2 + y**2) + (2 * math.pi / (lam * f)) * (x * t.x_m + y * t.y_m)
        d = d + t.charge * np.arctan2(y, x)
        out.append(np.sum(a * np.exp(1j * (phi - d))) / setup.n_pix**2)
    return np.array(out)


@pytest.mark.parametrize("n,pad", [(32, 2), (32, 1), (64, 3)])
def test_fft_and_point_trap_agree_on_bins(n, pad):
    s = make(n, pad)
    phi = Rng(1).phases(n * n).reshape(n, n)
    bins = [(0, 0), (3, -2), (-5, 4), (7, 7), (-8, -3), (1, 0)]
    tr = bin_traps(s, bins)
    v_pt = point_trap_fields(phi, s, tr)
    v_fft = trap_fields_from_fft(fft_focal_field(phi, s), s, tr)
    assert np.max(np.abs(v_pt - v_fft)) / np.max(np.abs(v_pt)) < 1e-9


@pytest.mark.parametrize("n", [256, 512])
def test_agreement_on_real_grids(n):
    s = make(n, 2)
    phi = Rng(2).phases(n * n).reshape(n, n)
    tr = bin_traps(s, [(0, 0), (10, -20), (-33, 7), (60, 41)])
    v_pt = point_trap_fields(phi, s, tr)
    v_fft = trap_fields_from_fft(fft_focal_field(phi, s), s, tr)
    assert np.max(np.abs(v_pt - v_fft)) / np.max(np.abs(v_pt)) < 1e-9


def test_point_trap_matches_brute_force_with_z_and_vortex():
    s = make(24, 2)
    phi = Rng(3).phases(24 * 24).reshape(24, 24)
    b = focal_bin_m(s)
    tr = TrapSet((
        Trap(0, 2.3 * b, -1.1 * b, z_m=30e-6),
        Trap(1, -4 * b, 3 * b, z_m=-20e-6, charge=3),   # dense (vortex) path
        Trap(2, 0.0, 0.0, charge=-2),
        Trap(3, 5.5 * b, 5.5 * b),                      # separable path
    ))
    assert np.allclose(point_trap_fields(phi, s, tr), brute_force(phi, s, tr), rtol=0, atol=1e-12)


def test_chunking_does_not_change_result():
    s = make(32, 2)
    phi = Rng(4).phases(32 * 32).reshape(32, 32)
    tr = bin_traps(s, [(i - 10, (3 * i) % 9 - 4) for i in range(20)])
    a = point_trap_fields(phi, s, tr, chunk=3)
    b = point_trap_fields(phi, s, tr, chunk=1000)
    assert np.allclose(a, b, rtol=0, atol=1e-13)


def test_single_trap_hologram_has_unit_amplitude():
    s = make(32, 2, beam="flat")
    b = focal_bin_m(s)
    t = TrapSet((Trap(0, 3 * b, -2 * b, z_m=50e-6),))
    phi = wrap_phase(lens_phase(s, 50e-6) + grating_phase(s, 3 * b, -2 * b))
    assert abs(point_trap_fields(phi, s, t)[0]) == pytest.approx(1.0, abs=1e-12)


def test_backproject_is_adjoint_of_projection():
    s = make(16, 2)
    b = focal_bin_m(s)
    tr = TrapSet((Trap(0, 1.5 * b, 2 * b, z_m=1e-5), Trap(1, -3 * b, 1 * b, charge=2), Trap(2, 0, -2.2 * b)))
    rng = Rng(5)
    f = rng.normal_array(256).reshape(16, 16) + 1j * rng.normal_array(256).reshape(16, 16)
    c = rng.normal_array(3) + 1j * rng.normal_array(3)
    lhs = np.sum(c * np.conj(point_trap_projection(f, s, tr)))
    rhs = np.vdot(f, point_trap_backproject(c, s, tr)) / s.n_pix**2
    assert lhs == pytest.approx(rhs, rel=1e-12)


def test_parseval_fft():
    s = make(64, 2)
    phi = Rng(6).phases(64 * 64).reshape(64, 64)
    e = fft_focal_field(phi, s)
    assert e.shape == (128, 128)
    assert np.sum(np.abs(e) ** 2) == pytest.approx(np.sum(np.abs(slm_field(phi, s)) ** 2), rel=1e-12)
    assert np.sum(np.abs(e) ** 2) == pytest.approx(64 * 64, rel=1e-12)


def test_fft_inverse_roundtrip():
    s = make(32, 2)
    phi = Rng(7).phases(32 * 32).reshape(32, 32)
    back = fft_inverse(fft_focal_field(phi, s), s)
    assert np.allclose(back, slm_field(phi, s), atol=1e-12)


def test_out_of_field_raises_everywhere():
    s = make(32, 2)
    phi = np.zeros((32, 32))
    far = TrapSet((Trap(9, half_field_m(s) * 1.5, 0.0),))
    with pytest.raises(OutOfFieldError):
        point_trap_fields(phi, s, far)
    with pytest.raises(OutOfFieldError):
        trap_fields_from_fft(fft_focal_field(phi, s), s, far)


def test_phi_shape_and_finite_checks():
    s = make(16, 2)
    tr = bin_traps(s, [(0, 0)])
    with pytest.raises(ValueError):
        point_trap_fields(np.zeros((8, 8)), s, tr)
    bad = np.zeros((16, 16))
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        point_trap_fields(bad, s, tr)
    with pytest.raises(ValueError):
        fft_focal_field(bad, s)


def test_memory_under_one_gb_for_1024_traps_on_512():
    s = make(512, 2)
    phi = Rng(8).phases(512 * 512).reshape(512, 512)
    # 32 x 32 traps on a 2-bin pitch (inside the +-512 bin field)
    tr = bin_traps(s, [(2 * i - 31, 2 * j - 31) for i in range(32) for j in range(32)])
    assert len(tr) == 1024
    tracemalloc.start()
    try:
        v = point_trap_fields(phi, s, tr)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert v.shape == (1024,) and peak < 1e9
    # and the dense (vortex) path for a few traps stays small too
    vt = TrapSet(Trap(i, t.x_m, t.y_m, charge=1) for i, t in enumerate(list(tr)[:20]))
    tracemalloc.start()
    try:
        point_trap_fields(phi, s, vt)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 1e9


def _gaussian_focal_field(s, w0):
    m = s.n_fft
    c = (np.arange(m) - m // 2) * focal_bin_m(s)
    xx, yy = np.meshgrid(c, c)
    return np.exp(-(xx**2 + yy**2) / w0**2).astype(complex)


def test_angular_spectrum_reversible_and_power_conserving():
    s = make(32, 2, wavelength_m=0.85e-6, focal_m=0.0005)  # fine focal bin, small window
    e = _gaussian_focal_field(s, 4 * focal_bin_m(s))
    out = angular_spectrum(e, 3e-6, s)
    assert np.sum(np.abs(out) ** 2) == pytest.approx(np.sum(np.abs(e) ** 2), rel=1e-9)
    back = angular_spectrum(out, -3e-6, s)
    assert np.allclose(back, e, atol=1e-9)


def test_angular_spectrum_matches_gaussian_beam():
    s = make(64, 2, focal_m=0.002)  # bin = 0.85e-6*0.002/(128*12.5e-6) ~ 1.06e-6
    bin_m = focal_bin_m(s)
    w0 = 8 * bin_m
    lam = s.wavelength_m / s.n_imm
    zr = math.pi * w0**2 / lam
    e = _gaussian_focal_field(s, w0)
    z = zr
    out = angular_spectrum(e, z, s)
    m = s.n_fft
    w = w0 * math.sqrt(1 + (z / zr) ** 2)
    c = (np.arange(m) - m // 2) * bin_m
    xx, yy = np.meshgrid(c, c)
    expect = (w0 / w) * np.exp(-(xx**2 + yy**2) / w**2)
    assert np.max(np.abs(np.abs(out) - expect)) < 5e-3


def test_angular_spectrum_zeroes_evanescent():
    s = make(32, 1, focal_m=0.0001)  # bin ~ 0.85e-6*1e-4/(32*12.5e-6) = 0.21e-6 < lambda/2: evanescent bins exist
    e = np.zeros((32, 32), dtype=complex)
    e[0, 0] = 1.0  # highest spatial frequencies
    e[16, 16] = 1.0
    out = angular_spectrum(e, 0.0, s)
    assert np.sum(np.abs(out) ** 2) < np.sum(np.abs(e) ** 2)


def test_axial_cut_peak_follows_z_sign():
    s = make(64, 2, focal_m=0.01, beam="flat")
    z0 = 1.5e-3
    for sign in (+1, -1):
        phi = wrap_phase(lens_phase(s, sign * z0))
        inten, z, lat = axial_cut(phi, s, y_m=0.0, z_range_m=(-4e-3, 4e-3), nz=81)
        assert inten.shape == (81, s.n_fft) and z.shape == (81,) and lat.shape == (s.n_fft,)
        on_axis = inten[:, s.n_fft // 2]
        zpk = z[np.argmax(on_axis)]
        assert sign * zpk > 0 and abs(zpk - sign * z0) < 0.3 * z0
    # yz cut of the same hologram is the same by symmetry
    ixz, _, _ = axial_cut(phi, s, y_m=0.0, z_range_m=(-4e-3, 4e-3), nz=9)
    iyz, _, _ = axial_cut(phi, s, x_m=0.0, z_range_m=(-4e-3, 4e-3), nz=9)
    assert np.allclose(ixz, iyz, rtol=1e-8, atol=1e-12)


def test_axial_cut_matches_full_propagation():
    s = make(32, 2, focal_m=0.01)
    phi = Rng(11).phases(32 * 32).reshape(32, 32)
    zs = (-1e-3, 1e-3)
    inten, z, lat = axial_cut(phi, s, y_m=0.0, z_range_m=zs, nz=3)
    e = fft_focal_field(phi, s)
    full = angular_spectrum(e, z[2], s)
    row = np.abs(full[s.n_fft // 2]) ** 2 * s.pad**2 / s.n_pix**2
    assert np.allclose(inten[2], row, rtol=1e-8, atol=1e-12)


def test_axial_cut_argument_errors():
    s = make(16, 2)
    phi = np.zeros((16, 16))
    with pytest.raises(ValueError):
        axial_cut(phi, s, z_range_m=(0, 1e-3), nz=3)
    with pytest.raises(ValueError):
        axial_cut(phi, s, x_m=0.0, y_m=0.0, z_range_m=(0, 1e-3), nz=3)
    with pytest.raises(ValueError):
        axial_cut(phi, s, y_m=0.0, z_range_m=(0, 1e-3), nz=0)
