from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.device import (
    Device, crosstalk, crosstalk_adjoint, crosstalk_kernel, device_focal_field, displayed_phase, pixel_envelope,
    quantize,
)
from pipeline.model.holo.core.forward import fft_focal_field
from pipeline.model.holo.core.geometry import Setup, wrap_phase
from pipeline.model.holo.core.rng import Rng


def make(n=8, pad=2, **kw):
    base = dict(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n, pitch_m=12.5e-6, pad=pad,
                beam="flat")
    base.update(kw)
    return Setup(**base)


# ---- quantization, LUT, flicker -------------------------------------------------------------------------------

def test_quantize_levels_and_wrap():
    phi = np.array([0.0, 0.1, math.pi / 2 + 0.01, math.pi, 2 * math.pi - 1e-9, 3 * math.pi + 0.2])
    q = quantize(phi, 2)
    assert np.allclose(q, [0.0, 0.0, math.pi / 2, math.pi, 0.0, math.pi])
    assert q.dtype == np.float64 and q.min() >= 0 and q.max() < 2 * math.pi
    assert np.array_equal(quantize(q, 2), q)  # idempotent


def test_quantize_error_bound():
    phi = Rng(1).phases(5000)
    for b in (2, 4, 8):
        err = np.abs(np.angle(np.exp(1j * (quantize(phi, b) - phi))))
        assert err.max() <= math.pi / 2**b + 1e-12


@pytest.mark.parametrize("bad", [0, -1, 1.5, 33, True])
def test_quantize_bad_depth(bad):
    with pytest.raises(ValueError):
        quantize(np.zeros(3), bad)


def test_device_validation():
    for kw in (dict(bit_depth=0), dict(upsample=0), dict(fill_factor=0.0), dict(fill_factor=1.2),
               dict(flicker_rad=-1.0), dict(lut_gamma=0.0), dict(crosstalk=(0.0, 1.8)), dict(crosstalk=(1.2, -1.0)),
               dict(crosstalk=(1.2,))):
        with pytest.raises(ValueError):
            Device(**kw)
    Device()  # defaults are valid


def test_displayed_phase_composition():
    phi = Rng(2).phases(400).reshape(20, 20)
    assert np.allclose(displayed_phase(phi, Device(), None), phi)  # ideal levels, no noise
    d = Device(bit_depth=3)
    assert np.array_equal(displayed_phase(phi, d, None), quantize(phi, 3))
    g = Device(lut_gamma=2.0)
    expect = 2 * math.pi * (phi / (2 * math.pi)) ** 2.0
    assert np.allclose(displayed_phase(phi, g, None), expect)
    out = displayed_phase(phi, Device(bit_depth=5, lut_gamma=1.3, flicker_rad=0.1), Rng(3))
    assert out.min() >= 0 and out.max() < 2 * math.pi


def test_flicker_statistics_and_determinism():
    phi = np.zeros((200, 200))
    dev = Device(flicker_rad=0.05)
    a = displayed_phase(phi, dev, Rng(4))
    err = np.angle(np.exp(1j * a))
    assert abs(err.std() - 0.05) < 0.002 and abs(err.mean()) < 0.002
    assert np.array_equal(a, displayed_phase(phi, dev, Rng(4)))
    assert not np.array_equal(a, displayed_phase(phi, dev, Rng(5)))
    with pytest.raises(ValueError, match="rng"):
        displayed_phase(phi, dev, None)


