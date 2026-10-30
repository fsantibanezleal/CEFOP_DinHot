"""Forward models: the point-trap (direct sum) form and the zero-padded FFT form, plus propagation.

Conventions (all arrays indexed ``[iy, ix]``; the focal grid is ``n_fft x n_fft`` and centred, bin ``(0, 0)`` at index
``n_fft // 2``):

- Point-trap form (algorithms D1.0, Di Leonardo et al. 2007 eqs (1) to (4)):
  ``V_m = (1 / N_pix) sum_j A_j exp(i (phi_j - Delta_j^m))`` with
  ``Delta_j^m = (pi z_m / (lambda f^2)) (x_j^2 + y_j^2) + (2 pi / (lambda f)) (x_j x_m + y_j y_m) + l_m atan2(y_j, x_j)``
  and ``N_pix = n_pix^2``; ``A_j`` is normalised so that ``sum A_j^2 = N_pix``; ``I_m = |V_m|^2`` is the fraction of the
  input power in the peak of trap m.
- FFT form (physics-viz D1.1 and D1.2, Schroff et al. 2023 Methods eq (7)): the focal field is the Fraunhofer transform
  of the SLM field, evaluated by a zero-padded FFT with orthonormal scaling (so Parseval holds: ``sum |E|^2 = N_pix``).
  Pixel centres are at ``(j - (n_pix - 1) / 2) p``, so the FFT is multiplied by the linear phase that moves its origin
  to the optical axis; then at a trap on an FFT bin (z = 0, l = 0) ``V_m = E[bin] * pad / n_pix`` exactly (the factor is
  ``n_fft / N_pix``), which is what ``trap_fields_from_fft`` returns and the oracle tests compare to 1e-9.
- Angular spectrum (physics-viz D1.3, Schroff et al. 2023 Supplementary eqs (S2) to (S4)): transfer function
  ``H = exp(2 pi i (z / lambda) sqrt(1 - (lambda xi_x)^2 - (lambda xi_y)^2))`` for ``xi_x^2 + xi_y^2 < 1 / lambda^2``,
  0 otherwise (evanescent components removed). The band-limited variant of Matsushima and Shimobaba (2009) is PENDING
  the gap research (its formula was not readable); this plain form is valid for short distances.
"""
from __future__ import annotations

import math

import numpy as np

from .geometry import Setup, focal_bin_m, input_amplitude, slm_grid
from .traps import TrapSet, check_in_field


def _check_phi(phi: np.ndarray, setup: Setup) -> np.ndarray:
    phi = np.asarray(phi, dtype=np.float64)
    if phi.shape != (setup.n_pix, setup.n_pix):
        raise ValueError(f"phi must have shape {(setup.n_pix, setup.n_pix)}, got {phi.shape}")
    if not np.all(np.isfinite(phi)):
        raise ValueError("phi contains NaN or infinite values")
    return phi


def slm_field(phi: np.ndarray, setup: Setup) -> np.ndarray:
    """The complex SLM field ``A_j exp(i phi_j)`` (input amplitude of ``geometry.input_amplitude``)."""
    return input_amplitude(setup) * np.exp(1j * _check_phi(phi, setup))


def _separable_factors(setup: Setup, traps: TrapSet, idx: slice, sign: float):
    """Per-trap 1D factors ``exp(sign i (c_z x^2 + k x x_m))`` along x and y, shapes ``(c, n_pix)``."""
    lam, f = setup.wavelength_m, setup.focal_m
    c = (np.arange(setup.n_pix) - (setup.n_pix - 1) / 2.0) * setup.pitch_m
    cz = math.pi * traps.z_m[idx, None] / (lam * f**2)
    k = 2.0 * math.pi / (lam * f)
    gx = np.exp(sign * 1j * (cz * c[None] ** 2 + k * traps.x_m[idx, None] * c[None]))
    gy = np.exp(sign * 1j * (cz * c[None] ** 2 + k * traps.y_m[idx, None] * c[None]))
    return gx, gy


def _dense_delay(setup: Setup, traps: TrapSet, m: int) -> np.ndarray:
    """``Delta_j^m`` for the single trap index m on the full grid (used when a vortex is present)."""
    lam, f = setup.wavelength_m, setup.focal_m
    x, y = slm_grid(setup)
    d = (math.pi * traps.z_m[m] / (lam * f**2)) * (x**2 + y**2)
    d = d + (2.0 * math.pi / (lam * f)) * (x * traps.x_m[m] + y * traps.y_m[m])
    return d + traps.charge[m] * np.arctan2(y, x)


def _chunk_size(chunk: int | None) -> int:
    if chunk is None:
        return 256
    if chunk < 1:
        raise ValueError("chunk must be >= 1")
    return int(chunk)


