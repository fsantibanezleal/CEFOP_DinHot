"""SLM device model: phase quantization, phase-response LUT, flicker, pixel crosstalk and the pixel-aperture envelope.

A missing device means the ideal one (``device=None`` in the callers): phase displayed exactly, point-sampled pixels,
no crosstalk. ``Device()`` with its defaults is different on purpose: a real pixelated SLM with square pixels of fill
factor 1, so the pixel-aperture envelope (below) is present; quantization, crosstalk, flicker and the LUT nonlinearity
are off.

- Crosstalk (physics-viz D2.1, READ from Schroff et al. 2023, Methods, "Pixel crosstalk modelling", Eq. 4 checked on the
  rendered page): each SLM pixel is ``upsample x upsample`` computational pixels and the phase, kept in ``[0, 2 pi)``,
  is convolved with ``K = F^-1 { exp[-(|kx|^q + |ky|^q) / sigma^q] }`` (fitted ``sigma = 1.24 px^-1``, ``q = 1.80``).
  UNVERIFIED: the dossier does not state the unit of ``k``. This implementation takes ``k`` in cycles per SLM pixel
  (so the computational grid spans +-``upsample / 2``); the gap research must re-check it against the paper.
  The convolution is circular (FFT based), so the phase wraps at the border of the SLM.
- Pixel envelope (physics-viz D1.6, DERIVED there, not read from a source): a square pixel of width
  ``a = sqrt(fill_factor) p`` multiplies the focal field by ``sinc(a x / (lambda f)) sinc(a y / (lambda f))``, so the
  intensity falls to ``sinc^2(sqrt(fill) / 2) ~ 0.4`` at the edge of the unaliased window. The test compares it with a
  brute-force DFT of a pixel-sampled hologram. The envelope has unit value at the centre: the power lost to dead
  area (``1 - fill_factor``) is not applied; the input power is the power that reaches the active area.
- Quantization, LUT gamma and flicker: no primary source with measured effects was read (physics-viz D2.2, UNVERIFIED);
  they are computed device parameters. Order in ``displayed_phase``: wrap, quantize to ``2^b`` levels, nonlinear response
  ``2 pi (level phase / 2 pi)^gamma``, additive Gaussian flicker noise of rms ``flicker_rad`` per pixel, wrap.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .forward import fft_focal_field
from .geometry import Setup, input_amplitude, wrap_phase
from .rng import Rng

_TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class Device:
    """Non-idealities of the SLM. ``crosstalk`` is ``(sigma_per_px, q)`` or None; defaults are described above."""

    bit_depth: int | None = None
    crosstalk: tuple[float, float] | None = None
    upsample: int = 3
    fill_factor: float = 1.0
    flicker_rad: float = 0.0
    lut_gamma: float = 1.0

    def __post_init__(self) -> None:
        b = self.bit_depth
        if b is not None and (isinstance(b, bool) or not isinstance(b, int) or not 1 <= b <= 16):
            raise ValueError(f"bit_depth must be an integer in 1..16 or None, got {b!r}")
        if isinstance(self.upsample, bool) or not isinstance(self.upsample, int) or self.upsample < 1:
            raise ValueError(f"upsample must be a positive integer, got {self.upsample!r}")
        if not (math.isfinite(self.fill_factor) and 0 < self.fill_factor <= 1):
            raise ValueError(f"fill_factor must be in (0, 1], got {self.fill_factor!r}")
        if not (math.isfinite(self.flicker_rad) and self.flicker_rad >= 0):
            raise ValueError(f"flicker_rad must be finite and >= 0, got {self.flicker_rad!r}")
        if not (math.isfinite(self.lut_gamma) and self.lut_gamma > 0):
            raise ValueError(f"lut_gamma must be finite and > 0, got {self.lut_gamma!r}")
        if self.crosstalk is not None:
            if len(self.crosstalk) != 2:
                raise ValueError("crosstalk must be (sigma_per_px, q)")
            sigma, q = self.crosstalk
            if not (math.isfinite(sigma) and sigma > 0 and math.isfinite(q) and q > 0):
                raise ValueError(f"crosstalk sigma and q must be finite and positive, got {self.crosstalk!r}")


def quantize(phi: np.ndarray, bit_depth: int) -> np.ndarray:
    """Round the phase (wrapped to ``[0, 2 pi)``) to the nearest of ``2^bit_depth`` equally spaced levels."""
    if isinstance(bit_depth, bool) or not isinstance(bit_depth, int) or not 1 <= bit_depth <= 16:
        raise ValueError(f"bit_depth must be an integer in 1..16, got {bit_depth!r}")
    levels = 1 << bit_depth
    k = np.floor(wrap_phase(phi) / _TWO_PI * levels + 0.5).astype(np.int64) % levels
    return k * (_TWO_PI / levels)


def displayed_phase(phi: np.ndarray, device: Device, rng: Rng | None) -> np.ndarray:
    """The phase the device really shows (module docstring order). ``rng`` is required only if ``flicker_rad > 0``."""
    p = np.asarray(phi, dtype=np.float64)
    if not np.all(np.isfinite(p)):
        raise ValueError("phi contains NaN or infinite values")
    p = wrap_phase(p)
    if device.bit_depth is not None:
        p = quantize(p, device.bit_depth)
    if device.lut_gamma != 1.0:
        p = _TWO_PI * (p / _TWO_PI) ** device.lut_gamma
    if device.flicker_rad > 0:
        if rng is None:
            raise ValueError("an rng is required when flicker_rad > 0 (ADR-0054: no hidden randomness)")
        p = p + device.flicker_rad * rng.normal_array(p.size).reshape(p.shape)
    return wrap_phase(p)


def _transfer(n_up: int, sigma: float, q: float, upsample: int) -> np.ndarray:
    k = np.abs(np.fft.fftfreq(n_up, d=1.0 / upsample))          # cycles per SLM pixel
    return np.exp(-((k[:, None] ** q + k[None, :] ** q) / sigma**q))


def crosstalk_kernel(n_up: int, sigma: float, q: float, upsample: int = 3) -> np.ndarray:
    """The spatial kernel ``K = F^-1 { exp[-(|kx|^q + |ky|^q) / sigma^q] }`` on an ``n_up x n_up`` upsampled grid.

    Real, symmetric, origin at index (0, 0), sum 1. Circular convolution with it equals multiplying by the transfer
    function in the Fourier domain (Schroff et al. 2023 Eq. 4; unit of k: see the module docstring).
    """
    if isinstance(n_up, bool) or not isinstance(n_up, int) or n_up < 1:
        raise ValueError("n_up must be a positive integer")
    if not (math.isfinite(sigma) and sigma > 0 and math.isfinite(q) and q > 0):
        raise ValueError("sigma and q must be finite and positive")
    return np.real(np.fft.ifft2(_transfer(n_up, sigma, q, upsample)))


def _upsample(phi: np.ndarray, device: Device) -> np.ndarray:
    phi = np.asarray(phi, dtype=np.float64)
    if phi.ndim != 2 or phi.shape[0] != phi.shape[1]:
        raise ValueError("phi must be a square 2D array")
    return np.kron(phi, np.ones((device.upsample, device.upsample)))


def crosstalk(phi: np.ndarray, device: Device) -> np.ndarray:
    """Upsample each pixel to ``upsample x upsample`` samples and blur with the crosstalk kernel (if the device has one)."""
    up = _upsample(phi, device)
    if device.crosstalk is None:
        return up
    h = _transfer(up.shape[0], *device.crosstalk, device.upsample)
    return np.real(np.fft.ifft2(np.fft.fft2(up) * h))


def crosstalk_adjoint(g: np.ndarray, device: Device) -> np.ndarray:
    """Adjoint of ``crosstalk``: gradient with respect to ``phi`` given the gradient ``g`` with respect to its output.

    Convolution with the reversed kernel (conjugate transfer function; the kernel is symmetric, so it equals the
    kernel), then summation over each ``upsample x upsample`` block. Satisfies ``<crosstalk(phi), g> = <phi, adjoint(g)>``.
    """
    g = np.asarray(g, dtype=np.float64)
    u = device.upsample
    if g.ndim != 2 or g.shape[0] != g.shape[1] or g.shape[0] % u:
        raise ValueError(f"g must be a square array whose side is a multiple of upsample ({u}), got {g.shape}")
    if device.crosstalk is not None:
        h = _transfer(g.shape[0], *device.crosstalk, u)
        g = np.real(np.fft.ifft2(np.fft.fft2(g) * np.conj(h)))
    n = g.shape[0] // u
    return g.reshape(n, u, n, u).sum(axis=(1, 3))


def _sinc_1d(setup: Setup, fill_factor: float) -> np.ndarray:
    k = np.arange(setup.n_fft) - setup.n_fft // 2
    return np.sinc(math.sqrt(fill_factor) * k / setup.n_fft)


def pixel_envelope(setup: Setup, device: Device) -> np.ndarray:
    """Intensity envelope of the square pixel aperture on the centred focal grid, ``sinc^2 x sinc^2``, 1 at the centre.

    DERIVED (physics-viz D1.6), validated against a brute-force DFT in the tests. Shape ``(n_fft, n_fft)``.
    """
    s = _sinc_1d(setup, device.fill_factor) ** 2
    return s[:, None] * s[None, :]


def _upsampled_focal_field(disp: np.ndarray, setup: Setup, device: Device) -> np.ndarray:
    """Centred focal field (shape ``n_fft^2``) of the crosstalk-blurred, sample-and-hold upsampled hologram."""
    u, n, m = device.upsample, setup.n_pix, setup.n_fft
    mu = m * u
    phase = crosstalk(disp, device)
    amp = np.kron(input_amplitude(setup), np.ones((u, u)))
    padded = np.zeros((mu, mu), dtype=np.complex128)
    padded[: n * u, : n * u] = amp * np.exp(1j * phase)
    e = np.fft.fftshift(np.fft.fft2(padded, norm="ortho"))
    ramp = np.exp(2j * math.pi * ((n * u - 1) / 2.0) * (np.arange(mu) - mu // 2) / mu)
    e = e * ramp[:, None] * ramp[None, :]
    lo = mu // 2 - m // 2
    e = e[lo:lo + m, lo:lo + m] / u        # 2D orthonormal scaling over the finer grid carries a factor u
    # the sample-and-hold of u samples per pixel contributes the Dirichlet factor D(k); replace it by the pixel aperture
    k = np.arange(m) - m // 2
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.sin(math.pi * k / m) / (u * np.sin(math.pi * k / mu))
    d[m // 2] = 1.0
    swap = _sinc_1d(setup, device.fill_factor) / d
    return e * swap[:, None] * swap[None, :]


def device_focal_field(phi: np.ndarray, setup: Setup, device: Device, rng: Rng | None) -> np.ndarray:
    """Focal field (``n_fft x n_fft``, centred, same scaling as ``forward.fft_focal_field``) of what the device displays.

    Without crosstalk: the FFT of the displayed phase times the pixel-aperture field envelope. With crosstalk: the
    hologram is upsampled and blurred (``crosstalk``), transformed on the finer grid, cropped to the same window, and
    the sample-and-hold factor is exchanged for the pixel aperture, so the two paths agree exactly when the kernel is
    a delta. ``rng`` is needed only for flicker.
    """
    disp = displayed_phase(phi, device, rng)
    if disp.shape != (setup.n_pix, setup.n_pix):
        raise ValueError(f"phi must have shape {(setup.n_pix, setup.n_pix)}, got {disp.shape}")
    if device.crosstalk is None:
        e = fft_focal_field(disp, setup)
        s = _sinc_1d(setup, device.fill_factor)
        return e * s[:, None] * s[None, :]
    return _upsampled_focal_field(disp, setup, device)

