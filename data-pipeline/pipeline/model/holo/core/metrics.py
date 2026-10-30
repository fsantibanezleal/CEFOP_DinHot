"""Trap-array metrics, one definition each (algorithms D1.0, Di Leonardo et al. 2007 eq (4); Bianchi and Di Leonardo 2010).

With ``I_m = |V_m|^2`` the fraction of the input power in the peak of trap m (see ``forward``):

- efficiency ``e = sum_m I_m``;
- uniformity ``u = 1 - (max I - min I) / (max I + min I)`` (1 is perfect; Polin et al. 2005 use the same ratio without
  the leading ``1 -``, which is a non-uniformity: do not mix them);
- relative standard deviation ``sigma = 100 std(I) / mean(I)`` in percent (population standard deviation, divisor M).

With target weights ``w_m`` the intensities that enter ``uniformity`` and ``rel_std`` are ``I_m / w_m``
(``trap_intensities(V, weights)``); the efficiency uses the raw ``I_m`` (``trap_intensities(V)``).

``zero_order_fraction``, ``ghost_fraction`` and ``power_budget`` account for where the rest of the power goes.
"""
from __future__ import annotations

import numpy as np

from .forward import trap_bins
from .geometry import Setup
from .traps import TrapSet


def _vec(i: np.ndarray, name: str = "intensities") -> np.ndarray:
    i = np.asarray(i, dtype=np.float64)
    if i.ndim != 1 or i.size == 0:
        raise ValueError(f"{name} must be a non-empty 1D array")
    if not np.all(np.isfinite(i)):
        raise ValueError(f"{name} contain NaN or infinite values")
    return i


def trap_intensities(v: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    """``I_m = |V_m|^2``, divided by the target weights ``w_m`` when given (positive, one per trap)."""
    v = np.asarray(v)
    i = np.abs(v) ** 2
    if weights is None:
        return i
    w = np.asarray(weights, dtype=np.float64)
    if w.shape != i.shape:
        raise ValueError(f"weights shape {w.shape} differs from the trap count {i.shape}")
    if not np.all(np.isfinite(w)) or np.any(w <= 0):
        raise ValueError("weights must be finite and positive")
    return i / w


def efficiency(i: np.ndarray) -> float:
    """``e = sum_m I_m``."""
    return float(np.sum(_vec(i)))


def uniformity(i: np.ndarray) -> float:
    """``u = 1 - (max I - min I) / (max I + min I)``; raises if all intensities are zero."""
    i = _vec(i)
    s = i.max() + i.min()
    if s <= 0:
        raise ValueError("uniformity is undefined when all intensities are zero")
    return float(1.0 - (i.max() - i.min()) / s)


def rel_std(i: np.ndarray) -> float:
    """``sigma = 100 std(I) / mean(I)`` in percent; raises if the mean is zero."""
    i = _vec(i)
    mean = i.mean()
    if mean <= 0:
        raise ValueError("relative standard deviation is undefined when the mean intensity is zero")
    return float(100.0 * i.std() / mean)


def zero_order_fraction(e: np.ndarray, setup: Setup) -> float:
    """Peak fraction at the zero order, ``|V_0|^2 = |E[0, 0]|^2 pad^2 / N_pix`` (same units as a trap's ``I_m``)."""
    e = _check(e, setup)
    h = setup.n_fft // 2
    return float(np.abs(e[h, h]) ** 2 * setup.pad**2 / setup.n_pix**2)


def _check(e: np.ndarray, setup: Setup) -> np.ndarray:
    e = np.asarray(e)
    if e.shape != (setup.n_fft, setup.n_fft):
        raise ValueError(f"focal field must have shape {(setup.n_fft, setup.n_fft)}, got {e.shape}")
    return e


def power_budget(e: np.ndarray, setup: Setup, traps: TrapSet, radius_bins: float | None = None) -> dict[str, float]:
    """Where the input power goes, as fractions of ``N_pix`` (integrated power, not peak values).

    - ``traps``: power within ``radius_bins`` (default ``pad``) of the bin of any trap;
    - ``zero_order``: power within the same radius of bin (0, 0) that is not already counted for a trap;
    - ``ghosts``: all other power on the FFT grid. The grid spans exactly one replica period ``lambda f / p`` (physics-viz
      D1.2), so light of the pixel-sampling replicas folds onto it and is counted here together with ghost images
      and diffraction tails;
    - ``remainder``: ``1 - (sum of the three)``, the power that is not on the grid (zero for the plain FFT form by
      Parseval; positive when the field has been attenuated by a device envelope or camera model).
    The discs are clipped at the grid edge. ``radius_bins`` must be positive.
    """
    e = _check(e, setup)
    r = float(setup.pad if radius_bins is None else radius_bins)
    if not r > 0:
        raise ValueError("radius_bins must be positive")
    m = setup.n_fft
    pw = np.abs(e) ** 2 / setup.n_pix**2
    iy, ix = trap_bins(setup, traps)
    yy, xx = np.indices((m, m))
    near_trap = np.zeros((m, m), dtype=bool)
    for a, b in zip(iy, ix):
        near_trap |= (yy - a) ** 2 + (xx - b) ** 2 <= r * r
    h = m // 2
    near_zero = ((yy - h) ** 2 + (xx - h) ** 2 <= r * r) & ~near_trap
    p_trap = float(pw[near_trap].sum())
    p_zero = float(pw[near_zero].sum())
    p_ghost = float(pw.sum()) - p_trap - p_zero
    return {"traps": p_trap, "zero_order": p_zero, "ghosts": p_ghost, "remainder": 1.0 - float(pw.sum())}


def ghost_fraction(e: np.ndarray, setup: Setup, traps: TrapSet, radius_bins: float) -> float:
    """The ``ghosts`` entry of ``power_budget`` (power outside the trap and zero-order discs)."""
    return power_budget(e, setup, traps, radius_bins)["ghosts"]
