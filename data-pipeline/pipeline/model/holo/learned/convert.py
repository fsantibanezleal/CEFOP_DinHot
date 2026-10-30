"""Unit conversion between the engine (metres) and the model-slot coordinates (focal bins and SLM-limited Rayleigh ranges);
numpy only. See ``torch_forward`` for the definitions."""
from __future__ import annotations

import math

import numpy as np

from ..core.geometry import Setup, focal_bin_m
from ..core.traps import Trap, TrapSet

MAX_TRAPS = 1024


def rayleigh_range_m(setup: Setup) -> float:
    """``z_R = lambda f^2 / (pi R^2)``, ``R = N p / 2``: the Rayleigh range of the beam the SLM aperture focuses."""
    r = setup.n_pix * setup.pitch_m / 2.0
    return setup.wavelength_m * setup.focal_m**2 / (math.pi * r * r)


def traps_to_input(setup: Setup, traps: TrapSet) -> tuple[np.ndarray, np.ndarray]:
    """``(traps float32 [1, 1024, 4], mask float32 [1, 1024])`` for the warmstart-model; ``ValueError`` above 1024 traps or
    for a vortex trap (the slot does not take charges)."""
    m = len(traps)
    if m > MAX_TRAPS:
        raise ValueError(f"the warm start takes at most {MAX_TRAPS} traps, got {m}")
    if np.any(traps.charge != 0):
        raise ValueError("the warm start does not take vortex traps")
    b, zr = focal_bin_m(setup), rayleigh_range_m(setup)
    arr = np.zeros((1, MAX_TRAPS, 4), dtype=np.float32)
    arr[0, :m, 0], arr[0, :m, 1] = traps.x_m / b, traps.y_m / b
    arr[0, :m, 2], arr[0, :m, 3] = traps.z_m / zr, traps.weight
    mask = np.zeros((1, MAX_TRAPS), dtype=np.float32)
    mask[0, :m] = 1.0
    return arr, mask


def input_to_traps(setup: Setup, arr: np.ndarray, mask: np.ndarray) -> TrapSet:
    """Inverse of ``traps_to_input`` for the valid entries (used by the tests and the evaluation)."""
    b, zr = focal_bin_m(setup), rayleigh_range_m(setup)
    idx = np.flatnonzero(np.asarray(mask).reshape(-1) > 0.5)
    a = np.asarray(arr, dtype=np.float64).reshape(-1, 4)
    return TrapSet(Trap(int(i), float(a[i, 0] * b), float(a[i, 1] * b), float(a[i, 2] * zr), float(a[i, 3])) for i in idx)