def point_trap_projection(field: np.ndarray, setup: Setup, traps: TrapSet, chunk: int | None = None) -> np.ndarray:
    """``V_m = (1 / N_pix) sum_j f_j exp(-i Delta_j^m)`` for an arbitrary complex SLM field ``f`` (algorithms D1.0).

    Traps without a vortex use the separable form (a matrix product over chunks of traps, memory
    ``O(chunk * n_pix)``); traps with a vortex use the dense form, one trap at a time (a few ``n_pix^2`` temporaries). Raises ``OutOfFieldError`` for a trap outside the field of view.
    """
    check_in_field(setup, traps)
    field = np.asarray(field, dtype=np.complex128)
    if field.shape != (setup.n_pix, setup.n_pix) or not np.all(np.isfinite(field)):
        raise ValueError("field must be a finite complex array of shape (n_pix, n_pix)")
    out = np.empty(len(traps), dtype=np.complex128)
    plain = np.flatnonzero(traps.charge == 0)
    vort = np.flatnonzero(traps.charge != 0)
    n_pix2 = setup.n_pix**2
    step = _chunk_size(chunk)
    for s0 in range(0, len(plain), step):
        sel = plain[s0:s0 + step]
        gx, gy = _separable_factors(setup, traps, sel, -1.0)
        tmp = field @ gx.T                                   # (iy, m)
        out[sel] = np.einsum("mi,im->m", gy, tmp) / n_pix2
    for m in vort:  # dense path: one trap at a time, a few n_pix^2 temporaries
        out[m] = np.sum(field * np.exp(-1j * _dense_delay(setup, traps, m))) / n_pix2
    return out


def point_trap_fields(phi: np.ndarray, setup: Setup, traps: TrapSet, chunk: int | None = None) -> np.ndarray:
    """``V_m`` of the hologram ``phi`` (point-trap form, algorithms D1.0); see ``point_trap_projection``."""
    return point_trap_projection(slm_field(phi, setup), setup, traps, chunk)


def point_trap_backproject(coeffs: np.ndarray, setup: Setup, traps: TrapSet, chunk: int | None = None) -> np.ndarray:
    """The SLM field ``F_j = sum_m c_m exp(+i Delta_j^m)`` (no ``1 / N_pix``): the adjoint direction of the projection.

    It satisfies ``sum_m c_m conj(V_m(f)) = vdot(f, F) / N_pix``. Weighted Gerchberg-Saxton updates take its argument.
    """
    check_in_field(setup, traps)
    coeffs = np.asarray(coeffs, dtype=np.complex128)
    if coeffs.shape != (len(traps),) or not np.all(np.isfinite(coeffs)):
        raise ValueError(f"coeffs must be a finite vector of length {len(traps)}")
    n = setup.n_pix
    out = np.zeros((n, n), dtype=np.complex128)
    plain = np.flatnonzero(traps.charge == 0)
    vort = np.flatnonzero(traps.charge != 0)
    step = _chunk_size(chunk)
    for s0 in range(0, len(plain), step):
        sel = plain[s0:s0 + step]
        gx, gy = _separable_factors(setup, traps, sel, +1.0)
        out += (gy * coeffs[sel, None]).T @ gx
    for m in vort:
        out += coeffs[m] * np.exp(1j * _dense_delay(setup, traps, m))
    return out


def _ramp(setup: Setup) -> np.ndarray:
    """Phase ramp ``exp(+2 pi i c k / n_fft)`` along one focal axis (k = -n_fft/2 .. n_fft/2 - 1)."""
    m = setup.n_fft
    k = np.arange(m) - m // 2
    return np.exp(2j * math.pi * ((setup.n_pix - 1) / 2.0) * k / m)


def fft_focal_field(phi: np.ndarray, setup: Setup) -> np.ndarray:
    """Centred, zero-padded, orthonormal FFT of the SLM field: shape ``(n_fft, n_fft)``, Parseval holds."""
    m = setup.n_fft
    padded = np.zeros((m, m), dtype=np.complex128)
    padded[: setup.n_pix, : setup.n_pix] = slm_field(phi, setup)
    e = np.fft.fftshift(np.fft.fft2(padded, norm="ortho"))
    r = _ramp(setup)
    return e * r[:, None] * r[None, :]


def fft_inverse(e: np.ndarray, setup: Setup) -> np.ndarray:
    """Inverse of ``fft_focal_field`` back to the SLM grid (complex field, cropped to ``n_pix x n_pix``)."""
    e = _check_focal(e, setup)
    r = np.conj(_ramp(setup))
    full = np.fft.ifft2(np.fft.ifftshift(e * r[:, None] * r[None, :]), norm="ortho")
    return full[: setup.n_pix, : setup.n_pix]


def _check_focal(e: np.ndarray, setup: Setup) -> np.ndarray:
    e = np.asarray(e, dtype=np.complex128)
    if e.shape != (setup.n_fft, setup.n_fft):
        raise ValueError(f"focal field must have shape {(setup.n_fft, setup.n_fft)}, got {e.shape}")
    return e


