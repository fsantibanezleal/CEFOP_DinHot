"""Trap physics: gradient-force stiffness of a Rayleigh bead and dipole-trap depth and frequencies of an atom.

Names carry their units (``_m``, ``_N_per_m``, ``_W_per_m2``, ``_J``, ``_rad_s``, ``_Fm2`` = F m^2 = C m^2 / V).

Rayleigh bead (physics-viz D3.1, READ from Bouloumis and Nic Chormaic, arXiv 2001.07359, Eq. 5 to 14, who follow
Harada and Asakura 1996, not opened): polarizability ``alpha_0 = 4 pi r^3 eps0 (eps_r - 1) / (eps_r + 2)`` (Eq. 5,
Clausius-Mossotti), time-averaged gradient force ``F = (1/2) Re(alpha) / (c eps0) grad I`` (Eq. 9), and for a Gaussian focus
``I = I0 exp(-2 rho^2 / w0^2)`` the stiffness ``kappa = 2 Re(alpha) I0 / (c eps0 w0^2)`` (Eq. 12 and 13), ``U = kappa rho^2 / 2``
(Eq. 14). In general ``kappa_i = -Re(alpha) / (2 c eps0) d^2 I / d x_i^2``. Here ``eps_r = (n_particle / n_medium)^2`` and the
vacuum prefactor of the dossier is kept: the extra medium factors of a bead in water are not in the section read
(UNVERIFIED), so the magnitude carries that caveat. Radiation reaction (Eq. 6) and the scattering force are not modelled.

Atom (physics-viz D3.4, READ and verified on a rendered page, Grimm, Weidemuller and Ovchinnikov 2000, arXiv physics/9902072):
``U_dip = (3 pi c^2 / (2 omega0^3)) (Gamma / Delta) I`` (Eq. 12), ``Gamma_sc = (3 pi c^2 / (2 hbar omega0^3)) (Gamma / Delta)^2 I``
(Eq. 13), ``hbar Gamma_sc = (Gamma / Delta) U_dip`` (Eq. 14), with ``Delta = omega - omega0`` (red detuning, ``Delta < 0``, is
attractive). Focused Gaussian beam: ``I(r, z) = 2 P / (pi w^2(z)) exp(-2 r^2 / w^2(z))`` (Eq. 36), ``z_R = pi w0^2 / lambda``
(Eq. 37), ``U = -U_hat [1 - 2 (r / w0)^2 - (z / z_R)^2]`` (Eq. 38), so ``omega_r = sqrt(4 U_hat / (m w0^2))`` and
``omega_z = sqrt(2 U_hat / (m z_R^2))`` (text after Eq. 38).

Constants: SI 2019 exact values (c, k_B, h) and the CODATA 2018 value of eps0.
"""
from __future__ import annotations

import math

import numpy as np

C_M_PER_S = 299792458.0
KB_J_PER_K = 1.380649e-23
H_J_S = 6.62607015e-34
HBAR_J_S = H_J_S / (2.0 * math.pi)
EPS0_F_PER_M = 8.8541878128e-12


def _pos(name: str, v: float) -> float:
    if not (isinstance(v, (int, float, np.floating)) and math.isfinite(v) and v > 0):
        raise ValueError(f"{name} must be finite and positive, got {v!r}")
    return float(v)


def rayleigh_polarizability_Fm2(radius_m: float, n_particle: float, n_medium: float) -> float:
    """``alpha_0 = 4 pi r^3 eps0 (eps_r - 1) / (eps_r + 2)`` with ``eps_r = (n_particle / n_medium)^2`` (Eq. 5)."""
    r, npar, nmed = _pos("radius_m", radius_m), _pos("n_particle", n_particle), _pos("n_medium", n_medium)
    er = (npar / nmed) ** 2
    return 4.0 * math.pi * r**3 * EPS0_F_PER_M * (er - 1.0) / (er + 2.0)


def gradient_stiffness_N_per_m(alpha_Fm2: float, intensity_curvature_W_per_m4: float) -> float:
    """``kappa = -alpha / (2 c eps0) d^2 I / dx^2`` along one axis (from Eq. 9)."""
    return -alpha_Fm2 / (2.0 * C_M_PER_S * EPS0_F_PER_M) * intensity_curvature_W_per_m4


def gaussian_peak_intensity_W_per_m2(power_w: float, waist_m: float) -> float:
    """``I0 = 2 P / (pi w0^2)`` (Grimm Eq. 36 at r = z = 0)."""
    return 2.0 * _pos("power_w", power_w) / (math.pi * _pos("waist_m", waist_m) ** 2)


def gaussian_stiffness_N_per_m(alpha_Fm2: float, peak_intensity_W_per_m2: float, waist_m: float) -> float:
    """``kappa = 2 alpha I0 / (c eps0 w0^2)`` (Eq. 12 and 13)."""
    w = _pos("waist_m", waist_m)
    return 2.0 * alpha_Fm2 * peak_intensity_W_per_m2 / (C_M_PER_S * EPS0_F_PER_M * w**2)


