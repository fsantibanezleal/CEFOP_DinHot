from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import (
    Setup, bin_to_um, focal_bin_m, half_field_m, input_amplitude, slm_grid, um_to_bin,
)


def make(**kw):
    base = dict(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)
    base.update(kw)
    return Setup(**base)


def test_bin_and_field():
    s = make()
    assert focal_bin_m(s) == pytest.approx(0.85e-6 * 0.25 / (2 * 64 * 12.5e-6))
    assert half_field_m(s) == pytest.approx(0.85e-6 * 0.25 / (2 * 12.5e-6))
    assert half_field_m(s) == pytest.approx(focal_bin_m(s) * s.pad * s.n_pix / 2)


def test_dossier_pixel_relation():
    # physics-viz D1.2: lambda f / (2 N p) = 8.32 um for N=1024, p=12.5 um, f=250 mm, lambda ~0.85 um
    s = make(wavelength_m=0.8528e-6, n_pix=1024)
    assert focal_bin_m(s) * 1e6 == pytest.approx(8.32, abs=0.01)


def test_um_bin_roundtrip():
    s = make()
    assert bin_to_um(s, um_to_bin(s, 12.3)) == pytest.approx(12.3)


def test_grid_centred_and_pitch():
    s = make(n_pix=8)
    x, y = slm_grid(s)
    assert x.shape == y.shape == (8, 8)
    assert x[0, 1] - x[0, 0] == pytest.approx(s.pitch_m)
    assert y[1, 0] - y[0, 0] == pytest.approx(s.pitch_m)
    assert x.mean() == pytest.approx(0, abs=1e-18) and y.mean() == pytest.approx(0, abs=1e-18)


def test_amplitude_normalisation():
    for beam in ("flat", "gaussian"):
        a = input_amplitude(make(beam=beam, waist_frac=0.7))
        assert a.shape == (64, 64)
        assert np.sum(a**2) == pytest.approx(64 * 64, rel=1e-12)
    flat = input_amplitude(make(beam="flat"))
    assert np.allclose(flat, 1.0)
    g = input_amplitude(make(beam="gaussian", waist_frac=0.5))
    assert g[32, 32] > g[0, 0]


@pytest.mark.parametrize("kw", [
    dict(wavelength_m=0), dict(focal_m=-1), dict(na=0), dict(na=1.5, n_imm=1.0), dict(n_imm=0.5),
    dict(n_pix=0), dict(n_pix=3.5), dict(pitch_m=0), dict(pad=0), dict(beam="x"), dict(waist_frac=0),
    dict(wavelength_m=float("nan")), dict(focal_m=float("inf")),
])
def test_setup_validation(kw):
    with pytest.raises(ValueError):
        make(**kw)


def test_setup_frozen():
    with pytest.raises(Exception):
        make().n_pix = 3  # type: ignore[misc]


def test_um_conversion_finite():
    with pytest.raises(ValueError):
        um_to_bin(make(), math.nan)
