"""Optical setup, SLM grid, input beam and focal sampling.

Units are SI (metres, radians); helpers named ``_um`` take micrometres. Arrays are indexed ``[iy, ix]``.

Focal sampling (physics-viz D1.2, READ from Schroff et al. 2023 Methods): one FFT bin of the zero-padded transform is
``lambda f / (pad N p)`` (the paper's 8.32 um for N = 1024, p = 12.5 um, f = 250 mm, pad = 2). The FFT grid has
``pad N`` bins, so it spans the replica period ``lambda f / p`` (DERIVED there); the unaliased half-window is
``lambda f / (2 p)``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _pos(name: str, v: float) -> None:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} must be a finite positive number, got {v!r}")


@dataclass(frozen=True)
class Setup:
    """Optical setup. ``n_pix`` is the SLM side (square), ``pad`` the integer padding factor (FFT grid ``pad * n_pix``).

    ``beam`` is ``"gaussian"`` (``waist_frac`` = 1/e^2 intensity waist over half the SLM side) or ``"flat"``.
    """

    wavelength_m: float
    focal_m: float
    na: float
    n_imm: float
    n_pix: int
    pitch_m: float
    pad: int = 2
    beam: str = "gaussian"
    waist_frac: float = 1.0

    def __post_init__(self) -> None:
        for name in ("wavelength_m", "focal_m", "na", "pitch_m", "waist_frac"):
            _pos(name, getattr(self, name))
        _pos("n_imm", self.n_imm)
        if self.n_imm < 1.0:
            raise ValueError(f"n_imm must be >= 1, got {self.n_imm}")
        if self.na > self.n_imm:
            raise ValueError(f"na {self.na} cannot exceed the immersion index {self.n_imm}")
        for name in ("n_pix", "pad"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise ValueError(f"{name} must be a positive integer, got {v!r}")
        if self.beam not in ("gaussian", "flat"):
            raise ValueError(f"beam must be 'gaussian' or 'flat', got {self.beam!r}")

    @property
    def n_fft(self) -> int:
        """Side of the FFT grid (``pad * n_pix``)."""
        return self.pad * self.n_pix


def slm_grid(setup: Setup) -> tuple[np.ndarray, np.ndarray]:
    """Pixel centres ``(x, y)`` in metres, shape ``(n_pix, n_pix)``, centred on the optical axis."""
    c = (np.arange(setup.n_pix) - (setup.n_pix - 1) / 2.0) * setup.pitch_m
    x, y = np.meshgrid(c, c)
    return x, y


def input_amplitude(setup: Setup) -> np.ndarray:
    """Input amplitude ``A_j`` on the SLM grid, normalised so that ``sum A_j^2 = n_pix^2`` (algorithms D1.0).

    Gaussian: intensity ``exp(-2 r^2 / w^2)`` with ``w = waist_frac * n_pix * pitch / 2``.
    """
    if setup.beam == "flat":
        return np.ones((setup.n_pix, setup.n_pix))
    x, y = slm_grid(setup)
    w = setup.waist_frac * setup.n_pix * setup.pitch_m / 2.0
    a = np.exp(-(x**2 + y**2) / w**2)
    return a * math.sqrt(setup.n_pix**2 / np.sum(a**2))


def focal_bin_m(setup: Setup) -> float:
    """One FFT bin in the focal plane, ``lambda f / (pad N p)`` (physics-viz D1.2)."""
    return setup.wavelength_m * setup.focal_m / (setup.pad * setup.n_pix * setup.pitch_m)


def half_field_m(setup: Setup) -> float:
    """Unaliased half-window ``lambda f / (2 p)`` (physics-viz D1.2, DERIVED there)."""
    return setup.wavelength_m * setup.focal_m / (2.0 * setup.pitch_m)


def um_to_bin(setup: Setup, x_um: float) -> float:
    """Micrometres in the focal plane to (fractional) FFT bins."""
    if not math.isfinite(x_um):
        raise ValueError(f"position must be finite, got {x_um!r}")
    return x_um * 1e-6 / focal_bin_m(setup)


def bin_to_um(setup: Setup, k: float) -> float:
    """FFT bins to micrometres in the focal plane."""
    if not math.isfinite(k):
        raise ValueError(f"bin must be finite, got {k!r}")
    return k * focal_bin_m(setup) * 1e6


def wrap_phase(phi: np.ndarray) -> np.ndarray:
    """Wrap to ``[0, 2 pi)`` as float64 (the convention of every displayed phase)."""
    out = np.mod(np.asarray(phi, dtype=np.float64), 2.0 * math.pi)
    # np.mod can return exactly 2 pi for tiny negative inputs
    return np.where(out >= 2.0 * math.pi, 0.0, out)
