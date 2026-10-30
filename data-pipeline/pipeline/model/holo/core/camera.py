"""Emulated camera for closed-loop methods: per-trap gain error, additive noise, blur and edge roll-off.

EMULATION, not a model of a specific sensor: every error is a parameter with a stated meaning, so a feedback result
on this camera shows that the loop works against these errors, not against a real instrument (the dossier names a
measured hardware loop as a documented frontier).

- ``gain_rms``: each trap id has a fixed multiplicative gain ``exp(s z - s^2 / 2)`` with ``s = gain_rms`` and ``z`` the
  first normal of a stream seeded from ``(seed, trap id)``: log-normal with mean 1 and relative rms ``~ gain_rms``.
  Drawn once per trap id, independent of the order and composition of the trap set.
- ``noise_rms``: additive Gaussian noise per measurement, in the units of ``I_m`` (fraction of the input power), from the
  camera's own stream (seeded from ``seed``), so successive frames differ and a fresh camera with the same seed
  repeats the sequence. ``measure(..., rng=Rng)`` draws from the given stream instead. Results are clipped at 0.
- ``blur_bins``: Gaussian blur (sigma in FFT bins) of the intensity map, evaluated as a normalised weighted average
  over a ``+-ceil(3 sigma)`` window around each trap bin.
- ``rolloff``: multiplies each trap by the pixel-aperture envelope at its bin (``device.pixel_envelope`` for
  ``fill_factor``): the diffraction-efficiency roll-off of the ideal point-sampled hologram. Do not combine it with a
  field already produced by ``device_focal_field`` (that field carries the envelope).
"""
from __future__ import annotations

import math

import numpy as np

from .device import _sinc_1d
from .forward import trap_bins
from .geometry import Setup
from .rng import Rng
from .traps import TrapSet

_M = 0xFFFFFFFF


class EmulatedCamera:
    """Seeded emulated camera (see the module docstring for each error)."""

    def __init__(
        self, seed: int, gain_rms: float = 0.05, noise_rms: float = 0.0, blur_bins: float = 0.0,
        rolloff: bool = True, fill_factor: float = 1.0,
    ):
        for name, v in (("gain_rms", gain_rms), ("noise_rms", noise_rms), ("blur_bins", blur_bins)):
            if not (math.isfinite(v) and v >= 0):
                raise ValueError(f"{name} must be finite and >= 0, got {v!r}")
        if not (math.isfinite(fill_factor) and 0 < fill_factor <= 1):
            raise ValueError("fill_factor must be in (0, 1]")
        Rng(seed)  # validates the seed
        self.seed, self.gain_rms, self.noise_rms = int(seed), float(gain_rms), float(noise_rms)
        self.blur_bins, self.rolloff, self.fill_factor = float(blur_bins), bool(rolloff), float(fill_factor)
        self._noise = Rng((self.seed * 0x9E3779B1 + 0x1234567) & _M)

    def gain(self, trap_id: int) -> float:
        """The fixed gain of one trap id."""
        s = self.gain_rms
        if s == 0.0:
            return 1.0
        z = Rng((self.seed * 0x9E3779B1 + (int(trap_id) + 1) * 0x85EBCA6B) & _M).normal()
        return math.exp(s * z - 0.5 * s * s)

    def measure(self, e: np.ndarray, setup: Setup, traps: TrapSet, rng: Rng | None = None) -> np.ndarray:
        """Measured trap intensities (units of ``I_m = |V|^2``) from the centred focal field ``e`` (``n_fft^2``)."""
        e = np.asarray(e)
        if e.shape != (setup.n_fft, setup.n_fft):
            raise ValueError(f"focal field must have shape {(setup.n_fft, setup.n_fft)}, got {e.shape}")
        inten = np.abs(e) ** 2 * (setup.pad**2 / setup.n_pix**2)
        iy, ix = trap_bins(setup, traps)
        m = setup.n_fft
        if self.blur_bins > 0:
            r = int(math.ceil(3 * self.blur_bins))
            off = np.arange(-r, r + 1)
            g1 = np.exp(-0.5 * (off / self.blur_bins) ** 2)
            vals = np.empty(len(traps))
            for t, (a, b) in enumerate(zip(iy, ix)):
                ya, yb = max(a - r, 0), min(a + r + 1, m)
                xa, xb = max(b - r, 0), min(b + r + 1, m)
                wy, wx = g1[ya - a + r:yb - a + r], g1[xa - b + r:xb - b + r]
                w = wy[:, None] * wx[None, :]
                vals[t] = np.sum(w * inten[ya:yb, xa:xb]) / np.sum(w)
        else:
            vals = inten[iy, ix].copy()
        if self.rolloff:
            s = _sinc_1d(setup, self.fill_factor) ** 2
            vals = vals * s[iy] * s[ix]
        vals = vals * np.array([self.gain(int(i)) for i in traps.ids])
        if self.noise_rms > 0:
            src = rng if rng is not None else self._noise
            vals = vals + self.noise_rms * src.normal_array(len(traps))
        return np.maximum(vals, 0.0)