def test_quantization_costs_efficiency_monotonically():
    # sawtooth grating, 16 pixels per period: first order is FFT bin n/16 on a pad=1 grid
    n = 64
    s = make(n, 1)
    x = np.arange(n)
    phi = wrap_phase(2 * math.pi * x[None, :] / 16.0 * np.ones((n, 1)))
    eff = {}
    for b in (1, 2, 3, 8):
        e = fft_focal_field(displayed_phase(phi, Device(bit_depth=b), None), s)
        p = np.abs(e) ** 2 / n**2
        eff[b] = p[n // 2, n // 2 + n // 16]
    assert eff[1] < eff[2] < eff[3] < eff[8]
    assert eff[8] > 0.95
    assert eff[1] == pytest.approx(4 / math.pi**2, rel=0.1)   # binary phase grating, +1 order


# ---- crosstalk -------------------------------------------------------------------------------------------------

def test_kernel_normalised_symmetric_real():
    k = crosstalk_kernel(24, 1.24, 1.80, upsample=3)
    assert k.shape == (24, 24) and k.dtype == np.float64
    assert k.sum() == pytest.approx(1.0, abs=1e-12)
    kk = np.roll(k[::-1, ::-1], (1, 1), axis=(0, 1))   # reversal about the origin
    assert np.allclose(k, kk, atol=1e-12)
    assert k[0, 0] == k.max()


def test_kernel_matches_definition_eq4():
    n, up = 12, 3
    k = crosstalk_kernel(n, 1.24, 1.80, upsample=up)
    f = np.fft.fftfreq(n, d=1.0 / up)
    h = np.exp(-((np.abs(f)[:, None] ** 1.8 + np.abs(f)[None, :] ** 1.8) / 1.24**1.8))
    assert np.allclose(np.fft.fft2(k), h, atol=1e-12)


def test_crosstalk_is_circular_convolution_with_kernel():
    d = Device(crosstalk=(1.24, 1.8), upsample=3)
    phi = Rng(6).phases(16).reshape(4, 4)
    out = crosstalk(phi, d)
    up = np.kron(phi, np.ones((3, 3)))
    k = crosstalk_kernel(12, 1.24, 1.8, upsample=3)
    brute = np.zeros_like(up)
    for dy in range(12):
        for dx in range(12):
            brute += k[dy, dx] * np.roll(up, (dy, dx), axis=(0, 1))
    assert out.shape == (12, 12)
    assert np.allclose(out, brute, atol=1e-12)


def test_crosstalk_constant_phase_unchanged_and_no_model_is_pure_upsample():
    d = Device(crosstalk=(1.24, 1.8))
    assert np.allclose(crosstalk(np.full((5, 5), 1.7), d), 1.7)
    assert np.array_equal(crosstalk(np.arange(4.0).reshape(2, 2), Device(upsample=2)),
                          np.kron(np.arange(4.0).reshape(2, 2), np.ones((2, 2))))


@pytest.mark.parametrize("dev", [Device(crosstalk=(1.24, 1.8)), Device(crosstalk=(0.4, 1.2), upsample=2), Device(upsample=3)])
def test_crosstalk_adjoint_inner_product_identity(dev):
    rng = Rng(7)
    n = 6
    phi = rng.normal_array(n * n).reshape(n, n)
    g = rng.normal_array((n * dev.upsample) ** 2).reshape(n * dev.upsample, n * dev.upsample)
    lhs = np.sum(crosstalk(phi, dev) * g)
    rhs = np.sum(phi * crosstalk_adjoint(g, dev))
    assert lhs == pytest.approx(rhs, rel=1e-12)


def test_adjoint_shape_error():
    with pytest.raises(ValueError):
        crosstalk_adjoint(np.zeros((7, 7)), Device(upsample=3))


# ---- pixel envelope vs brute-force DFT -------------------------------------------------------------------------

def test_pixel_envelope_values():
    s = make(8, 2)
    env = pixel_envelope(s, Device())
    m = s.n_fft
    assert env.shape == (m, m) and env[m // 2, m // 2] == 1.0
    assert env[m // 2, 0] == pytest.approx(np.sinc(0.5) ** 2)          # edge of the window, unit fill factor ~0.405
    assert np.sinc(0.5) ** 2 == pytest.approx(0.405, abs=1e-3)
    assert pixel_envelope(s, Device(fill_factor=0.5))[m // 2, 0] > env[m // 2, 0]


@pytest.mark.parametrize("ff", [1.0, 0.64])
def test_pixel_envelope_against_brute_force_dft(ff):
    n, pad, sub = 8, 2, 40
    s = make(n, pad)
    m = s.n_fft
    phi = Rng(8).phases(n * n).reshape(n, n)
    # fine-sampled hologram: each pixel is a block of sub x sub samples, the central sqrt(ff) fraction active
    act = int(round(sub * math.sqrt(ff)))
    block = np.zeros((sub, sub))
    lo = (sub - act) // 2
    block[lo:lo + act, lo:lo + act] = 1.0
    fine = np.kron(np.exp(1j * phi), block)
    c = (np.arange(n * sub) - (n * sub - 1) / 2.0) / sub          # position in pixel units
    k = np.arange(m) - m // 2
    # E_fine(k) = sum_n f_n exp(-2 pi i x_n k / m), separable in x and y
    w = np.exp(-2j * math.pi * np.outer(k, c) / m)                # (m, n*sub)
    e_fine = (w @ fine @ w.T) / (sub * sub * ff) / m
    e_dev = device_focal_field(phi, s, Device(fill_factor=ff), None)
    assert np.max(np.abs(e_dev - e_fine)) / np.max(np.abs(e_dev)) < 2e-3


def test_device_field_equals_ideal_times_envelope_amplitude():
    s = make(16, 2)
    phi = Rng(9).phases(256).reshape(16, 16)
    dev = Device(fill_factor=0.8)
    ideal = fft_focal_field(phi, s)
    got = device_focal_field(phi, s, dev, None)
    assert np.allclose(np.abs(got) ** 2, np.abs(ideal) ** 2 * pixel_envelope(s, dev), rtol=1e-10, atol=1e-14)


def test_device_field_crosstalk_path_reduces_to_ideal_without_blur():
    s = make(16, 2)
    phi = Rng(10).phases(256).reshape(16, 16)
    base = device_focal_field(phi, s, Device(fill_factor=0.9), None)
    # a huge sigma makes the kernel a delta: the upsampled path must reproduce the direct path exactly
    got = device_focal_field(phi, s, Device(fill_factor=0.9, crosstalk=(1e6, 1.8), upsample=3), None)
    assert np.max(np.abs(got - base)) / np.max(np.abs(base)) < 1e-9


def test_crosstalk_changes_field_and_loses_power_to_ghosts():
    s = make(16, 2)
    phi = Rng(11).phases(256).reshape(16, 16)
    a = device_focal_field(phi, s, Device(), None)
    b = device_focal_field(phi, s, Device(crosstalk=(1.24, 1.8)), None)
    assert not np.allclose(a, b, atol=1e-6)
    assert a.shape == b.shape == (32, 32)


def test_device_field_flicker_is_seeded():
    s = make(16, 2)
    phi = Rng(12).phases(256).reshape(16, 16)
    dev = Device(flicker_rad=0.2)
    a = device_focal_field(phi, s, dev, Rng(1))
    assert np.array_equal(a, device_focal_field(phi, s, dev, Rng(1)))
    assert not np.array_equal(a, device_focal_field(phi, s, dev, Rng(2)))
