"""Zernike aberrations in Noll order, orthonormal over the unit disc.

Definitions (physics-viz D2.3, READ from the Janssen documentation page, a library guide and not Noll's paper):
``Z_n^m(rho, theta) = N_n^m R_n^|m|(rho) {cos(m theta) for m >= 0, sin(|m| theta) for m < 0}`` with
``R_n^|m|(rho) = sum_s (-1)^s (n - s)! / (s! ((n+|m|)/2 - s)! ((n-|m|)/2 - s)!) rho^(n - 2 s)`` and the normalisation
``N = sqrt(2 (n + 1))`` for ``m != 0``, ``sqrt(n + 1)`` for ``m = 0``, which gives unit rms over the disc (orthogonality
``int Z Z' rho drho dtheta = pi eps_m delta delta'`` on the page). With this basis the rms wavefront error is the
root sum of squares of the coefficients (DERIVED there), ``sigma_W`` in waves.

Noll ordering: the table of the page for j = 1..11 (piston, tip, tilt, defocus, oblique and vertical astigmatism, vertical
and horizontal coma, vertical and oblique trefoil, primary spherical) and j = 12..15 = (4,2), (4,-2), (4,4), (4,-4)
from a secondary table. For j = 12..21 this module applies the Noll rule: within an n, even j takes the cos term
(m > 0), odd j the sin term (m < 0), ordered by increasing |m|. UNVERIFIED: Noll 1976 (JOSA 66, 207) itself was not opened;
sign conventions differ between sources. The gap research must re-check j = 12..21 and the signs.

Strehl (physics-viz D2.3, page statements): Marechal approximation ``S ~ exp[-(2 pi sigma_W)^2]`` (sigma_W in waves),
``S > 0.8`` for ``sigma_W < 1/14`` wave.
"""
from __future__ import annotations

import math

import numpy as np

from .geometry import Setup, slm_grid, wrap_phase

J_MAX = 21

_NAMES = {
    1: "piston", 2: "tip", 3: "tilt", 4: "defocus", 5: "oblique astigmatism", 6: "vertical astigmatism",
    7: "vertical coma", 8: "horizontal coma", 9: "vertical trefoil", 10: "oblique trefoil", 11: "primary spherical",
}


def _check_j(j) -> int:
    if isinstance(j, bool) or int(j) != j or not 1 <= j <= J_MAX:
        raise ValueError(f"Noll index must be an integer in 1..{J_MAX}, got {j!r}")
    return int(j)


def noll_to_nm(j: int) -> tuple[int, int]:
    """Radial order n and azimuthal order m (signed: m > 0 cos, m < 0 sin) of Noll index ``j`` (1..21)."""
    j = _check_j(j)
    n = 0
    while (n + 1) * (n + 2) // 2 < j:
        n += 1
    k = j - n * (n + 1) // 2 - 1                 # position within the order n
    m_abs = 2 * ((k + 1) // 2) if n % 2 == 0 else 2 * (k // 2) + 1
    if m_abs == 0:
        return n, 0
    return n, (m_abs if j % 2 == 0 else -m_abs)


def zernike_name(j: int) -> str:
    """Common name for j = 1..11 (page table); ``"Z(n,m)"`` for the rest."""
    j = _check_j(j)
    if j in _NAMES:
        return _NAMES[j]
    n, m = noll_to_nm(j)
    return f"Z({n},{m})"


def _radial(n: int, m_abs: int, rho: np.ndarray) -> np.ndarray:
    out = np.zeros_like(rho)
    for s in range((n - m_abs) // 2 + 1):
        c = ((-1) ** s) * math.factorial(n - s) / (
            math.factorial(s) * math.factorial((n + m_abs) // 2 - s) * math.factorial((n - m_abs) // 2 - s))
        out = out + c * rho ** (n - 2 * s)
    return out


def zernike(j: int, rho: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Orthonormal Zernike mode ``j`` (unit rms over the disc); zero for ``rho > 1``."""
    n, m = noll_to_nm(j)
    rho = np.asarray(rho, dtype=np.float64)
    theta = np.asarray(theta, dtype=np.float64)
    norm = math.sqrt(n + 1) if m == 0 else math.sqrt(2 * (n + 1))
    ang = np.ones_like(theta) if m == 0 else (np.cos(m * theta) if m > 0 else np.sin(-m * theta))
    return np.where(rho <= 1.0, norm * _radial(n, abs(m), rho) * ang, 0.0)


def _coeffs(c) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64).ravel()
    if c.size > J_MAX:
        raise ValueError(f"at most {J_MAX} coefficients (Noll j = 1..{J_MAX}), got {c.size}")
    if not np.all(np.isfinite(c)):
        raise ValueError("coefficients must be finite")
    return c


def wavefront_waves(coeffs_waves, setup: Setup) -> np.ndarray:
    """Unwrapped wavefront in waves on the SLM grid: ``sum_j c_j Z_j``; ``c_j`` for Noll j = index + 1.

    The pupil radius is half the SLM side; pixels outside the disc (the corners) are 0.
    """
    c = _coeffs(coeffs_waves)
    x, y = slm_grid(setup)
    r0 = setup.n_pix * setup.pitch_m / 2.0
    rho, theta = np.hypot(x, y) / r0, np.arctan2(y, x)
    w = np.zeros_like(rho)
    for j, cj in enumerate(c, start=1):
        if cj != 0.0:
            w = w + cj * zernike(j, rho, theta)
    return w


def phase_from_coeffs(coeffs_waves, setup: Setup) -> np.ndarray:
    """Phase in radians wrapped to ``[0, 2 pi)``: ``2 pi`` times ``wavefront_waves``. Empty coefficients give zeros."""
    return wrap_phase(2.0 * math.pi * wavefront_waves(coeffs_waves, setup))


def rms_waves(coeffs_waves, include_piston: bool = False) -> float:
    """Root sum of squares of the coefficients (orthonormal basis), piston excluded unless asked: it does not blur."""
    c = _coeffs(coeffs_waves)
    if not include_piston:
        c = c[1:]
    return float(math.sqrt(np.sum(c**2)))


def strehl(coeffs_waves) -> float:
    """Marechal approximation ``exp[-(2 pi sigma_W)^2]`` with ``sigma_W = rms_waves(coeffs)`` (piston excluded)."""
    return float(math.exp(-((2.0 * math.pi * rms_waves(coeffs_waves)) ** 2)))
