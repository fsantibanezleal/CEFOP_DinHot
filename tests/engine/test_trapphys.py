from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core import trapphys as tp


def test_constants():
    assert tp.C_M_PER_S == 299792458.0
    assert tp.KB_J_PER_K == 1.380649e-23
    assert tp.H_J_S == 6.62607015e-34
    assert tp.HBAR_J_S == pytest.approx(tp.H_J_S / (2 * math.pi))
    assert tp.EPS0_F_PER_M == pytest.approx(8.8541878128e-12)


def test_polarizability_clausius_mossotti_and_r3_scaling():
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.33)
    er = (1.59 / 1.33) ** 2
    assert a == pytest.approx(4 * math.pi * (50e-9) ** 3 * tp.EPS0_F_PER_M * (er - 1) / (er + 2))
    assert a > 0
    # the gradient force scales as r^3: a factor 1000 for a tenfold radius (dossier D3.1)
    assert tp.rayleigh_polarizability_Fm2(500e-9, 1.59, 1.33) / a == pytest.approx(1000.0)
    assert tp.rayleigh_polarizability_Fm2(50e-9, 1.2, 1.33) < 0     # lower index than the medium: repelled


def test_gaussian_stiffness_eq12_13():
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.33)
    i0 = tp.gaussian_peak_intensity_W_per_m2(1e-3, 0.5e-6)
    assert i0 == pytest.approx(2e-3 / (math.pi * 0.25e-12))
    k = tp.gaussian_stiffness_N_per_m(a, i0, 0.5e-6)
    assert k == pytest.approx(2 * a / (tp.C_M_PER_S * tp.EPS0_F_PER_M) * i0 / 0.25e-12)
    assert k > 0
    # curvature form: kappa = -alpha/(2 c eps0) I'' with I'' = -4 I0 / w^2 at the centre of a Gaussian
    assert tp.gradient_stiffness_N_per_m(a, -4 * i0 / 0.25e-12) == pytest.approx(k)


def test_stiffness_map_matches_analytic_gaussian():
    w, dx = 0.5e-6, 0.02e-6
    ax = (np.arange(121) - 60) * dx
    xx, yy = np.meshgrid(ax, ax)
    rel = np.exp(-2 * (xx**2 + yy**2) / w**2)              # relative intensity, peak 1
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.33)
    i0 = tp.gaussian_peak_intensity_W_per_m2(1e-3, w)
    kxx, kyy = tp.stiffness_map(rel, dx, i0, a)
    assert kxx.shape == rel.shape
    assert kxx[60, 60] == pytest.approx(tp.gaussian_stiffness_N_per_m(a, i0, w), rel=5e-3)
    assert kyy[60, 60] == pytest.approx(kxx[60, 60], rel=1e-9)
    assert kxx[60, 0] < kxx[60, 60]                         # the flank is not stiffer than the centre... sign check
    with pytest.raises(ValueError):
        tp.stiffness_map(np.zeros(5), dx, i0, a)
    with pytest.raises(ValueError):
        tp.stiffness_map(rel, -1.0, i0, a)


def test_dipole_potential_signs_and_eq14():
    om0 = 2 * math.pi * 3.8e14
    gam = 2 * math.pi * 6.07e6
    i = 1e9
    u_red = tp.dipole_potential_J(i, om0, gam, -2 * math.pi * 1e13)
    u_blue = tp.dipole_potential_J(i, om0, gam, +2 * math.pi * 1e13)
    assert u_red < 0 < u_blue and u_red == pytest.approx(-u_blue)
    d = -2 * math.pi * 1e13
    # hbar Gamma_sc = (Gamma / Delta) U_dip  (Grimm Eq. 14)
    assert tp.HBAR_J_S * tp.scattering_rate_per_s(i, om0, gam, d) == pytest.approx(gam / d * tp.dipole_potential_J(i, om0, gam, d))
    # I / Delta scaling of U and I / Delta^2 of the scattering
    assert tp.dipole_potential_J(i, om0, gam, 2 * d) == pytest.approx(tp.dipole_potential_J(i, om0, gam, d) / 2)
    assert tp.scattering_rate_per_s(i, om0, gam, 2 * d) == pytest.approx(tp.scattering_rate_per_s(i, om0, gam, d) / 4)


def test_trap_depth_and_frequencies_ebadi_check():
    # physics-viz D3.3: depth h * 17 MHz, 87Rb, waist 0.9 um gives omega_r / 2 pi ~ 99 kHz (DERIVED there)
    depth = tp.H_J_S * 17e6
    wr, wz = tp.trap_frequencies_rad_s(depth, 1.443e-25, 0.9e-6, 0.82e-6)
    assert wr / (2 * math.pi) == pytest.approx(99e3, rel=0.02)
    zr = tp.rayleigh_range_m(0.9e-6, 0.82e-6)
    assert zr == pytest.approx(math.pi * 0.9e-6**2 / 0.82e-6)
    assert wz == pytest.approx(math.sqrt(2 * depth / (1.443e-25 * zr**2)))
    assert wz < wr


def test_dipole_trap_depth_uses_gaussian_peak():
    om0, gam, d = 2 * math.pi * 3.8e14, 2 * math.pi * 6.07e6, -2 * math.pi * 1e13
    p, w = 3e-3, 1e-6
    depth = tp.dipole_trap_depth_J(p, w, om0, gam, d)
    assert depth == pytest.approx(-tp.dipole_potential_J(2 * p / (math.pi * w**2), om0, gam, d))
    assert depth > 0
    with pytest.raises(ValueError):
        tp.dipole_trap_depth_J(p, w, om0, gam, +abs(d))      # blue detuned: repulsive, no trap


@pytest.mark.parametrize("fn,args", [
    (tp.rayleigh_polarizability_Fm2, (-1e-9, 1.5, 1.3)),
    (tp.gaussian_peak_intensity_W_per_m2, (1e-3, 0.0)),
    (tp.rayleigh_range_m, (1e-6, -1.0)),
    (tp.trap_frequencies_rad_s, (-1.0, 1e-25, 1e-6, 1e-6)),
])
def test_domain_errors(fn, args):
    with pytest.raises(ValueError):
        fn(*args)
