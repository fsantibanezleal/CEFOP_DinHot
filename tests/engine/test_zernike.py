from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import Setup, slm_grid
from pipeline.model.holo.core.zernike import (
    noll_to_nm, phase_from_coeffs, rms_waves, strehl, wavefront_waves, zernike, zernike_name,
)

DOSSIER = {1: (0, 0), 2: (1, 1), 3: (1, -1), 4: (2, 0), 5: (2, -2), 6: (2, 2), 7: (3, -1), 8: (3, 1),
           9: (3, -3), 10: (3, 3), 11: (4, 0), 12: (4, 2), 13: (4, -2), 14: (4, 4), 15: (4, -4)}


def test_noll_table_matches_dossier():
    for j, nm in DOSSIER.items():
        assert noll_to_nm(j) == nm
    assert [noll_to_nm(j) for j in range(16, 22)] == [(5, 1), (5, -1), (5, 3), (5, -3), (5, 5), (5, -5)]


@pytest.mark.parametrize("bad", [0, -3, 22, 2.5, True])
def test_noll_bad_index(bad):
    with pytest.raises(ValueError):
        noll_to_nm(bad)


def test_names():
    assert [zernike_name(j) for j in (1, 2, 3, 4)] == ["piston", "tip", "tilt", "defocus"]
    assert zernike_name(5) == "oblique astigmatism" and zernike_name(6) == "vertical astigmatism"
    assert zernike_name(7) == "vertical coma" and zernike_name(8) == "horizontal coma"
    assert zernike_name(11) == "primary spherical"
    assert zernike_name(14) == "Z(4,4)"


def _disc(n=300):
    rho = np.sqrt((np.arange(n) + 0.5) / n)          # equal-area midpoint rule in rho^2
    th = 2 * math.pi * np.arange(2 * n) / (2 * n)
    r, t = np.meshgrid(rho, th)
    return r, t


def test_orthonormal_over_disc():
    r, t = _disc()
    zs = [zernike(j, r, t) for j in range(1, 22)]
    gram = np.array([[np.mean(a * b) for b in zs] for a in zs])
    assert np.max(np.abs(gram - np.eye(21))) < 1e-3


def test_known_values():
    r = np.array([0.0, 0.5, 1.0])
    t = np.zeros(3)
    assert np.allclose(zernike(1, r, t), 1.0)
    assert np.allclose(zernike(4, r, t), math.sqrt(3) * (2 * r**2 - 1))          # defocus
    assert np.allclose(zernike(2, r, t), 2 * r)                                  # tip: 2 rho cos(theta)
    assert np.allclose(zernike(11, r, t), math.sqrt(5) * (6 * r**4 - 6 * r**2 + 1))
    assert zernike(4, np.array([1.2]), np.array([0.0]))[0] == 0.0                # outside the disc


def _setup(n=128):
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n, pitch_m=12.5e-6, pad=2)


def test_rms_equals_root_sum_of_squares_and_matches_samples():
    s = _setup()
    c = np.zeros(11)
    c[3], c[6], c[10] = 0.10, 0.05, 0.03          # defocus, coma, spherical (piston left at 0)
    w = wavefront_waves(c, s)
    x, y = slm_grid(s)
    inside = np.hypot(x, y) <= s.n_pix * s.pitch_m / 2
    assert np.sqrt(np.mean(w[inside] ** 2)) == pytest.approx(rms_waves(c), rel=0.03)
    assert rms_waves(c) == pytest.approx(math.sqrt(0.1**2 + 0.05**2 + 0.03**2))
    c[0] = 5.0
    assert rms_waves(c) == pytest.approx(math.sqrt(0.1**2 + 0.05**2 + 0.03**2))   # piston excluded
    assert rms_waves(c, include_piston=True) > 5.0


def test_phase_from_coeffs_wrapped_and_scaled():
    s = _setup(64)
    p = phase_from_coeffs([0.0, 0.0, 0.0, 0.5], s)
    assert p.dtype == np.float64 and p.shape == (64, 64) and p.min() >= 0 and p.max() < 2 * math.pi
    w = wavefront_waves([0.0, 0.0, 0.0, 0.5], s)
    assert np.allclose(np.exp(1j * p), np.exp(2j * math.pi * w))
    assert np.allclose(phase_from_coeffs([], s), 0.0)


def test_phase_from_coeffs_errors():
    s = _setup(16)
    with pytest.raises(ValueError):
        phase_from_coeffs(np.zeros(22), s)
    with pytest.raises(ValueError):
        phase_from_coeffs([math.nan], s)


def test_strehl_marechal():
    assert strehl([0, 0, 0, 0]) == 1.0
    sigma = 1 / 14
    assert strehl([0.0, sigma]) == pytest.approx(math.exp(-((2 * math.pi * sigma) ** 2)))
    assert strehl([0.0, sigma]) > 0.8
    assert strehl([0.0, 0.1]) < 0.8
