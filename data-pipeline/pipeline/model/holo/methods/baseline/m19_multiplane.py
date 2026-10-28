r"""M19: volumetric 3D Gerchberg-Saxton with the Ewald-sphere constraint (Whyte and Courtial 2005).

Source (R2 D3.2, Whyte and Courtial, New J. Phys. 7, 117, https://doi.org/10.1088/1367-2630/7/1/117, Eqs. (1) to (7),
author PDF read): 3D GS adapted from Shabtay 2003 deals with two VOLUMES, a real-space field and its k-space field, a 3D
Fourier pair; it is not plane-by-plane propagation. The k-space constraint is the Ewald sphere
$k_0^2 = k_x^2 + k_y^2 + k_z^2$ with $k_z > 0$; in the discrete implementation, for each $(k_x, k_y)$ only the $k_z$ element
nearest to $\sqrt{k_0^2 - k_x^2 - k_y^2}$ carries the field, all others are zero (a hemisphere one element thick). The
real-space volume carries the target. One iteration:
$$K[k_x, k_y, k_z^{\rm sphere}] = A_j e^{i\phi_j},\qquad U = \mathcal F_{3D} K,\qquad
U' = a_m e^{i \arg U}\ \text{at the target voxels, } 0 \text{ elsewhere},\qquad \phi_j = \arg\,(\mathcal F_{3D}^{-1} U')[k_x, k_y, k_z^{\rm sphere}]$$
and the hologram is the k-space phase on the sphere projected onto the SLM plane (their Fig. 1, Section 5.1); the SLM
amplitude is reset to the beam. Targets are point voxels (one per trap, weight $a_m = \sqrt{w_m}$).

Mapping to the DinHot engine (DERIVED here): SLM pixel $j$ is the lateral frequency $\xi = (x_j, y_j) / (\lambda f)$; the
lateral voxel is one FFT bin times ``pad`` ($dx = \lambda f / (n_{pix} p)$), so a trap at $x_m$ sits on voxel
$\mathrm{round}(x_m / dx)$; in $z$ the voxel pitch is ``dz_m`` and the carrier $k_0 z$ is removed (baseband), so the sphere
element is $i_z = \mathrm{round}\big(n_z\, dz\,(1 - \sqrt{1 - s})/\lambda_m\big)$ with $s = (\lambda_m \xi)^2$ and
$\lambda_m = \lambda / n_{imm}$, which in the paraxial limit is $\pi z \rho^2 / (\lambda f^2)$, the lens term of the
point-trap model. The reported trap fields are the point-trap model of the voxel-snapped traps (an independent
evaluation: ``fields`` equals ``core.forward.point_trap_fields(phi, setup, meta['snapped'])``).

Grid limits at DinHot sizes (256 x 256 pixels): the volume is $256 \times 256 \times n_z$ complex128, 33.6 MB for
$n_z = 32$ (default: the next power of two of at least 32 and 8 times the largest plane index); one iteration is two 3D FFTs
(about 0.3 s at $n_z = 32$). The rounding of the sphere element limits the axial placement: the phase error at depth $z$
is about $\pi z / (n_z\, dz)$ rad (0.05 rad at 40 mm, $n_z\, dz = 1.28$ m). The z extent $n_z\, dz$ is a period: the
sphere elements wrap modulo $n_z$ at the corners of the square SLM (periodic replicas of the volume, $n_z\, dz$ apart).
Axial resolution is set by the aperture: the depth of field is about $2\lambda/NA^2$ with
$NA = n_{pix}\, p / (2 f)$ (about 40 mm here), so planes closer than that cannot be told apart by any hologram.
Defaults: ``dz_m`` = smallest gap between the distinct plane depths of the target; ``nz`` as above.
UNVERIFIED: the paper reports the experimental match as weak (secondary, not read); no per-plane weighting is in the
paper, so none is applied.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ...core.forward import point_trap_fields
from ...core.geometry import focal_bin_m, input_amplitude, slm_grid
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ._common import Recorder, amp_targets, require_kinds, sr_start

SPEC = MethodSpec(id="M19", name="Volumetric 3D GS (multi-plane)", family="GS", lane="both",
                  targets=("traps",), dims=(3,))


def _next_pow2(n: int) -> int:
    return 1 << max(0, int(n - 1).bit_length())


def _plan(setup, traps: TrapSet, dz_m, nz):
    """Voxel indices of the traps, the snapped trap set, ``dz`` and ``nz``."""
    zs = np.unique(np.round(traps.z_m, 12))
    if dz_m is None:
        if len(zs) < 2:
            raise ValueError("a target on a single depth needs dz_m (the axial voxel pitch in metres)")
        dz_m = float(np.min(np.diff(zs)))
    if not (math.isfinite(dz_m) and dz_m > 0):
        raise ValueError(f"dz_m must be finite and positive, got {dz_m!r}")
    iz = np.rint(traps.z_m / dz_m).astype(int)
    if nz is None:
        nz = _next_pow2(max(32, 8 * int(np.abs(iz).max()) + 1))
    if nz < 2 * int(np.abs(iz).max()) + 1:
        raise ValueError(f"nz = {nz} cannot hold the plane indices up to {int(np.abs(iz).max())}")
    n = setup.n_pix
    dx = setup.pad * focal_bin_m(setup)
    ix, iy = np.rint(traps.x_m / dx).astype(int), np.rint(traps.y_m / dx).astype(int)
    if np.abs(ix).max() >= n // 2 or np.abs(iy).max() >= n // 2:
        raise ValueError("a trap lies outside the lateral voxel grid")
    keys = set(zip(ix.tolist(), iy.tolist(), iz.tolist()))
    if len(keys) != len(traps):
        raise ValueError("two traps fall on the same voxel; use a finer target or a smaller dz_m")
    snapped = TrapSet(replace(t, x_m=float(a * dx), y_m=float(b * dx), z_m=float(c * dz_m))
                      for t, a, b, c in zip(traps, ix, iy, iz))
    return ix, iy, iz, snapped, float(dz_m), int(nz)


def _sphere_index(setup, dz_m: float, nz: int) -> np.ndarray:
    """``i_z`` of every SLM pixel (mod ``nz``): the sphere element nearest to the baseband ``k_z``."""
    x, y = slm_grid(setup)
    lam_m = setup.wavelength_m / setup.n_imm
    s = (lam_m * np.hypot(x, y) / (setup.wavelength_m * setup.focal_m)) ** 2
    if np.any(s >= 1.0):
        raise ValueError("the SLM aperture exceeds the propagating cone")
    return np.rint(nz * dz_m * (1.0 - np.sqrt(1.0 - s)) / lam_m).astype(np.int64) % nz


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, dz_m: float | None = None,
        nz: int | None = None) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    traps = target.traps
    n = setup.n_pix
    ix, iy, iz, snapped, dz, nz = _plan(setup, traps, dz_m, nz)
    zsph = _sphere_index(setup, dz, nz)
    jy, jx = np.indices((n, n))
    kk = np.rint(np.fft.fftfreq(n) * n).astype(int)
    ramp = np.exp(2j * math.pi * ((n - 1) / 2.0) * kk / n)       # puts the lateral origin on the optical axis
    amp = input_amplitude(setup)
    a_m = amp_targets(traps)
    tz, ty, tx = iz % nz, iy % n, ix % n
    rec = Recorder(budget, snapped.weight)
    if init is None:
        phi = sr_start(setup, snapped, rng)
    else:
        phi = np.asarray(init, dtype=np.float64)
        if phi.shape != (n, n) or not np.all(np.isfinite(phi)):
            raise ValueError(f"init must be a finite array of shape {(n, n)}")
        phi = phi.copy()
    k = 0
    while True:
        k += 1
        vol = np.zeros((nz, n, n), dtype=np.complex128)
        vol[zsph, jy, jx] = amp * np.exp(1j * phi)
        u = np.fft.fftn(vol, norm="ortho") * ramp[None, :, None] * ramp[None, None, :]
        ut = np.zeros_like(u)
        uv = u[tz, ty, tx]
        ut[tz, ty, tx] = a_m * np.where(np.abs(uv) > 1e-300, uv / np.maximum(np.abs(uv), 1e-300), 1.0)
        back = np.fft.ifftn(ut / (ramp[None, :, None] * ramp[None, None, :]), norm="ortho")
        phi = np.angle(back[zsph, jy, jx])
        v = point_trap_fields(phi, setup, snapped)
        rec.add(k, v)
        if rec.done(k):
            break
    return Result(phi=phi, history=rec.history, fields=v,
                  meta={"method": SPEC.id, "snapped": snapped, "dz_m": dz, "nz": nz, "iterations": k})
