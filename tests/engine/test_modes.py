from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import Setup, slm_grid
from pipeline.model.holo.core.modes import grating_phase, lens_phase, vortex_phase

S = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=16, pitch_m=12.5e-6, pad=2)


def in_range(p):
    return p.dtype == np.float64 and p.shape == (16, 16) and p.min() >= 0 and p.max() < 2 * math.pi


def test_ranges():
    assert in_range(vortex_phase(S, 3)) and in_range(lens_phase(S, 1e-3)) and in_range(grating_phase(S, 1e-4, -2e-4))


def test_vortex_winding():
    p = vortex_phase(S, 2)
    x, y = slm_grid(S)
    assert np.allclose(np.exp(1j * p), np.exp(2j * np.arctan2(y, x)))
    assert np.allclose(np.exp(1j * vortex_phase(S, 0)), 1.0)
    shifted = vortex_phase(S, 1, centre=(S.pitch_m * 0.5, 0.0))
    assert not np.allclose(shifted, vortex_phase(S, 1))


def test_lens_and_grating_formulas():
    x, y = slm_grid(S)
    z = 2e-4
    assert np.allclose(np.exp(1j * lens_phase(S, z)), np.exp(1j * math.pi * z / (S.wavelength_m * S.focal_m**2) * (x**2 + y**2)))
    g = grating_phase(S, 3e-5, -1e-5)
    assert np.allclose(np.exp(1j * g), np.exp(2j * math.pi / (S.wavelength_m * S.focal_m) * (x * 3e-5 + y * -1e-5)))
    assert np.allclose(np.exp(1j * lens_phase(S, 0.0)), 1.0)


def test_bad_inputs():
    with pytest.raises(ValueError):
        vortex_phase(S, 1.5)
    with pytest.raises(ValueError):
        vortex_phase(S, 1, centre=(math.nan, 0.0))
    with pytest.raises(ValueError):
        lens_phase(S, math.inf)
    with pytest.raises(ValueError):
        grating_phase(S, math.nan, 0.0)
