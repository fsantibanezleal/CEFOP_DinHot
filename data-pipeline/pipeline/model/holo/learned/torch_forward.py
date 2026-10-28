"""PyTorch re-implementation of the forward model, for training the two learned slots only (needs torch; the engine and the
method modules never import this file). Checked against the numpy engine in ``tests/learned/test_torch_forward.py``.

Coordinates of the model slots (the unit system the networks use, independent of lambda, f and the pixel pitch):

- ``kx, ky``: trap position in FFT bins (one bin is ``lambda f / (pad N p)``, the resolution cell is ``pad`` bins);
- ``Z``: trap depth in units of the SLM-limited Rayleigh range ``z_R = lambda f^2 / (pi R^2)`` with ``R = N p / 2`` (the
  Rayleigh range of the beam the SLM aperture focuses). With it the quadratic phase of the point-trap delay at the aperture
  edge is exactly ``Z`` radians, so the delay is ``Delta_j^m = Z (cx^2 + cy^2) / (N/2)^2 + 2 pi (kx cx + ky cy) / (pad N)``
  with ``cx, cy`` the pixel offsets from the centre, and the forward model does not depend on lambda, f or p at all.

``project`` / ``backproject`` are the separable point-trap form of ``core.forward`` (vortex charges are not modelled: the
slots do not take them). ``unrolled_wgs`` is the phase-fixed WGS rule of M07 (``_gs.rule_wgs_fixed``) with differentiable
steps, used as the training loss of the warm start. ``focal_intensity`` is the FFT form for pad 1 used by the cgh-net loss.
"""
from __future__ import annotations

import math

import torch

TINY = 1e-12


def pixel_axis(n_pix: int, device=None, dtype=torch.float32) -> torch.Tensor:
    return torch.arange(n_pix, device=device, dtype=dtype) - (n_pix - 1) / 2.0


def input_amplitude(n_pix: int, beam: str = "gaussian", waist_frac: float = 1.0, device=None) -> torch.Tensor:
    """``geometry.input_amplitude`` in torch: sum A^2 = n_pix^2."""
    if beam == "flat":
        return torch.ones(n_pix, n_pix, device=device)
    c = pixel_axis(n_pix, device, torch.float64)
    w = waist_frac * n_pix / 2.0
    a = torch.exp(-(c[None, :] ** 2 + c[:, None] ** 2) / w**2)
    return (a * math.sqrt(n_pix**2 / float((a**2).sum()))).float()


def _factors(kx, ky, z, n_pix: int, pad: int, sign: float):
    """Per-trap 1D factors ``exp(sign i (Z c^2 / (N/2)^2 + 2 pi k c / (pad N)))``, shapes ``(B, M, N)`` (x then y)."""
    c = pixel_axis(n_pix, kx.device, torch.float32)
    quad = z[..., None] * (c / (n_pix / 2.0)) ** 2
    lin = 2.0 * math.pi / (pad * n_pix)
    gx = torch.polar(torch.ones_like(quad), sign * (quad + lin * kx[..., None] * c))
    gy = torch.polar(torch.ones_like(quad), sign * (quad + lin * ky[..., None] * c))
    return gx, gy


def trap_factors(traps: torch.Tensor, n_pix: int, pad: int):
    """``(gx_minus, gy_minus)`` for the projection; the back-projection uses their conjugates."""
    return _factors(traps[..., 0], traps[..., 1], traps[..., 2], n_pix, pad, -1.0)


def project(field: torch.Tensor, gx: torch.Tensor, gy: torch.Tensor, n_pix: int) -> torch.Tensor:
    """``V_m = (1 / N^2) sum_j f_j exp(-i Delta_j^m)`` for the complex SLM field ``(B, N, N)``; returns ``(B, M)``."""
    tmp = torch.einsum("byx,bmx->bym", field, gx)
    return torch.einsum("bym,bmy->bm", tmp, gy) / float(n_pix**2)


def backproject(coeffs: torch.Tensor, gx: torch.Tensor, gy: torch.Tensor) -> torch.Tensor:
    """``F_j = sum_m c_m exp(+i Delta_j^m)``, shape ``(B, N, N)`` (the conjugates of the projection factors)."""
    return torch.einsum("bmy,bmx->byx", gy.conj() * coeffs[..., None], gx.conj())


