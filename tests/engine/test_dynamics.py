from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.dynamics import (
    AtomParams, BeadParams, atom_trajectory, bead_trajectory, boltzmann_check, fit_lorentzian, psd,
)
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.trapphys import KB_J_PER_K

R = 1.0e-6                      # parabola reaches zero at |r| = R


def parabola(n=101):
    ax = np.linspace(-R, R, n)
    xx, yy = np.meshgrid(ax, ax)
    return np.clip(1.0 - (xx**2 + yy**2) / R**2, 0.0, None), (ax, ax)


def bead_setup(kappa=1e-5, radius=0.5e-6, eta=0.93e-3):
    gamma = 6 * math.pi * eta * radius
    depth = kappa * R**2 / 2          # U = -depth * (1 - r^2/R^2): kappa = 2 depth / R^2
    return BeadParams(depth_J=depth, gamma_Ns_per_m=gamma, temperature_K=295.0), kappa, gamma


def test_corner_frequency_oracle():
    imap, grid = parabola()
    params, kappa, gamma = bead_setup()
    tau = gamma / kappa
    dt = tau / 40
    traj = bead_trajectory(imap, grid, params, 2**17, dt, Rng(1234))
    assert traj.shape == (2**17 + 1, 2)
    fc_expected = kappa / (2 * math.pi * gamma)
    f, p = psd(traj[:, 0], dt, segments=64)
    keep = f <= 5 * fc_expected
    fc, d = fit_lorentzian(f[keep], p[keep])
    assert fc == pytest.approx(fc_expected, rel=0.10)
    assert d == pytest.approx(KB_J_PER_K * 295.0 / gamma, rel=0.15)


def test_equipartition_and_boltzmann():
    imap, grid = parabola()
    params, kappa, gamma = bead_setup()
    dt = gamma / kappa / 40
    traj = bead_trajectory(imap, grid, params, 2**17, dt, Rng(77))
    var = np.var(traj[:, 0])
    assert var == pytest.approx(KB_J_PER_K * 295.0 / kappa, rel=0.1)
    def u(x):
        return 0.5 * kappa * x**2
    good = boltzmann_check(traj[:, 0], u, 295.0)
    bad = boltzmann_check(traj[:, 0], lambda x: 0.5 * 4 * kappa * x**2, 295.0)
    assert good["total_variation"] < 0.06
    assert bad["total_variation"] > 2 * good["total_variation"]


def test_bead_determinism_and_seed():
    imap, grid = parabola(41)
    params, kappa, gamma = bead_setup()
    a = bead_trajectory(imap, grid, params, 500, gamma / kappa / 40, Rng(1))
    b = bead_trajectory(imap, grid, params, 500, gamma / kappa / 40, Rng(1))
    c = bead_trajectory(imap, grid, params, 500, gamma / kappa / 40, Rng(2))
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_bead_force_points_to_the_maximum():
    imap, grid = parabola(41)
    params = BeadParams(depth_J=1e-17, gamma_Ns_per_m=1e-8, temperature_K=0.0, start_m=(0.5e-6, -0.5e-6))
    traj = bead_trajectory(imap, grid, params, 200, 1e-6, Rng(1))
    assert np.hypot(*traj[-1]) < np.hypot(*traj[0])           # no noise at T = 0: it slides down to the centre


def test_atom_harmonic_frequency_and_energy():
    imap, grid = parabola()
    m = 1.443e-25
    depth = 1e-27
    kappa = 2 * depth / R**2
    omega = math.sqrt(kappa / m)
    period = 2 * math.pi / omega
    dt = period / 400
    params = AtomParams(depth_J=depth, mass_kg=m, temperature_K=0.0, start_m=(0.3e-6, 0.0))
    pos, vel = atom_trajectory(imap, grid, params, 1200, dt, Rng(3))
    assert pos.shape == vel.shape == (1201, 2)
    x = pos[:, 0]
    crossings = np.flatnonzero(np.diff(np.sign(x)) != 0)
    half_period = np.mean(np.diff(crossings)) * dt
    assert 2 * half_period == pytest.approx(period, rel=0.01)
    e = 0.5 * m * np.sum(vel**2, axis=1) + 0.5 * kappa * np.sum(pos**2, axis=1)
    assert np.ptp(e) / e.mean() < 5e-3


def test_atom_thermal_start_and_kick_heating():
    imap, grid = parabola(61)
    m = 1.443e-25
    depth = 1e-27
    omega = math.sqrt(2 * depth / R**2 / m)
    dt = 2 * math.pi / omega / 200
    cold = AtomParams(depth_J=depth, mass_kg=m, temperature_K=1e-6)
    hot = AtomParams(depth_J=depth, mass_kg=m, temperature_K=1e-6, kick_m_per_s=2e-4)
    _, v0 = atom_trajectory(imap, grid, cold, 2000, dt, Rng(5))
    _, v1 = atom_trajectory(imap, grid, hot, 2000, dt, Rng(5))
    z = Rng(5).normal_array(2)                                   # draw order: initial velocity first
    assert np.allclose(v0[0], math.sqrt(KB_J_PER_K * 1e-6 / m) * z)
    assert np.mean(v1[-500:] ** 2) > np.mean(v0[-500:] ** 2)


def test_psd_normalisation_white_noise():
    dt = 1e-3
    x = Rng(9).normal_array(2**16) * 2.0
    f, p = psd(x, dt, segments=16)
    assert f[0] > 0 and f[-1] <= 0.5 / dt
    assert np.sum(p) * (f[1] - f[0]) == pytest.approx(np.var(x), rel=0.05)


def test_psd_single_tone():
    dt = 1e-3
    t = np.arange(2**14) * dt
    x = 3.0 * np.sin(2 * math.pi * 50.0 * t)
    f, p = psd(x, dt, segments=8)
    assert f[np.argmax(p)] == pytest.approx(50.0, abs=1.0)
    assert np.sum(p) * (f[1] - f[0]) == pytest.approx(4.5, rel=0.05)    # variance of A sin = A^2 / 2


def test_fit_lorentzian_exact_input():
    f = np.linspace(1, 500, 300)
    fc, d = 80.0, 2e-12
    p = d / (math.pi**2 * (f**2 + fc**2))
    fc_fit, d_fit = fit_lorentzian(f, p)
    assert fc_fit == pytest.approx(fc, rel=1e-9) and d_fit == pytest.approx(d, rel=1e-9)


def test_errors():
    imap, grid = parabola(21)
    params, kappa, gamma = bead_setup()
    with pytest.raises(ValueError):
        bead_trajectory(imap, grid, params, 0, 1e-5, Rng(1))
    with pytest.raises(ValueError):
        bead_trajectory(imap, grid, params, 10, -1.0, Rng(1))
    with pytest.raises(ValueError):
        bead_trajectory(np.zeros((21, 21)), grid, params, 10, 1e-5, Rng(1))        # no intensity maximum
    with pytest.raises(ValueError):
        bead_trajectory(imap[:5], grid, params, 10, 1e-5, Rng(1))
    with pytest.raises(ValueError):
        BeadParams(depth_J=-1.0, gamma_Ns_per_m=1e-8)
    with pytest.raises(ValueError):
        psd(np.zeros(10), 1e-3, segments=20)
    with pytest.raises(ValueError):
        fit_lorentzian(np.array([1.0, 2.0]), np.array([1.0, 1.0]))     # flat: no corner
    with pytest.raises(ValueError):
        AtomParams(depth_J=1e-27, mass_kg=-1.0)