def trap_bins(setup: Setup, traps: TrapSet) -> tuple[np.ndarray, np.ndarray]:
    """Array indices ``(iy, ix)`` of the FFT bin nearest to each trap (raises ``OutOfFieldError`` if outside)."""
    check_in_field(setup, traps)
    b = focal_bin_m(setup)
    h = setup.n_fft // 2
    return np.rint(traps.y_m / b).astype(int) + h, np.rint(traps.x_m / b).astype(int) + h


def trap_fields_from_fft(e: np.ndarray, setup: Setup, traps: TrapSet) -> np.ndarray:
    """``V_m`` read from the FFT field at the bin nearest to each trap: ``E[bin] * pad / n_pix``.

    Equal to the point-trap value for traps on bins with z = 0 and no vortex; for others it is the sampled value.
    """
    e = _check_focal(e, setup)
    iy, ix = trap_bins(setup, traps)
    return e[iy, ix] * (setup.pad / setup.n_pix)


def _transfer(setup: Setup, dz_m: float) -> np.ndarray:
    """Transfer function ``H`` on the focal grid (FFT frequency order), wavelength in the medium ``lambda / n_imm``."""
    m = setup.n_fft
    lam = setup.wavelength_m / setup.n_imm
    xi = np.fft.fftfreq(m, d=focal_bin_m(setup))
    s = (lam * xi[:, None]) ** 2 + (lam * xi[None, :]) ** 2
    prop = s < 1.0
    kz = np.sqrt(np.where(prop, 1.0 - s, 0.0))
    return np.where(prop, np.exp(2j * math.pi * (dz_m / lam) * kz), 0.0)


def angular_spectrum(e: np.ndarray, dz_m: float, setup: Setup) -> np.ndarray:
    """Propagate a focal-plane field by ``dz_m`` with the plain angular-spectrum transfer function (module docstring).

    The grid spacing is the focal bin; the wavelength is ``lambda / n_imm``. Evanescent components are set to zero, so
    for ``dz_m = 0`` the field is band-limited to the propagating disc. Band-limited ASM: pending the gap research.
    """
    e = _check_focal(e, setup)
    if not math.isfinite(dz_m):
        raise ValueError("dz_m must be finite")
    spec = np.fft.fft2(np.fft.ifftshift(e)) * _transfer(setup, dz_m)
    return np.fft.fftshift(np.fft.ifft2(spec))


def axial_cut(
    phi: np.ndarray,
    setup: Setup,
    *,
    x_m: float | None = None,
    y_m: float | None = None,
    z_range_m: tuple[float, float],
    nz: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Intensity slice through the focal volume: ``y_m`` given gives the xz plane, ``x_m`` given the yz plane.

    Returns ``(intensity[nz, n_fft], z_axis_m, lateral_axis_m)`` with intensity in the units of ``I_m = |V|^2``
    (``|E|^2 pad^2 / N_pix``). The focal-plane field of the FFT form is propagated to each z by the angular spectrum;
    this assumes the scalar, paraxial model (the lens is parabolic and the field at z = 0 is the Fraunhofer field), so
    the z position of a displaced trap is exact only for ``|z| << f``. Only the requested row is synthesised.
    """
    if (x_m is None) == (y_m is None):
        raise ValueError("give exactly one of x_m (yz plane) or y_m (xz plane)")
    if isinstance(nz, bool) or int(nz) != nz or nz < 1:
        raise ValueError("nz must be a positive integer")
    z0, z1 = z_range_m
    if not (math.isfinite(z0) and math.isfinite(z1)):
        raise ValueError("z_range_m must be finite")
    pos = y_m if y_m is not None else x_m
    if not math.isfinite(pos):
        raise ValueError("the cut position must be finite")
    m = setup.n_fft
    b = focal_bin_m(setup)
    k_fix = int(round(pos / b))
    if abs(k_fix) >= m // 2:
        raise ValueError("the cut lies outside the focal grid")
    e = fft_focal_field(phi, setup)
    spec = np.fft.fft2(np.fft.ifftshift(e))           # [ky, kx] in FFT frequency order
    if y_m is None:
        spec = spec.T                                 # make the fixed axis the first
    z = np.linspace(z0, z1, int(nz))
    lam = setup.wavelength_m / setup.n_imm
    xi = np.fft.fftfreq(m, d=b)
    s = (lam * xi[:, None]) ** 2 + (lam * xi[None, :]) ** 2
    prop = s < 1.0
    kz = np.sqrt(np.where(prop, 1.0 - s, 0.0))
    sel = np.exp(2j * math.pi * np.fft.fftfreq(m) * k_fix)   # row selector along the fixed axis
    out = np.empty((int(nz), m))
    scale = setup.pad**2 / setup.n_pix**2
    for i, zi in enumerate(z):
        h = np.where(prop, np.exp(2j * math.pi * (zi / lam) * kz), 0.0)
        row = np.einsum("a,ab->b", sel, spec * h) / m
        out[i] = np.abs(np.fft.fftshift(np.fft.ifft(row))) ** 2 * scale
    lateral = (np.arange(m) - m // 2) * b
    return out, z, lateral
