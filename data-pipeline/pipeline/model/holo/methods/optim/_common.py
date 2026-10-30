"""Shared private machinery of the optimization methods (M09 to M13, M18) and the beyond methods (B1, B2, B4, B5).

Everything here is numpy only, with closed-form gradients (no autodiff: the TypeScript port needs the same formulas).

Conventions. For a real loss ``L`` of a complex array ``Z`` the *Wirtinger gradient* is ``G = dL/dZ*`` (half the
gradient with respect to the real part plus i times the gradient with respect to the imaginary part). For an
intensity loss ``L(I)`` with ``I = |Z|^2`` it is ``G = L'(I) Z``. If ``Z = Op(phi)`` is linear in the SLM field
``f_j = A_j exp(i phi_j)``, then (chain rule, Chakravarthula et al. 2019 eqs (5) to (8))

    dL/dphi_j = 2 Re( i f_j conj( (Op^H G)_j ) ),

where ``Op^H`` is the adjoint of the linear operator ``f -> Z``. ``FocalForward`` and ``TrapForward`` implement
``Op`` and ``Op^H`` for the ideal FFT form, the point-trap form and the device model of ``core/device.py``.

Device straight-through. The displayed phase of a device (quantization, LUT) is applied in the forward pass
(``displayed_phase``); the backward pass treats it as the identity (a straight-through estimator). Flicker is a random
effect of the display and is not part of an optimization model, so it is dropped.

Cost functions follow Harte et al. 2014 (algorithms dossier D2.2): ``C_t = sum (I - s T)^t`` over the signal region,
normalised by ``sum (s T)^t`` so that the value is scale free (the minimizers are unchanged), ``t`` even. The target
intensity ``T`` carries the requested efficiency: ``sum T = efficiency`` (traps: fraction of the input power; fields:
fraction of ``n_pix^2`` in the signal region, Parseval). ``s`` is a fixed multiplier (1) unless a method refits it.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
import time
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from ...core.device import Device, crosstalk, crosstalk_adjoint, displayed_phase
from ...core.forward import (
    fft_focal_field, fft_inverse, point_trap_backproject, point_trap_projection, slm_field, trap_bins,
)
from ...core.geometry import Setup, input_amplitude
from ...core.metrics import efficiency, rel_std, trap_intensities, uniformity
from ...core.rng import Rng
from ...core.traps import TrapSet


# ---- seeded permutation, deadlines ----------------------------------------------------------------------------

def permutation(rng: Rng, n: int) -> np.ndarray:
    """Fisher-Yates shuffle of ``0..n-1`` through the portable ``Rng`` (``j = floor(u (i + 1))`` for ``i = n-1..1``)."""
    p = np.arange(n, dtype=np.int64)
    for i in range(n - 1, 0, -1):
        j = int(rng.uniform() * (i + 1))
        p[i], p[j] = p[j], p[i]
    return p


def deadline_of(time_s: float | None) -> float | None:
    return None if time_s is None else time.perf_counter() + time_s


def expired(deadline: float | None) -> bool:
    return deadline is not None and time.perf_counter() >= deadline


def start_phase(setup: Setup, rng: Rng, init: np.ndarray | None) -> np.ndarray:
    """The starting phase: ``init`` (validated) or ``n_pix^2`` uniform random phases drawn in C order from ``rng``."""
    n = setup.n_pix
    if init is None:
        return rng.phases(n * n).reshape(n, n)
    init = np.asarray(init, dtype=np.float64)
    if init.shape != (n, n) or not np.all(np.isfinite(init)):
        raise ValueError(f"init must be a finite array of shape {(n, n)}")
    return init.copy()


# ---- forward models with exact adjoints -----------------------------------------------------------------------

def _sinc_1d(setup: Setup, fill_factor: float) -> np.ndarray:
    k = np.arange(setup.n_fft) - setup.n_fft // 2
    return np.sinc(math.sqrt(fill_factor) * k / setup.n_fft)


class FocalForward:
    """``phi -> E`` on the centred ``n_fft x n_fft`` focal grid (scaling of ``forward.fft_focal_field``), with adjoint.

    ``device=None`` is the ideal device (``fft_focal_field``). A device without crosstalk multiplies the FFT by the
    pixel-aperture envelope; with crosstalk the hologram is upsampled, blurred and transformed on the finer grid
    exactly as ``device.device_focal_field`` does (the tests compare the two to 1e-12). ``adjoint(G, cache)`` returns
    ``dL/dphi`` for ``G = dL/dE*`` (module docstring).
    """

    def __init__(self, setup: Setup, device: Device | None = None):
        self.setup = setup
        self.device = None if device is None else replace(device, flicker_rad=0.0)
        self.amp = input_amplitude(setup)
        d = self.device
        # a quantizer makes the cost a staircase in the phase while the backward pass is the identity (module docstring)
        self.smooth = d is None or d.bit_depth is None
        if d is not None:
            self._swap_env = _sinc_1d(setup, d.fill_factor)
            if d.crosstalk is not None:
                u, n, m = d.upsample, setup.n_pix, setup.n_fft
                mu = m * u
                self._u, self._mu = u, mu
                self._amp_up = np.kron(self.amp, np.ones((u, u)))
                r = np.exp(2j * math.pi * ((n * u - 1) / 2.0) * (np.arange(mu) - mu // 2) / mu)
                lo = mu // 2 - m // 2
                self._wramp = r[lo:lo + m]                           # linear phase on the wanted window
                self._idx = np.arange(-(m // 2), m - m // 2) % mu    # FFT bins of the window, in window order
                k = np.arange(m) - m // 2
                with np.errstate(invalid="ignore", divide="ignore"):
                    dirichlet = np.sin(math.pi * k / m) / (u * np.sin(math.pi * k / mu))
                dirichlet[m // 2] = 1.0
                self._swap = self._swap_env / dirichlet

    def forward(self, phi: np.ndarray):
        s, d = self.setup, self.device
        if d is None:
            f = slm_field(phi, s)
            return fft_focal_field(phi, s), f
        disp = displayed_phase(phi, d, None)
        if d.crosstalk is None:
            f = slm_field(disp, s)
            e = fft_focal_field(disp, s)
            return e * self._swap_env[:, None] * self._swap_env[None, :], f
        u = self._u
        psi = crosstalk(disp, d)
        g = self._amp_up * np.exp(1j * psi)
        # pruned zero-padded 2D transform: only the n u nonzero rows and the m wanted frequencies are computed
        t1 = np.fft.fft(g, n=self._mu, axis=1, norm="ortho")[:, self._idx]
        y = np.fft.fft(t1, n=self._mu, axis=0, norm="ortho")[self._idx, :]
        e = y * self._wramp[:, None] * self._wramp[None, :] / u
        return e * self._swap[:, None] * self._swap[None, :], g

    def adjoint(self, grad_e: np.ndarray, cache) -> np.ndarray:
        s, d = self.setup, self.device
        if d is None:
            h = fft_inverse(grad_e, s)
            return 2.0 * np.real(1j * cache * np.conj(h))
        if d.crosstalk is None:
            h = fft_inverse(grad_e * self._swap_env[:, None] * self._swap_env[None, :], s)
            return 2.0 * np.real(1j * cache * np.conj(h))
        n, m, u, mu = s.n_pix, s.n_fft, self._u, self._mu
        gc = grad_e * self._swap[:, None] * self._swap[None, :] / u
        gc = gc * np.conj(self._wramp)[:, None] * np.conj(self._wramp)[None, :]
        s1 = np.zeros((mu, m), dtype=np.complex128)
        s1[self._idx, :] = gc
        s2 = np.fft.ifft(s1, axis=0, norm="ortho")[: n * u, :]
        s3 = np.zeros((n * u, mu), dtype=np.complex128)
        s3[:, self._idx] = s2
        h = np.fft.ifft(s3, axis=1, norm="ortho")[:, : n * u]
        grad_psi = 2.0 * np.real(1j * cache * np.conj(h))
        return crosstalk_adjoint(grad_psi, d)


class TrapForward:
    """``phi -> V_m`` (the trap fields) with adjoint. Ideal device: the point-trap form (any z and vortex charge).

    With a device the fields are read from the device's FFT-form focal field at the FFT bin nearest to each trap,
    ``V_m = E[bin] pad / n_pix`` (exact for traps on bins with z = 0 and no vortex; the other cases are sampled, and
    a z different from 0 is not modelled: ``ValueError``).
    """

    def __init__(self, setup: Setup, traps: TrapSet, device: Device | None = None, chunk: int | None = None):
        self.setup, self.traps, self.chunk = setup, traps, chunk
        self.device = device
        if device is None:
            self._focal = None
        else:
            if np.any(traps.z_m != 0) or np.any(traps.charge != 0):
                raise ValueError("a device model supports traps with z = 0 and no vortex charge (FFT form)")
            self._focal = FocalForward(setup, device)
            self._iy, self._ix = trap_bins(setup, traps)
            self._scale = setup.pad / setup.n_pix

    def fields(self, phi: np.ndarray):
        if self._focal is None:
            f = slm_field(phi, self.setup)
            return point_trap_projection(f, self.setup, self.traps, self.chunk), f
        e, cache = self._focal.forward(phi)
        return e[self._iy, self._ix] * self._scale, cache

    def adjoint(self, grad_v: np.ndarray, cache) -> np.ndarray:
        if self._focal is None:
            h = point_trap_backproject(grad_v, self.setup, self.traps, self.chunk) / self.setup.n_pix**2
            return 2.0 * np.real(1j * cache * np.conj(h))
        g = np.zeros((self.setup.n_fft, self.setup.n_fft), dtype=np.complex128)
        np.add.at(g, (self._iy, self._ix), grad_v * self._scale)
        return self._focal.adjoint(g, cache)


# ---- cost functions -------------------------------------------------------------------------------------------

class TrapCost:
    """``C_t = sum_m (I_m - s T_m)^t / sum_m (s T_m)^t`` with ``T_m = efficiency w_m / sum w`` (module docstring).

    ``value_grad(phi)`` returns ``(C, dC/dphi, V)``. ``refit(V)`` sets ``s`` to the least-squares scale (Polin et al.
    2005's gamma, t = 2 closed form); ``s`` is held fixed inside a line search, so the gradient is exact for the cost
    that is being minimised.
    """

    def __init__(self, setup: Setup, traps: TrapSet, device: Device | None = None, *, t: int = 2,
                 efficiency: float = 0.9, scale: float = 1.0, chunk: int | None = None):
        if t < 2 or t % 2:
            raise ValueError(f"t must be an even integer >= 2, got {t}")
        if not (0 < efficiency <= 1):
            raise ValueError(f"efficiency must be in (0, 1], got {efficiency}")
        self.fwd = TrapForward(setup, traps, device, chunk)
        self.smooth = self.fwd._focal is None or self.fwd._focal.smooth
        self.t, self.s = int(t), float(scale)
        self.target = efficiency * traps.weight / np.sum(traps.weight)

    def refit(self, v: np.ndarray) -> None:
        i = np.abs(v) ** 2
        self.s = float(np.sum(i * self.target) / np.sum(self.target**2))

    def value_grad(self, phi: np.ndarray):
        v, cache = self.fwd.fields(phi)
        i = np.abs(v) ** 2
        d = i - self.s * self.target
        norm = np.sum((self.s * self.target) ** self.t)
        value = float(np.sum(d**self.t) / norm)
        g_i = self.t * d ** (self.t - 1) / norm
        return value, self.fwd.adjoint(g_i * v, cache), v


class FieldCost:
    """The same cost over the signal region of a focal-field target (Harte et al. 2014 eqs (6) and (10)).

    ``amplitude`` and ``mask`` are on the ``n_fft`` focal grid; the target intensity inside the mask is
    ``efficiency n_pix^2 amplitude^2 / sum_mask amplitude^2`` (so ``sum T`` is the requested fraction of the total
    power ``n_pix^2``); the noise region (outside the mask) is free. ``value_grad`` returns ``(C, dC/dphi, E)``.
    """

    def __init__(self, setup: Setup, amplitude: np.ndarray, mask: np.ndarray, device: Device | None = None, *,
                 t: int = 2, efficiency: float = 0.4, scale: float = 1.0):
        m = setup.n_fft
        amplitude = np.asarray(amplitude, dtype=np.float64)
        mask = np.asarray(mask, dtype=bool)
        if amplitude.shape != (m, m) or mask.shape != (m, m):
            raise ValueError(f"the target must be on the {m} x {m} focal grid (n_fft), got {amplitude.shape}")
        if t < 2 or t % 2:
            raise ValueError(f"t must be an even integer >= 2, got {t}")
        if not (0 < efficiency <= 1):
            raise ValueError(f"efficiency must be in (0, 1], got {efficiency}")
        self.setup, self.mask = setup, mask
        self.fwd = FocalForward(setup, device)
        self.smooth = self.fwd.smooth
        self.t, self.s = int(t), float(scale)
        a2 = np.where(mask, amplitude**2, 0.0)
        if a2.sum() <= 0:
            raise ValueError("the signal region carries no target power")
        self.target = efficiency * setup.n_pix**2 * a2 / a2.sum()

    def refit(self, e: np.ndarray) -> None:
        i = np.where(self.mask, np.abs(e) ** 2, 0.0)
        self.s = float(np.sum(i * self.target) / np.sum(self.target**2))

    def value_grad(self, phi: np.ndarray):
        e, cache = self.fwd.forward(phi)
        i = np.abs(e) ** 2
        st = self.s * self.target
        d = np.where(self.mask, i - st, 0.0)
        norm = np.sum(np.where(self.mask, st, 0.0) ** self.t)
        value = float(np.sum(d**self.t) / norm)
        g_i = self.t * d ** (self.t - 1) / norm
        return value, self.fwd.adjoint(g_i * e, cache), e


# ---- optimizers -----------------------------------------------------------------------------------------------

_STAIRCASE = contextvars.ContextVar("staircase_search", default=False)


@contextlib.contextmanager
def staircase_search():
    """Within the block ``cg_minimize`` searches a model flagged not ``smooth`` (a quantizing device) with the ladder of
    ``_sufficient_decrease`` instead of strong Wolfe (``cg_minimize``, Straight-through models). Opt-in, so a caller that
    optimises such a model with the Wolfe search keeps its results (B1 on case C08)."""
    token = _STAIRCASE.set(True)
    try:
        yield
    finally:
        _STAIRCASE.reset(token)


@dataclass
class OptResult:
    x: np.ndarray
    f: float
    iterations: int
    evaluations: int
    aux: Any = None


def _cubic_min(a, fa, ga, b, fb, gb):
    """Minimizer of the cubic through ``(a, fa, ga)`` and ``(b, fb, gb)`` or None (Nocedal and Wright, eq 3.59)."""
    if a == b or not all(math.isfinite(v) for v in (fa, ga, fb, gb)):
        return None
    d1 = ga + gb - 3.0 * (fa - fb) / (a - b)
    rad = d1 * d1 - ga * gb
    if rad < 0:
        return None
    d2 = math.copysign(math.sqrt(rad), b - a)
    den = gb - ga + 2.0 * d2
    if den == 0:
        return None
    return b - (b - a) * (gb + d2 - d1) / den


def cg_minimize(fun, x0: np.ndarray, iterations: int, *, callback=None, deadline: float | None = None,
                c1: float = 1e-4, c2: float = 0.1, max_line_evals: int = 25, nonsmooth: bool | None = None) -> OptResult:
    """Nonlinear conjugate gradient, Fletcher-Reeves, with a strong-Wolfe line search.

    ``fun(x) -> (f, grad, aux)``. Directions ``d_i = -g_i + gamma_i d_{i-1}`` with ``gamma_i = g_i.g_i / g_{i-1}.g_{i-1}``
    (Harte et al. 2014 eqs (3) to (5)); the Hessian is never formed. The line search (Nocedal and Wright, Algorithms 3.5
    and 3.6, cubic interpolation, ``c1 = 1e-4``, ``c2 = 0.1``: ``c2 < 1/2`` keeps Fletcher-Reeves directions descent
    directions) returns a step with sufficient decrease and a curvature condition. The first trial step moves the
    largest pixel by 0.1 rad, later ones are ``2 (f_k - f_{k-1}) / phi'(0)`` (eq 3.60). If the direction is not a descent
    direction or the search fails, the iteration restarts from steepest descent and the run stops if that fails too.
    ``callback(i, x, f, aux)`` is called after every accepted step and stops the run when it returns True. The cost
    value never increases.

    Straight-through models. Inside ``staircase_search()`` (opt-in: M13), when ``fun`` is a bound method of an object whose
    ``smooth`` attribute is False (a cost on a device that quantizes the phase: the value is evaluated on the rounded phase,
    the backward pass is the identity), the
    cost is a staircase in the phase and the gradient is not its derivative, so the slope along a direction and the
    change of the value disagree and the curvature condition ``|phi'(a)| <= c2 |phi'(0)|`` has nothing to measure. The
    strong-Wolfe search then ran out of evaluations after two or three iterations whatever the budget (the early stop of
    M13 on case C08, found in the U12b notebooks: measured, 26 evaluations per search and no step). Such a model takes
    ``_sufficient_decrease`` instead, a ladder of trial steps that asks for the sufficient-decrease condition alone. When
    no trial lowers the cost the run walks on to the lowest trial instead of stopping (the straight-through direction is a
    good one for the smooth cost, and the staircase value at the point the last search chose is a lucky low), keeps the
    lowest point seen, reports that point to the callback and returns it, so the cost the caller sees never increases; the
    run uses its whole budget (measured on C08, 60 iterations: the lowest value was reached at iteration 33 and the remaining 27
    iterations did not improve it). ``nonsmooth`` overrides the choice. Outside the block, and for a
    smooth model, nothing changes: the runs of M10, B1 and the others are unchanged.
    """
    if nonsmooth is None:
        nonsmooth = _STAIRCASE.get() and not getattr(getattr(fun, "__self__", None), "smooth", True)
    x = np.array(x0, dtype=np.float64)
    f, g, aux = fun(x)
    evals = 1
    d = -g
    f_old = None
    best = (x, f, aux)                      # the lowest value seen (on a smooth model it is always the current point)
    it = 0
    for it in range(1, int(iterations) + 1):
        if expired(deadline):
            it -= 1
            break
        step = forced = None
        for restart in (False, True):
            if restart or float(np.sum(g * d)) >= 0:
                d = -g
            gd = float(np.sum(g * d))
            if not gd < 0:
                break
            if f_old is not None and f < f_old and not restart:
                a0 = 2.0 * (f - f_old) / gd
            else:
                a0 = 0.1 / max(float(np.abs(d).max()), 1e-300)
            if nonsmooth:
                step, forced, n_ev = _sufficient_decrease(fun, x, d, f, gd, a0, c1, max_line_evals)
            else:
                step, n_ev = _wolfe(fun, x, d, f, gd, a0, c1, c2, max_line_evals)
            evals += n_ev
            if step is not None:
                break
        if step is None and forced is not None:
            step = forced                   # no step lowers a staircase cost: walk on to the lowest trial, keep the best point
        if step is None:
            it -= 1
            break
        a, fn, gn_vec, auxn = step
        x = x + a * d
        gg = float(np.sum(g * g))
        d = -gn_vec + (float(np.sum(gn_vec * gn_vec)) / gg if gg > 0 else 0.0) * d
        f_old, f, g, aux = f, fn, gn_vec, auxn
        if f < best[1]:
            best = (x, f, aux)
        if callback is not None and callback(it, best[0], best[1], best[2]):
            break
    return OptResult(best[0], best[1], it, evals, best[2])


def _wolfe(fun, x, d, f0, g0, a1, c1, c2, max_evals):
    """Strong-Wolfe step along ``d``; returns ``((a, f, grad, aux) | None, evaluations)``."""
    cache: dict[float, tuple] = {0.0: (f0, g0, None, None)}
    evals = 0

    def phi(a):
        nonlocal evals
        if a not in cache:
            fa, ga, aux = fun(x + a * d)
            evals += 1
            cache[a] = (fa, float(np.sum(ga * d)), ga, aux)
        return cache[a]

    def zoom(lo, hi):
        flo, glo = phi(lo)[:2]
        fhi, ghi = phi(hi)[:2]
        for _ in range(max_evals):
            lo_b, hi_b = min(lo, hi), max(lo, hi)
            if hi_b - lo_b < 1e-15 * max(hi_b, 1e-300):
                break
            a = _cubic_min(lo, flo, glo, hi, fhi, ghi)
            if a is None or not (lo_b + 0.1 * (hi_b - lo_b) <= a <= hi_b - 0.1 * (hi_b - lo_b)):
                a = 0.5 * (lo + hi)
            fa, ga = phi(a)[:2]
            if not math.isfinite(fa) or fa > f0 + c1 * a * g0 or fa >= flo:
                hi, fhi, ghi = a, fa, ga
            else:
                if abs(ga) <= -c2 * g0:
                    return a
                if ga * (hi - lo) >= 0:
                    hi, fhi, ghi = lo, flo, glo
                lo, flo, glo = a, fa, ga
        return lo if lo > 0 and flo < f0 else None

    a_prev, f_prev = 0.0, f0
    a = a1
    result = None
    for i in range(max_evals):
        fa, ga = phi(a)[:2]
        if not math.isfinite(fa) or fa > f0 + c1 * a * g0 or (i > 0 and fa >= f_prev):
            result = zoom(a_prev, a)
            break
        if abs(ga) <= -c2 * g0:
            result = a
            break
        if ga >= 0:
            result = zoom(a, a_prev)
            break
        a_prev, f_prev = a, fa
        a *= 2.0
    else:
        result = a_prev if a_prev > 0 else None
    if result is None or result <= 0 or not (cache[result][0] < f0):
        return None, evals
    fa, _, ga, aux = cache[result]
    return (result, fa, ga, aux), evals


def _sufficient_decrease(fun, x, d, f0, g0, a1, c1, max_evals):
    """Ladder search along ``d`` for a staircase cost: ``(step, lowest, evaluations)``, steps as ``_wolfe`` returns them.

    A staircase is flat for steps too short to move a pixel across a level and jumps for longer ones, so the ladder goes in
    both directions: from ``a1`` the step is doubled while the value keeps falling (a flat or higher first trial does not end
    the doubling: the useful step may be longer), and when no doubled step satisfied the condition either, halved from ``a1``
    (``DOUBLINGS`` and ``HALVINGS`` trials at most, within ``max_evals``). ``step`` is the lowest trial that satisfies
    ``f(a) <= f0 + c1 a g0`` and ``f(a) < f0`` (``None`` if none does); ``lowest`` is the lowest trial of all, which the caller
    may walk to when ``step`` is ``None``.
    """
    best: tuple | None = None
    lowest: tuple | None = None
    evals = 0

    def trial(a):
        nonlocal best, lowest, evals
        fa, ga, aux = fun(x + a * d)
        evals += 1
        if math.isfinite(fa) and (lowest is None or fa < lowest[1]):
            lowest = (a, fa, ga, aux)
        ok = math.isfinite(fa) and fa <= f0 + c1 * a * g0 and fa < f0
        if ok and (best is None or fa < best[1]):
            best = (a, fa, ga, aux)
            return True
        return False

    a = a1
    for _ in range(min(DOUBLINGS + 1, max_evals)):
        improved = trial(a)
        if best is not None and not improved:
            break                           # the value stopped falling after a good step
        a *= 2.0
    if best is None:
        a = a1
        for _ in range(min(HALVINGS, max_evals - evals)):
            a *= 0.5
            if trial(a):
                break
    return best, lowest, evals


DOUBLINGS = 10      # trial steps a1 * 2^k, k = 0..DOUBLINGS, of the sufficient-decrease fallback
HALVINGS = 6        # then a1 * 2^-k, k = 1..HALVINGS, when no longer step lowered the cost


def adam_minimize(fun, x0: np.ndarray, iterations: int, *, lr: float, beta1: float = 0.9, beta2: float = 0.999,
                  eps: float = 1e-8, callback=None, deadline: float | None = None) -> OptResult:
    """Adam (Kingma and Ba 2015) on a real array: ``m <- b1 m + (1 - b1) g``, ``v <- b2 v + (1 - b2) g^2``,
    ``x <- x - lr mhat / (sqrt(vhat) + eps)`` with bias-corrected ``mhat, vhat``.

    ``fun(x) -> (f, grad, aux)``; ``callback(i, x, f, aux)`` is called with the value and aux evaluated at the point
    *before* the step of iteration ``i`` and stops the run when it returns True. Adam is not a descent method: the cost
    may rise, and the returned ``f`` is the last evaluated value.
    """
    x = np.array(x0, dtype=np.float64)
    m = np.zeros_like(x)
    v = np.zeros_like(x)
    f, aux = float("nan"), None
    it = 0
    for it in range(1, int(iterations) + 1):
        if expired(deadline):
            it -= 1
            break
        f, g, aux = fun(x)
        if callback is not None and callback(it, x, f, aux):
            break
        m = beta1 * m + (1.0 - beta1) * g
        v = beta2 * v + (1.0 - beta2) * g * g
        mh = m / (1.0 - beta1**it)
        vh = v / (1.0 - beta2**it)
        x = x - lr * mh / (np.sqrt(vh) + eps)
    return OptResult(x, f, it, it, aux)


# ---- history --------------------------------------------------------------------------------------------------

def trap_history(iteration: int, v: np.ndarray, weights: np.ndarray, t0: float, **extra) -> dict:
    """History entry from the trap fields: efficiency from ``I_m``, uniformity and relative std from ``I_m / w_m``."""
    iw = trap_intensities(v, weights)
    return {"iteration": int(iteration), "efficiency": efficiency(trap_intensities(v)), "uniformity": uniformity(iw),
            "rel_std": rel_std(iw), "time_s": time.perf_counter() - t0, **extra}


def measure_region(amplitude: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.asarray(mask, dtype=bool) & (np.asarray(amplitude) > 0)


def field_error(e: np.ndarray, amplitude: np.ndarray, mask: np.ndarray) -> float:
    """Relative RMS error over the measure region of the intensity shape: ``I`` and ``T = amplitude^2`` each
    normalised to unit sum in the region, ``epsilon = sqrt(mean(((I - T) / T)^2))`` (Schroff et al. 2023; Pasienski
    and DeMarco 2008 eta). Independent of efficiency and of overall scale."""
    reg = measure_region(amplitude, mask)
    i = np.abs(e[reg]) ** 2
    t = np.asarray(amplitude)[reg] ** 2
    i, t = i / i.sum(), t / t.sum()
    return float(np.sqrt(np.mean(((i - t) / t) ** 2)))


def field_efficiency(e: np.ndarray, mask: np.ndarray) -> float:
    """Fraction of the total power in the signal region (``sum |E|^2`` over the focal grid is ``n_pix^2`` by Parseval)."""
    p = np.abs(e) ** 2
    return float(p[np.asarray(mask, dtype=bool)].sum() / p.sum())


def field_history(iteration: int, e: np.ndarray, amplitude: np.ndarray, mask: np.ndarray, t0: float, **extra) -> dict:
    """History entry for a shaped target: efficiency is the signal-region power fraction; uniformity and relative
    std are those of ``I / T`` over the measure region; ``error`` is ``field_error``."""
    reg = measure_region(amplitude, mask)
    ratio = np.abs(e[reg]) ** 2 / np.asarray(amplitude)[reg] ** 2
    return {"iteration": int(iteration), "efficiency": field_efficiency(e, mask),
            "uniformity": float(1.0 - (ratio.max() - ratio.min()) / (ratio.max() + ratio.min())),
            "rel_std": float(100.0 * ratio.std() / ratio.mean()), "time_s": time.perf_counter() - t0,
            "error": field_error(e, amplitude, mask), **extra}
