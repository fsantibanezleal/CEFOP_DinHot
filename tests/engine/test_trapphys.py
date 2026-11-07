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
    # Harada and Asakura 1996: alpha = 4 pi eps0 n_m^2 r^3 (m^2 - 1) / (m^2 + 2), m = n_p / n_m
    assert a == pytest.approx(4 * math.pi * 1.33**2 * (50e-9) ** 3 * tp.EPS0_F_PER_M * (er - 1) / (er + 2), rel=1e-12, abs=0)
    assert a > 0
    # the gradient force scales as r^3: a factor 1000 for a tenfold radius (dossier D3.1)
    assert tp.rayleigh_polarizability_Fm2(500e-9, 1.59, 1.33) / a == pytest.approx(1000.0)
    assert tp.rayleigh_polarizability_Fm2(50e-9, 1.2, 1.33) < 0     # lower index than the medium: repelled


def test_gaussian_stiffness_eq12_13():
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.33)
    i0 = tp.gaussian_peak_intensity_W_per_m2(1e-3, 0.5e-6)
    assert i0 == pytest.approx(2e-3 / (math.pi * 0.25e-12))
    k = tp.gaussian_stiffness_N_per_m(a, i0, 0.5e-6, n_medium=1.33)
    assert k == pytest.approx(2 * a / (1.33 * tp.C_M_PER_S * tp.EPS0_F_PER_M) * i0 / 0.25e-12, rel=1e-12, abs=0)
    assert k > 0
    # curvature form: kappa = -alpha/(2 n_m c eps0) I'' with I'' = -4 I0 / w^2 at the centre of a Gaussian
    assert tp.gradient_stiffness_N_per_m(a, -4 * i0 / 0.25e-12, n_medium=1.33) == pytest.approx(k, rel=1e-12, abs=0)


def test_medium_factor_vacuum_is_the_old_form():
    """n_medium = 1 (the default) is the vacuum form of the dossier, to the last digit."""
    a = 3.3e-33
    i0, w, curv = 2.1e10, 0.7e-6, -4.4e22
    assert tp.gradient_stiffness_N_per_m(a, curv) == -a / (2.0 * tp.C_M_PER_S * tp.EPS0_F_PER_M) * curv
    assert tp.gradient_stiffness_N_per_m(a, curv, n_medium=1.0) == tp.gradient_stiffness_N_per_m(a, curv)
    assert tp.gaussian_stiffness_N_per_m(a, i0, w) == 2.0 * a * i0 / (tp.C_M_PER_S * tp.EPS0_F_PER_M * w**2)
    er = 1.59**2
    assert tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.0) == 4 * math.pi * (50e-9) ** 3 * tp.EPS0_F_PER_M * (er - 1) / (er + 2)


def test_stiffness_closed_form_in_water():
    """kappa = (2 pi n_m r^3 / c) L(m) (-d2I/dx2), with L(m) = (m^2 - 1)/(m^2 + 2) (Harada and Asakura 1996)."""
    r, n_p, n_m = 0.1e-6, 1.59, 1.33
    m = n_p / n_m
    lm = (m**2 - 1) / (m**2 + 2)
    a = tp.rayleigh_polarizability_Fm2(r, n_p, n_m)
    assert a == pytest.approx(4 * math.pi * tp.EPS0_F_PER_M * n_m**2 * r**3 * lm, rel=1e-12, abs=0)
    curv = -3.0e22
    assert tp.gradient_stiffness_N_per_m(a, curv, n_medium=n_m) == pytest.approx(2 * math.pi * n_m * r**3 / tp.C_M_PER_S * lm * -curv, rel=1e-12, abs=0)
    ratio = tp.gradient_stiffness_N_per_m(a, curv, n_medium=n_m) / tp.gradient_stiffness_N_per_m(a, curv)
    assert ratio == pytest.approx(1 / n_m, rel=1e-12, abs=0)
    # against the old vacuum-prefactor alpha the full stiffness is larger by exactly n_m
    a_old = 4 * math.pi * r**3 * tp.EPS0_F_PER_M * lm
    assert tp.gradient_stiffness_N_per_m(a, curv, n_medium=n_m) / tp.gradient_stiffness_N_per_m(a_old, curv) == pytest.approx(n_m, rel=1e-12, abs=0)


def test_stiffness_map_carries_the_medium_factor():
    w, dx, n_m = 0.5e-6, 0.02e-6, 1.33
    ax = (np.arange(121) - 60) * dx
    xx, yy = np.meshgrid(ax, ax)
    rel = np.exp(-2 * (xx**2 + yy**2) / w**2)
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, n_m)
    i0 = tp.gaussian_peak_intensity_W_per_m2(1e-3, w)
    k_vac = tp.stiffness_map(rel, dx, i0, a)
    k_med = tp.stiffness_map(rel, dx, i0, a, n_medium=n_m)
    assert k_med[0] == pytest.approx(k_vac[0] / n_m, rel=1e-12, abs=0)
    assert k_med[1] == pytest.approx(k_vac[1] / n_m, rel=1e-12, abs=0)
    assert k_med[0][60, 60] == pytest.approx(tp.gaussian_stiffness_N_per_m(a, i0, w, n_medium=n_m), rel=5e-3)


def test_medium_index_domain_errors():
    with pytest.raises(ValueError):
        tp.gradient_stiffness_N_per_m(1e-33, -1e22, n_medium=0.0)
    with pytest.raises(ValueError):
        tp.gaussian_stiffness_N_per_m(1e-33, 1e10, 1e-6, n_medium=float("nan"))
    with pytest.raises(ValueError):
        tp.stiffness_map(np.ones((5, 5)), 1e-7, 1e10, 1e-33, n_medium=-1.0)


def test_stiffness_map_matches_analytic_gaussian():
    w, dx = 0.5e-6, 0.02e-6
    ax = (np.arange(121) - 60) * dx
    xx, yy = np.meshgrid(ax, ax)
    rel = np.exp(-2 * (xx**2 + yy**2) / w**2)              # relative intensity, peak 1
    a = tp.rayleigh_polarizability_Fm2(50e-9, 1.59, 1.33)
    i0 = tp.gaussian_peak_intensity_W_per_m2(1e-3, w)
    kxx, kyy = tp.stiffness_map(rel, dx, i0, a, n_medium=1.33)
    assert kxx.shape == rel.shape
    assert kxx[60, 60] == pytest.approx(tp.gaussian_stiffness_N_per_m(a, i0, w, n_medium=1.33), rel=5e-3)
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