def stiffness_map(
    intensity_map: np.ndarray, spacing_m: float, intensity_scale_W_per_m2: float, alpha_Fm2: float
) -> tuple[np.ndarray, np.ndarray]:
    """Local stiffness ``(kappa_xx, kappa_yy)`` in N/m at every pixel of a focal intensity map.

    The physical intensity is ``map * intensity_scale_W_per_m2`` (the scale converts the map's units, e.g. the
    ``I_m = |V|^2`` units of the engine, to W/m^2; ``gaussian_peak_intensity_W_per_m2`` gives it for a trap of known
    power and waist). Second derivatives are 3-point central differences with the border rows copied from the next row.
    """
    i = np.asarray(intensity_map, dtype=np.float64)
    if i.ndim != 2 or min(i.shape) < 3 or not np.all(np.isfinite(i)):
        raise ValueError("intensity_map must be a finite 2D array of at least 3 x 3")
    dx = _pos("spacing_m", spacing_m)
    ph = i * _pos("intensity_scale_W_per_m2", intensity_scale_W_per_m2)
    d2x, d2y = np.zeros_like(ph), np.zeros_like(ph)
    d2x[:, 1:-1] = (ph[:, 2:] - 2 * ph[:, 1:-1] + ph[:, :-2]) / dx**2
    d2y[1:-1, :] = (ph[2:, :] - 2 * ph[1:-1, :] + ph[:-2, :]) / dx**2
    d2x[:, 0], d2x[:, -1] = d2x[:, 1], d2x[:, -2]
    d2y[0, :], d2y[-1, :] = d2y[1, :], d2y[-2, :]
    return (gradient_stiffness_N_per_m(alpha_Fm2, d2x), gradient_stiffness_N_per_m(alpha_Fm2, d2y))


def rayleigh_range_m(waist_m: float, wavelength_m: float) -> float:
    """``z_R = pi w0^2 / lambda`` (Grimm Eq. 37)."""
    return math.pi * _pos("waist_m", waist_m) ** 2 / _pos("wavelength_m", wavelength_m)


def dipole_potential_J(intensity_W_per_m2: float, omega0_rad_s: float, gamma_rad_s: float, delta_rad_s: float) -> float:
    """``U_dip = (3 pi c^2 / (2 omega0^3)) (Gamma / Delta) I`` (Grimm Eq. 12); negative for red detuning."""
    o, g = _pos("omega0_rad_s", omega0_rad_s), _pos("gamma_rad_s", gamma_rad_s)
    if not math.isfinite(delta_rad_s) or delta_rad_s == 0:
        raise ValueError("delta_rad_s must be finite and non-zero")
    return 3.0 * math.pi * C_M_PER_S**2 / (2.0 * o**3) * (g / delta_rad_s) * intensity_W_per_m2


def scattering_rate_per_s(intensity_W_per_m2: float, omega0_rad_s: float, gamma_rad_s: float, delta_rad_s: float) -> float:
    """``Gamma_sc = (3 pi c^2 / (2 hbar omega0^3)) (Gamma / Delta)^2 I`` (Grimm Eq. 13)."""
    o, g = _pos("omega0_rad_s", omega0_rad_s), _pos("gamma_rad_s", gamma_rad_s)
    if not math.isfinite(delta_rad_s) or delta_rad_s == 0:
        raise ValueError("delta_rad_s must be finite and non-zero")
    return 3.0 * math.pi * C_M_PER_S**2 / (2.0 * HBAR_J_S * o**3) * (g / delta_rad_s) ** 2 * intensity_W_per_m2


def dipole_trap_depth_J(power_w: float, waist_m: float, omega0_rad_s: float, gamma_rad_s: float, delta_rad_s: float) -> float:
    """``U_hat = -U_dip(I0)`` of a focused Gaussian beam (Eq. 36 and 38); raises for blue detuning (no trap)."""
    u = dipole_potential_J(gaussian_peak_intensity_W_per_m2(power_w, waist_m), omega0_rad_s, gamma_rad_s, delta_rad_s)
    if u >= 0:
        raise ValueError("the dipole potential is repulsive (blue detuning): there is no trap")
    return -u


def trap_frequencies_rad_s(depth_J: float, mass_kg: float, waist_m: float, wavelength_m: float) -> tuple[float, float]:
    """``(omega_r, omega_z)`` with ``omega_r = sqrt(4 U_hat / (m w0^2))``, ``omega_z = sqrt(2 U_hat / (m z_R^2))``."""
    d, m, w = _pos("depth_J", depth_J), _pos("mass_kg", mass_kg), _pos("waist_m", waist_m)
    zr = rayleigh_range_m(w, wavelength_m)
    return math.sqrt(4.0 * d / (m * w**2)), math.sqrt(2.0 * d / (m * zr**2))
