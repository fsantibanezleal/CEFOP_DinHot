r"""M18 optimal-transport initialized MRAF (Swan et al. 2024; Torchylo et al. 2025; algorithms dossier D2.4).

Sources: Swan, Torchylo, Van de Graaff, Rudolph, Hogan, arXiv 2408.17025 (S24 of the dossier): under the stationary
phase approximation the SLM phase satisfies the Monge-Ampere equation
``G^2(\nabla\phi(x)) \det(\nabla^2\phi(x)) = g^2(x)`` with ``g^2`` the input intensity and ``G^2`` the target intensity;
the quadratic-cost optimal-transport (OT) map ``\gamma`` between them (Sinkhorn, ``epsilon = 0.001``) is integrated,
``\phi(x) = \int \gamma(s).ds``, and seeds GS or MRAF. Their Table 1 (six targets): MRAF error 1.5 to 3.9 percent
with efficiency 18 to 45 percent; with OT initialization 0.17 to 0.96 percent with efficiency 53 to 85 percent.
Torchylo, Swan, Tellez, Hogan, arXiv 2512.19072 (S25): the dual form with a separable cost needs ``O(N)`` memory: the
plan is ``\Gamma = u\, K\, v`` with ``K = K_x \otimes K_y`` and the updates (dossier D2.4, ESTIMATED equation there)

.. math::
    u \leftarrow g^2 \oslash (\Lambda v \Lambda),\qquad v \leftarrow G^2 \oslash (\Lambda^T u \Lambda^T),

with the 1D kernels ``\Lambda`` evaluated as matrix products (``Ky @ v @ Kx.T``). Here: the cost is ``|x - y|^2 / 2``
with ``x`` the SLM pixel coordinate (pixel units) and ``y`` the focal bin coordinate; the stationary-phase relation is
``k = (n_fft / 2\pi)\, d\phi/dj`` (the Fourier phase ``2\pi k j / n_fft``), so ``\phi = (2\pi / n_fft)\Psi`` with
``\nabla\Psi = T`` the barycentric OT map in bins per pixel (the Brenier map is independent of the unit convention).
The kernel width is ``\sigma^2 = \epsilon\, n_fft^2`` bins squared (the dossier's ``\epsilon = 0.001`` is for coordinates
normalised by the image size; Torchylo's cost ``((j-L)^2+(k-M)^2)/(2 n^2)``). ``T`` is integrated to ``\Psi`` by a
least-squares Poisson solve on a mirror-extended grid (Frankot and Chellappa 1988: ``\hat\Psi = -i(k_x \hat T_x +
k_y \hat T_y)/|k|^2``; the dossier says only "integral of gamma.ds"), which is exact for a curl-free map and the
least-squares projection otherwise (the barycentric map of an entropic plan has a small curl).

MRAF (Pasienski and DeMarco 2008, Opt. Express 16, 2176; dossier D1.4, eq (1)): with signal region SR and noise
region NR,

.. math:: G^{(n)} = \left\{ m\, \sqrt{I_0}\big|_{SR} + (1-m)\, |E^{(n)}_{out}|\big|_{NR} \right\} e^{i \arg E^{(n)}_{out}},

then the inverse transform, the SLM amplitude reset to the beam, the phase kept. ``\sqrt{I_0}`` is the target amplitude
normalised to the total input power ``n_pix^2`` (UNVERIFIED: the dossier does not state the normalisation; rescaling
it to the current signal-region power instead drains the signal region); ``m = 0.4`` (Pasienski: 0.30 to 0.40), which
puts the fixed point near the efficiency solving ``\eta = m^2 / (m^2 + (1-m)^2 (1-\eta))``, which is 0.44 (measured
0.445 in the tests; Swan's MRAF rows: 0.18 to 0.45). The start is the OT phase; ``init`` replaces it (a random phase
is the baseline of the acceptance test: MRAF from a random start). Grids: live size 128 x 128 (64 pixel SLM padded 2),
baked 256 x 256 (128 pixel SLM padded 2). The model is the ideal device (``device`` is not part of M18's model).
"""
from __future__ import annotations

