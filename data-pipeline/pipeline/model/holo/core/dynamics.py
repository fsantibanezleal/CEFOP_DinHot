"""Particle dynamics in a computed focal intensity map: overdamped bead, underdamped atom, PSD and calibration.

Recipe (physics-viz D3.3, with the sources of D3.2):

- Bead (item 1): potential ``U(r) = -U0 I(r) / I_max``; force ``F = -grad U`` from a central-difference gradient of the map,
  bilinearly interpolated (positions outside the grid use the border values). Overdamped Euler-Maruyama step
  ``x_{n+1} = x_n + (dt / gamma) F(x_n) + sqrt(2 D dt) zeta_n`` with ``D = k_B T / gamma`` and ``zeta_n ~ N(0, 1)``. The
  dossier's design choice is ``dt <= tau / 20`` with ``tau = gamma / kappa``; the oracle test uses ``tau / 40``.
- Atom (item 2): ``m a = F``, velocity Verlet, optional heating as a Gaussian velocity kick of rms ``kick_m_per_s`` per
  step (design choice, not a source claim); initial velocity thermal ``sqrt(k_B T / m)`` per axis.
- Draw order from ``rng`` (ADR-0054; the TypeScript port draws in the same order): atom initial velocity (2 normals), then
  the noise or kick block ``normal_array(2 * n_steps)`` reshaped to ``(n_steps, 2)`` (x then y per step). The block is
  always drawn, so the stream does not depend on whether the kick is zero.
- PSD of a position trace: the one-sided periodogram of Hann-windowed segments, averaged. The thermal Lorentzian of
  Tolic-Norrelykke et al. 2006 (Eq. 4 to 8: ``D = k_B T / gamma``, ``f_c = kappa / (2 pi gamma)``,
  ``P(f) = D / (2 pi^2 (f^2 + f_c^2))``) integrates over positive AND negative f to ``k_B T / kappa``; the one-sided
  spectrum used here is twice that, ``P1(f) = D / (pi^2 (f^2 + f_c^2))`` (DERIVED from the same integral).
- ``fit_lorentzian`` fits ``1 / P = a + b f^2`` (a linearised least-squares fit, weights ``P^2`` because the relative error of
  an averaged periodogram bin is constant), so ``f_c = sqrt(a / b)`` and ``D = pi^2 / b``. The linearisation is biased at low
  segment counts (Norrelykke and Flyvbjerg 2010, arXiv 0906.1708, abstract only read: UNVERIFIED which correction applies);
  the oracle test bounds the effect at 10 percent for the run it uses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .rng import Rng
from .trapphys import KB_J_PER_K


def _finpos(name: str, v: float) -> float:
    if not (math.isfinite(v) and v > 0):
        raise ValueError(f"{name} must be finite and positive, got {v!r}")
    return float(v)


@dataclass(frozen=True)
class BeadParams:
    """Overdamped bead: trap depth ``depth_J`` at the intensity maximum, drag ``gamma_Ns_per_m`` (Stokes ``6 pi eta r``)."""

    depth_J: float
    gamma_Ns_per_m: float
    temperature_K: float = 295.0
    start_m: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        _finpos("depth_J", self.depth_J)
        _finpos("gamma_Ns_per_m", self.gamma_Ns_per_m)
        if not (math.isfinite(self.temperature_K) and self.temperature_K >= 0):
            raise ValueError("temperature_K must be finite and >= 0")


@dataclass(frozen=True)
class AtomParams:
    """Underdamped atom of mass ``mass_kg``; ``kick_m_per_s`` is the rms velocity kick per step (heating), default none."""

    depth_J: float
    mass_kg: float
    temperature_K: float = 0.0
    kick_m_per_s: float = 0.0
    start_m: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        _finpos("depth_J", self.depth_J)
        _finpos("mass_kg", self.mass_kg)
        if not (math.isfinite(self.temperature_K) and self.temperature_K >= 0):
            raise ValueError("temperature_K must be finite and >= 0")
        if not (math.isfinite(self.kick_m_per_s) and self.kick_m_per_s >= 0):
            raise ValueError("kick_m_per_s must be finite and >= 0")


class _Field:
    """Normalised intensity map with bilinear-interpolated gradient, as plain Python lists for a fast step loop."""

    def __init__(self, intensity_map: np.ndarray, grid_m: tuple[np.ndarray, np.ndarray]):
        i = np.asarray(intensity_map, dtype=np.float64)
        x, y = (np.asarray(g, dtype=np.float64) for g in grid_m)
        if i.ndim != 2 or i.shape != (y.size, x.size) or min(i.shape) < 3:
            raise ValueError("intensity_map must have shape (len(y), len(x)) with both at least 3")
        if not np.all(np.isfinite(i)):
            raise ValueError("intensity_map must be finite")
        dx, dy = np.diff(x), np.diff(y)
        if np.any(dx <= 0) or np.any(dy <= 0) or not (np.allclose(dx, dx[0]) and np.allclose(dy, dy[0])):
            raise ValueError("grid_m axes must be increasing and uniformly spaced")
        peak = i.max()
        if peak <= 0:
            raise ValueError("intensity_map has no positive maximum")
        i = i / peak
        gy, gx = np.gradient(i, y, x)
        self.x0, self.y0, self.dx, self.dy = float(x[0]), float(y[0]), float(dx[0]), float(dy[0])
        self.nx, self.ny = x.size, y.size
        self.gx, self.gy = gx.tolist(), gy.tolist()

    def grad(self, px: float, py: float) -> tuple[float, float]:
        """Bilinear gradient ``(dI/dx, dI/dy)`` of the normalised map at the point (clamped to the grid)."""
        u = min(max((px - self.x0) / self.dx, 0.0), self.nx - 1.000001)
        v = min(max((py - self.y0) / self.dy, 0.0), self.ny - 1.000001)
        i0, j0 = int(u), int(v)
        fu, fv = u - i0, v - j0
        w00, w10, w01, w11 = (1 - fu) * (1 - fv), fu * (1 - fv), (1 - fu) * fv, fu * fv
        gx, gy = self.gx, self.gy
        return (
            w00 * gx[j0][i0] + w10 * gx[j0][i0 + 1] + w01 * gx[j0 + 1][i0] + w11 * gx[j0 + 1][i0 + 1],
            w00 * gy[j0][i0] + w10 * gy[j0][i0 + 1] + w01 * gy[j0 + 1][i0] + w11 * gy[j0 + 1][i0 + 1],
        )


def _steps(n_steps: int, dt: float) -> int:
    if isinstance(n_steps, bool) or int(n_steps) != n_steps or n_steps < 1:
        raise ValueError("n_steps must be a positive integer")
    _finpos("dt", dt)
    return int(n_steps)


def bead_trajectory(
    intensity_map: np.ndarray, grid_m: tuple[np.ndarray, np.ndarray], params: BeadParams, n_steps: int, dt: float,
    rng: Rng,
) -> np.ndarray:
    """Positions ``(n_steps + 1, 2)`` in metres of an overdamped bead in the potential ``-depth * I / I_max``."""
    n = _steps(n_steps, dt)
    fld = _Field(intensity_map, grid_m)
    d = KB_J_PER_K * params.temperature_K / params.gamma_Ns_per_m
    amp = math.sqrt(2.0 * d * dt)
    drift = params.depth_J * dt / params.gamma_Ns_per_m          # F = -grad U = depth * grad(I / I_max)
    zeta = rng.normal_array(2 * n).reshape(n, 2).tolist()
    out = np.empty((n + 1, 2))
    px, py = params.start_m
    out[0] = px, py
    for k in range(n):
        gx, gy = fld.grad(px, py)
        px += drift * gx + amp * zeta[k][0]
        py += drift * gy + amp * zeta[k][1]
        out[k + 1, 0], out[k + 1, 1] = px, py
    return out


def atom_trajectory(
    intensity_map: np.ndarray, grid_m: tuple[np.ndarray, np.ndarray], params: AtomParams, n_steps: int, dt: float,
    rng: Rng,
) -> tuple[np.ndarray, np.ndarray]:
    """Velocity-Verlet positions and velocities, each ``(n_steps + 1, 2)``, of an atom in ``-depth * I / I_max``."""
    n = _steps(n_steps, dt)
    fld = _Field(intensity_map, grid_m)
    m = params.mass_kg
    k_force = params.depth_J / m                                 # acceleration = (depth / m) * grad(I / I_max)
    v_th = math.sqrt(KB_J_PER_K * params.temperature_K / m)
    z0 = rng.normal_array(2)
    kicks = (rng.normal_array(2 * n).reshape(n, 2) * params.kick_m_per_s).tolist()
    pos, vel = np.empty((n + 1, 2)), np.empty((n + 1, 2))
    px, py = params.start_m
    vx, vy = v_th * float(z0[0]), v_th * float(z0[1])
    pos[0], vel[0] = (px, py), (vx, vy)
    ax, ay = (k_force * g for g in fld.grad(px, py))
    for k in range(n):
        vx_h, vy_h = vx + 0.5 * dt * ax, vy + 0.5 * dt * ay
        px, py = px + dt * vx_h, py + dt * vy_h
        ax, ay = (k_force * g for g in fld.grad(px, py))
        vx, vy = vx_h + 0.5 * dt * ax + kicks[k][0], vy_h + 0.5 * dt * ay + kicks[k][1]
        pos[k + 1], vel[k + 1] = (px, py), (vx, vy)
    return pos, vel


def psd(x: np.ndarray, dt: float, segments: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """One-sided PSD (units of ``x^2 / Hz``): Hann-windowed periodograms of ``segments`` equal parts, averaged.

    Returns ``(f, P)`` without the zero-frequency bin. The mean of each segment is removed.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    _finpos("dt", dt)
    if isinstance(segments, bool) or int(segments) != segments or segments < 1:
        raise ValueError("segments must be a positive integer")
    nper = x.size // int(segments)
    if nper < 4:
        raise ValueError("the trace is too short for that number of segments")
    if not np.all(np.isfinite(x)):
        raise ValueError("x contains NaN or infinite values")
    w = np.hanning(nper)
    acc = np.zeros(nper // 2 + 1)
    for s in range(int(segments)):
        seg = x[s * nper:(s + 1) * nper]
        acc += np.abs(np.fft.rfft(w * (seg - seg.mean()))) ** 2
    p = acc / segments * dt / np.sum(w**2)
    p[1:-1 if nper % 2 == 0 else None] *= 2.0                     # one-sided: fold the negative frequencies
    f = np.fft.rfftfreq(nper, dt)
    return f[1:], p[1:]


def fit_lorentzian(f: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Corner frequency ``f_c`` (Hz) and ``D`` (x^2/s) of ``P1 = D / (pi^2 (f^2 + f_c^2))`` (module docstring).

    Weighted least squares of ``1 / P = a + b f^2`` with weights ``P^2``; ``ValueError`` if ``a`` or ``b`` is not positive.
    """
    f = np.asarray(f, dtype=np.float64).ravel()
    p = np.asarray(p, dtype=np.float64).ravel()
    if f.shape != p.shape or f.size < 3 or np.any(p <= 0) or not np.all(np.isfinite(p)):
        raise ValueError("need at least 3 matching frequency and positive finite PSD values")
    y, u, w = 1.0 / p, f**2, p**2
    sw, su, sy = w.sum(), (w * u).sum(), (w * y).sum()
    suu, suy = (w * u * u).sum(), (w * u * y).sum()
    den = sw * suu - su**2
    if den <= 0:
        raise ValueError("degenerate frequency set")
    b = (sw * suy - su * sy) / den
    a = (sy - b * su) / sw
    if not (a > 0 and b > 0):
        raise ValueError("no Lorentzian shape in the spectrum (non-positive intercept or slope)")
    return math.sqrt(a / b), math.pi**2 / b


def boltzmann_check(x: np.ndarray, potential_J, temperature_K: float, bins: int = 40) -> dict:
    """Compare the histogram of positions ``x`` with the Boltzmann density ``exp(-U(x) / k_B T)`` (1D, ``U`` a callable).

    Both are reduced to probabilities per bin over the range of ``x`` (the expected one integrates the density over
    each bin with 9 sub-points); ``total_variation`` is half the L1 distance (0 identical, 1 disjoint).
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    _finpos("temperature_K", temperature_K)
    if x.size < 10 or not np.all(np.isfinite(x)):
        raise ValueError("need at least 10 finite positions")
    emp, edges = np.histogram(x, bins=int(bins))
    emp = emp / emp.sum()
    sub = (edges[:-1, None] + (np.arange(9) + 0.5) / 9.0 * np.diff(edges)[:, None])
    u = np.asarray(potential_J(sub), dtype=np.float64)
    dens = np.exp(-(u - u.min()) / (KB_J_PER_K * temperature_K)).mean(axis=1)
    exp_p = dens / dens.sum()
    return {
        "total_variation": float(0.5 * np.abs(emp - exp_p).sum()),
        "bin_centres_m": 0.5 * (edges[:-1] + edges[1:]),
        "empirical": emp,
        "expected": exp_p,
    }
