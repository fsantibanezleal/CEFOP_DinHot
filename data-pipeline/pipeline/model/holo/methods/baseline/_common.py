"""Helpers shared by the baseline and control methods (no ``SPEC``: the registry skips this module).

- ``require_kinds`` raises the ``ValueError`` of the missing-data rule (unsupported target kind names the supported ones).
- ``Recorder`` builds the per-iteration ``history`` (keys of ``core.types.HISTORY_KEYS``) and tracks the time budget.
- ``sr_start`` is the superposition-of-random-phase starting hologram of Di Leonardo et al. 2007 (drawn through ``rng``).
- ``fft_fields`` and ``fft_backproject`` are the FFT form of the trap projection and of its adjoint (focal-plane deltas at
  the trap bins), the pair that makes the FFT form and the point-trap form identical for traps on bins (z = 0, no vortex).
"""
from __future__ import annotations

import time

import numpy as np

from ...core.forward import fft_focal_field, fft_inverse, point_trap_backproject, trap_bins, trap_fields_from_fft
from ...core.geometry import Setup
from ...core.metrics import efficiency, rel_std, trap_intensities, uniformity
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, Target

TINY = 1e-300


def require_kinds(target: Target, supported: tuple, method_id: str) -> None:
    """Raise ``ValueError`` naming the supported target kinds when the target kind is not one of them."""
    if target.kind not in supported:
        raise ValueError(f"{method_id} supports the target kinds {list(supported)}, got {target.kind!r}")


def phasor(v: np.ndarray) -> np.ndarray:
    """``v / |v|`` with the phasor 1 where ``v`` is zero."""
    a = np.abs(v)
    return np.where(a > TINY, v / np.maximum(a, TINY), 1.0 + 0.0j)


def amp_targets(traps: TrapSet) -> np.ndarray:
    """Target amplitudes ``sqrt(w_m)`` (the trap weight is a target intensity)."""
    return np.sqrt(traps.weight)


def sr_start(setup: Setup, traps: TrapSet, rng: Rng) -> np.ndarray:
    """``arg sum_m sqrt(w_m) exp(i (Delta^m + theta_m))`` with ``theta_m`` uniform: the SR hologram."""
    theta = rng.phases(len(traps))
    return np.angle(point_trap_backproject(amp_targets(traps) * np.exp(1j * theta), setup, traps))


def start_phase(setup: Setup, traps: TrapSet, rng: Rng, init: np.ndarray | None) -> np.ndarray:
    """``init`` (validated shape) when given, else the SR start."""
    if init is None:
        return sr_start(setup, traps, rng)
    phi = np.asarray(init, dtype=np.float64)
    if phi.shape != (setup.n_pix, setup.n_pix) or not np.all(np.isfinite(phi)):
        raise ValueError(f"init must be a finite array of shape {(setup.n_pix, setup.n_pix)}")
    return phi.copy()


def fft_fields(phi: np.ndarray, setup: Setup, traps: TrapSet) -> tuple[np.ndarray, np.ndarray]:
    """Focal field ``E`` and trap fields ``V_m = E[bin] pad / n_pix`` of the hologram ``phi``."""
    e = fft_focal_field(phi, setup)
    return e, trap_fields_from_fft(e, setup, traps)


def fft_backproject(coeffs: np.ndarray, setup: Setup, traps: TrapSet) -> np.ndarray:
    """SLM field from focal deltas ``c_m`` at the trap bins (adjoint of ``fft_fields``; the overall scale is irrelevant)."""
    iy, ix = trap_bins(setup, traps)
    f = np.zeros((setup.n_fft, setup.n_fft), dtype=np.complex128)
    np.add.at(f, (iy, ix), np.asarray(coeffs, dtype=np.complex128) * (setup.n_pix / setup.pad))
    return fft_inverse(f, setup)


class Recorder:
    """History recorder for a run: ``add(iteration, v)`` appends the entry, ``done()`` tells when the budget is spent."""

    def __init__(self, budget: Budget, weights: np.ndarray | None = None):
        self.budget, self.weights = budget, weights
        self.t0 = time.perf_counter()
        self.history: list = []

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def add(self, iteration: int, v: np.ndarray, **extra) -> dict:
        i_raw = trap_intensities(v)
        i_w = trap_intensities(v, self.weights)
        entry = {
            "iteration": int(iteration), "efficiency": efficiency(i_raw), "uniformity": uniformity(i_w),
            "rel_std": rel_std(i_w), "time_s": self.elapsed(),
        }
        entry.update(extra)
        self.history.append(entry)
        return entry

    def done(self, iteration: int) -> bool:
        """True after ``iteration`` iterations when the iteration cap or the time cap is reached."""
        if iteration >= self.budget.iterations:
            return True
        return self.budget.time_s is not None and self.elapsed() >= self.budget.time_s