import math
import time

import numpy as np

from ...core.forward import fft_focal_field, fft_inverse
from ...core.geometry import Setup, input_amplitude
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _common as C

SPEC = MethodSpec(id="M18", name="Optimal-transport initialized MRAF", family="optimization", lane="baked",
                  targets=("field",), dims=(2,))
DEFAULT_MIX = 0.4
DEFAULT_EPS = 0.001
DEFAULT_OT_ITERATIONS = 200
_TINY = 1e-300


def sinkhorn_separable(a: np.ndarray, b: np.ndarray, xs: np.ndarray, ys: np.ndarray, sigma2: float,
                       iterations: int) -> dict:
    """Entropic OT between ``a`` (source, ``(ny, nx)``, unit sum) and ``b`` (target, ``(my, mx)``, unit sum).

    ``xs`` and ``ys`` hold the source and target 1D coordinates (the same for both axes of a square grid:
    ``xs`` of length ``nx``, ``ys`` of length ``mx``). The kernel is ``K = exp(-|x - y|^2 / (2 sigma2))``, separable as
    ``Kx (x) Ky``; ``u, v`` are the scalings (plan ``u K v``). Returns ``u, v`` and ``residual``, the L1 distance
    between the source marginal ``u (K v)`` and ``a`` after the last ``v`` update (the target marginal is exact).
    """
    kx = np.exp(-((xs[:, None] - ys[None, :]) ** 2) / (2.0 * sigma2))          # (nx, mx)
    ky = kx if a.shape[0] == a.shape[1] else None
    if ky is None:
        raise ValueError("a square source grid is required")
    v = np.where(b > 0, 1.0, 0.0)
    u = np.ones_like(a)
    for _ in range(int(iterations)):
        kv = ky @ v @ kx.T
        u = a / np.maximum(kv, _TINY)
        ktu = ky.T @ u @ kx
        v = np.where(b > 0, b / np.maximum(ktu, _TINY), 0.0)
    kv = ky @ v @ kx.T
    return {"u": u, "v": v, "kx": kx, "ky": ky, "kv": kv, "residual": float(np.abs(u * kv - a).sum())}