def rel_std_pct(v: torch.Tensor, weights: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """``100 std(I / w) / mean(I / w)`` over the valid traps (population std, as ``core.metrics.rel_std``); shape ``(B,)``."""
    i = (v.abs() ** 2) / weights.clamp_min(TINY)
    n = mask.sum(-1).clamp_min(1.0)
    mean = (i * mask).sum(-1) / n
    var = (((i - mean[:, None]) ** 2) * mask).sum(-1) / n
    return 100.0 * torch.sqrt(var + 1e-20) / mean.clamp_min(TINY)


def efficiency(v: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    return ((v.abs() ** 2) * mask).sum(-1)


def sr_hologram(theta: torch.Tensor, amp: torch.Tensor, gx, gy) -> torch.Tensor:
    """``arg sum_m a_m exp(i (Delta^m + theta_m))`` (the SR form of ``_common.sr_start`` with given phases), ``(B, N, N)``."""
    c = amp * torch.polar(torch.ones_like(theta), theta)
    return torch.angle(backproject(c, gx, gy))


def unrolled_wgs(theta, traps, mask, n_pix: int, pad: int, steps: int, n_fix: int = 12, beam="gaussian", waist_frac=1.0):
    """Start from the SR hologram of ``theta`` and run ``steps`` iterations of M07 (point form). Returns the list of
    ``(rel_std_pct, efficiency)`` after iteration 0 (the start), 1, ..., ``steps``."""
    amp_in = input_amplitude(n_pix, beam, waist_frac, traps.device)
    gx, gy = trap_factors(traps, n_pix, pad)
    w_t = traps[..., 3]
    a = torch.sqrt(w_t.clamp_min(TINY)) * mask
    n = mask.sum(-1, keepdim=True).clamp_min(1.0)
    phi = sr_hologram(theta, a, gx, gy)
    v = project(amp_in * torch.polar(torch.ones_like(phi), phi), gx, gy, n_pix)
    out = [(rel_std_pct(v, w_t, mask), efficiency(v, mask))]
    g = mask.clone()
    psi = None
    for k in range(1, steps + 1):
        b = ((v.abs() / a.clamp_min(TINY)).clamp_min(TINY)) * mask + (1 - mask)
        mean_b = (b * mask).sum(-1, keepdim=True) / n
        g = g * mean_b / b
        if k < n_fix:
            ph = torch.angle(v)
        elif k == n_fix:
            ph = psi = torch.angle(v)
        else:
            ph = psi
        c = g * a * torch.polar(torch.ones_like(ph), ph) * mask
        phi = torch.angle(backproject(c, gx, gy))
        v = project(amp_in * torch.polar(torch.ones_like(phi), phi), gx, gy, n_pix)
        out.append((rel_std_pct(v, w_t, mask), efficiency(v, mask)))
    return out


def focal_intensity(phi: torch.Tensor, amp_in: torch.Tensor) -> torch.Tensor:
    """Centred focal intensity of the phase mask ``phi`` (B, N, N) on the pad-1 grid (n_fft = N), normalised to unit sum.

    ``|fftshift(fft2(A exp(i phi)))|^2`` with orthonormal scaling; by Parseval the sum is the input power, so dividing by it
    gives the unit-energy intensity the target is compared with. The linear phase of ``fft_focal_field`` only moves the
    origin of the phase, never the modulus, so it is omitted.
    """
    e = torch.fft.fftshift(torch.fft.fft2(amp_in * torch.polar(torch.ones_like(phi), phi), norm="ortho"), dim=(-2, -1))
    i = e.abs() ** 2
    return i / i.sum(dim=(-2, -1), keepdim=True)


def accuracy(target_amp: torch.Tensor, inten: torch.Tensor) -> torch.Tensor:
    """``AC = 2 sum(T I) / (sum T^2 + sum I^2)`` with ``T = a^2`` (unit-sum target intensity) and ``I`` the unit-sum
    reconstruction; 1 iff equal, in [0, 1]. DeepCGH's exact accuracy formula was not read (UNVERIFIED); this definition is
    applied identically to the network, GS and the loss."""
    t = target_amp**2
    t = t / t.sum(dim=(-2, -1), keepdim=True)
    num = 2.0 * (t * inten).sum(dim=(-2, -1))
    den = (t**2).sum(dim=(-2, -1)) + (inten**2).sum(dim=(-2, -1))
    return num / den


# ---------------------------------------------------------------------------------------------- multi-plane (cgh-net)
Z_PLANES = (-8.0, 0.0, 8.0)   # plane depths in SLM-limited Rayleigh ranges (edge defocus of 8 rad), the three planes of cgh-net


def lens_phase(n_pix: int, z: float, device=None) -> torch.Tensor:
    """``Z (cx^2 + cy^2) / (N/2)^2`` (N, N): the quadratic delay of a plane at depth ``z`` (paraxial lens term of the point-trap model)."""
    c = pixel_axis(n_pix, device, torch.float32)
    return z * (c[None, :] ** 2 + c[:, None] ** 2) / (n_pix / 2.0) ** 2


def plane_intensities(phi: torch.Tensor, amp_in: torch.Tensor, z_planes=Z_PLANES) -> torch.Tensor:
    """Unit-sum focal intensity of the mask ``phi`` (B, N, N) in each plane: ``(B, P, N, N)``. The field of plane ``z`` is the
    centred orthonormal FFT of ``A exp(i (phi - lens_phase(z)))``, which is ``point_trap_fields``' delay ``exp(-i Delta)`` for a trap
    at depth ``z`` (checked in the tests); with pad 1 each plane carries the whole input power."""
    n = phi.shape[-1]
    out = []
    for z in z_planes:
        out.append(focal_intensity(phi - lens_phase(n, z, phi.device), amp_in))
    return torch.stack(out, 1)


def volume_accuracy(target_amp: torch.Tensor, inten: torch.Tensor) -> torch.Tensor:
    """Mean over the planes of the per-plane AC (``accuracy``); ``(B, P, N, N)`` inputs, ``(B,)`` output."""
    return accuracy(target_amp, inten).mean(1)
