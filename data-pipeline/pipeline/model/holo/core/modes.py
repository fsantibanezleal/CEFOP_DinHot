"""Elementary phase functions on the SLM grid: vortex, lens (axial offset) and grating (lateral offset).

They are the phase terms of the delay ``Delta_j^m`` of the point-trap model (algorithms D1.0, Di Leonardo et al. 2007
eqs (1) to (4)); a hologram that displays ``+Delta_j^m`` sends the light to the trap m (``V_m = 1`` for a flat beam).
All outputs are float64 in ``[0, 2 pi)``.
"""
from __future__ import annotations

import math

import numpy as np

from .geometry import Setup, slm_grid, wrap_phase


def vortex_phase(setup: Setup, charge: int, centre: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """``charge * atan2(y - cy, x - cx)``; ``centre`` in metres on the SLM (default: the optical axis)."""
    if int(charge) != charge:
        raise ValueError(f"charge must be an integer, got {charge!r}")
    if not all(math.isfinite(c) for c in centre):
        raise ValueError("centre must be finite")
    x, y = slm_grid(setup)
    return wrap_phase(charge * np.arctan2(y - centre[1], x - centre[0]))


def lens_phase(setup: Setup, z_m: float) -> np.ndarray:
    """Fresnel lens term ``pi z (x^2 + y^2) / (lambda f^2)``: moves the trap along the axis by ``z_m``."""
    if not math.isfinite(z_m):
        raise ValueError("z_m must be finite")
    x, y = slm_grid(setup)
    return wrap_phase(math.pi * z_m / (setup.wavelength_m * setup.focal_m**2) * (x**2 + y**2))


def grating_phase(setup: Setup, x_m: float, y_m: float) -> np.ndarray:
    """Blazed-grating term ``2 pi (x x_m + y y_m) / (lambda f)``: moves the trap laterally to ``(x_m, y_m)``."""
    if not (math.isfinite(x_m) and math.isfinite(y_m)):
        raise ValueError("trap position must be finite")
    x, y = slm_grid(setup)
    return wrap_phase(2.0 * math.pi / (setup.wavelength_m * setup.focal_m) * (x * x_m + y * y_m))