def barycentric_map(sol: dict, ys: np.ndarray, xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Barycentric projection ``T(x) = sum_y Gamma(x, y) y / sum_y Gamma(x, y)`` per axis, in target coordinate units.

    Where the plan has no mass (the kernel underflows) the map is the identity ``T(x) = x``.
    """
    v, kx, ky, kv = sol["v"], sol["kx"], sol["ky"], sol["kv"]
    gx = np.broadcast_to(ys[None, :], v.shape)           # target x coordinate per [my, mx]
    gy = np.broadcast_to(ys[:, None], v.shape)
    ok = kv > _TINY
    tx = np.where(ok, (ky @ (v * gx) @ kx.T) / np.maximum(kv, _TINY), xs[None, :])
    ty = np.where(ok, (ky @ (v * gy) @ kx.T) / np.maximum(kv, _TINY), xs[:, None])
    return tx, ty


def integrate_gradient(tx: np.ndarray, ty: np.ndarray) -> np.ndarray:
    """Least-squares potential ``Psi`` with ``d Psi / dx = tx`` and ``d Psi / dy = ty`` (axis 1 is x, axis 0 is y), unit
    pixel spacing, zero mean. Mirror-extended Poisson solve in the Fourier domain (Frankot and Chellappa)."""
    n0, n1 = tx.shape
    p = np.block([[tx, -tx[:, ::-1]], [tx[::-1, :], -tx[::-1, ::-1]]])
    q = np.block([[ty, ty[:, ::-1]], [-ty[::-1, :], -ty[::-1, ::-1]]])
    kx = 2.0 * math.pi * np.fft.fftfreq(2 * n1)
    ky = 2.0 * math.pi * np.fft.fftfreq(2 * n0)
    kk = kx[None, :] ** 2 + ky[:, None] ** 2
    kk[0, 0] = 1.0
    z = (-1j * kx[None, :] * np.fft.fft2(p) - 1j * ky[:, None] * np.fft.fft2(q)) / kk
    z[0, 0] = 0.0
    psi = np.real(np.fft.ifft2(z))[:n0, :n1]
    return psi - psi.mean()


def ot_phase(setup: Setup, amplitude: np.ndarray, mask: np.ndarray, *, eps: float = DEFAULT_EPS,
             iterations: int = DEFAULT_OT_ITERATIONS) -> tuple[np.ndarray, dict]:
    """The OT seed phase for a shaped target: ``phi = (2 pi / n_fft) Psi`` (module docstring); returns ``(phi, info)``."""
    n, m = setup.n_pix, setup.n_fft
    a = input_amplitude(setup) ** 2
    a = a / a.sum()
    b = np.where(mask, np.asarray(amplitude, dtype=np.float64) ** 2, 0.0)
    b = b / b.sum()
    xs = np.arange(n) - (n - 1) / 2.0
    ys = np.arange(m) - m // 2.0
    sol = sinkhorn_separable(a, b, xs, ys, eps * m * m, iterations)
    tx, ty = barycentric_map(sol, ys, xs)
    psi = integrate_gradient(tx, ty)
    phi = np.mod(2.0 * math.pi / m * psi, 2.0 * math.pi)
    return phi, {"residual": sol["residual"], "sigma_bins": math.sqrt(eps) * m}


def mraf(setup: Setup, amplitude: np.ndarray, mask: np.ndarray, phi0: np.ndarray, iterations: int, *,
         mix: float = DEFAULT_MIX, t0: float | None = None, deadline: float | None = None) -> tuple[np.ndarray, np.ndarray, list]:
    """MRAF from the phase ``phi0``; returns ``(phi, E, history)`` with one history entry per iteration."""
    t0 = time.perf_counter() if t0 is None else t0
    amp = np.asarray(amplitude, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool)
    a2 = float(np.sum(np.where(mask, amp**2, 0.0)))
    phi = np.asarray(phi0, dtype=np.float64)
    e = fft_focal_field(phi, setup)
    history: list = []
    for it in range(1, int(iterations) + 1):
        if C.expired(deadline):
            break
        target_amp = amp * math.sqrt(setup.n_pix**2 / a2)
        g = np.where(mask, mix * target_amp, (1.0 - mix) * np.abs(e)) * np.exp(1j * np.angle(e))
        phi = np.angle(fft_inverse(g, setup))
        e = fft_focal_field(phi, setup)
        history.append(C.field_history(it, e, amp, mask, t0))
    return np.mod(phi, 2.0 * math.pi), e, history


def run(setup: Setup, target: Target, *, device=None, budget: Budget, rng: Rng, init: np.ndarray | None = None,
        mix: float = DEFAULT_MIX, eps: float = DEFAULT_EPS, ot_iterations: int = DEFAULT_OT_ITERATIONS) -> Result:
    """OT seed (unless ``init`` is given) then ``budget.iterations`` MRAF iterations on a shaped-field target."""
    if target.kind != "field":
        raise ValueError("M18 supports shaped-field targets only (targets: 'field'); got traps")
    m = setup.n_fft
    if target.amplitude.shape != (m, m):
        raise ValueError(f"the target must be on the {m} x {m} focal grid (n_fft), got {target.amplitude.shape}")
    if not (0.0 < mix < 1.0):
        raise ValueError("mix must be in (0, 1)")
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    info: dict = {}
    if init is None:
        phi0, info = ot_phase(setup, target.amplitude, target.mask, eps=eps, iterations=ot_iterations)
        info["ot_time_s"] = time.perf_counter() - t0
    else:
        phi0 = C.start_phase(setup, rng, init)
    phi, e, history = mraf(setup, target.amplitude, target.mask, phi0, budget.iterations, mix=mix, t0=t0,
                           deadline=deadline)
    if not history:
        history = [C.field_history(0, e, target.amplitude, target.mask, t0)]
    return Result(phi=phi, history=history, fields=e,
                  meta={"ot_init": init is None, "mix": mix, "eps": eps, **info})
