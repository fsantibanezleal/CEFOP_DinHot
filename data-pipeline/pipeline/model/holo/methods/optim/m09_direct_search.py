r"""M09 direct search with the efficiency-uniformity cost of Polin et al. (algorithms dossier D2.1).

Source: Polin, Hovhannisyan, Sorensen, Optics Express 13, 5831 (2005), https://doi.org/10.1364/OPEX.13.005831 (cost
eqs (11) to (13)); the benchmark numbers on the 10x10 task are Di Leonardo et al. 2007,
https://doi.org/10.1364/OE.15.001913 (direct search from SR, ``f = 0.5``: ``u = 1.00``, ``e = 0.68`` after 1.3 N steps).

Cost, with ``I_m`` the trap intensities (fractions of the input power), ``I^D_m = w_m / mean(w)`` the design
intensities and ``M`` the trap count:

.. math::
    C = -\langle I \rangle + f\,\sigma,\quad \sigma = \sqrt{\tfrac1M \sum_m (I_m - \gamma I^D_m)^2},\quad
    \gamma = \frac{\sum_m I_m I^D_m}{\sum_m (I^D_m)^2}.

``f`` weights uniformity against efficiency (default 0.5, the value of Di Leonardo et al. 2007's DS row). One *sweep*
visits every SLM pixel once in a seeded random order (``permutation(rng, n_pix^2)``); at each pixel all ``P`` trial
phases ``2 pi k / P`` (default ``P = 8``, the 8 grey levels of the DS row of Di Leonardo et al. 2007) are evaluated
and the best one is kept if it lowers the cost (the pixel's current phase stays otherwise), so the cost never
increases. The trap fields are updated incrementally: a change ``dz = exp(i phi') - exp(i phi)`` at pixel ``j`` changes
``V_m`` by ``(A_j / N_pix) dz exp(-i Delta_j^m)``, an ``O(M)`` update (point-trap form, any trap z and vortex charge).
Polin: convergence in about ``N`` trials, worst case ``N P``. ``budget.iterations`` is the number of sweeps; ``max_trials``
caps the number of trial phases evaluated. Limits (Polin; Di Leonardo): stuck in local minima, sequential, ghost traps
absorb efficiency. The optimization uses the ideal point-trap model: a ``device`` is not part of M09's model.
Start: the SR superposition (``init`` overrides), rounded to the ``P`` levels.
"""
from __future__ import annotations

import math
import time

import numpy as np

from ...core.forward import _separable_factors, point_trap_projection, slm_field
from ...core.geometry import Setup, input_amplitude, slm_grid
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ._common import deadline_of, expired, permutation, trap_history
from ._gs_family import sr_start

SPEC = MethodSpec(id="M09", name="Direct search", family="optimization", lane="baked", targets=("traps",),
                  dims=(2, 3))
DEFAULT_LEVELS = 8
DEFAULT_F = 0.5
DEFAULT_SWEEPS = 2


def polin_cost(i: np.ndarray, design: np.ndarray, f: float) -> np.ndarray:
    """``C = -mean(I) + f sigma`` over the last axis of ``i`` (shape ``(..., M)``), design intensities ``I^D``."""
    i = np.asarray(i, dtype=np.float64)
    gamma = (i @ design) / np.sum(design**2)
    resid = i - gamma[..., None] * design
    sigma = np.sqrt(np.mean(resid**2, axis=-1))
    return -np.mean(i, axis=-1) + f * sigma


def run(setup: Setup, target: Target, *, device=None, budget: Budget, rng: Rng, init: np.ndarray | None = None,
        f: float = DEFAULT_F, levels: int = DEFAULT_LEVELS, max_trials: int | None = None) -> Result:
    """Direct search on a trap target; see the module docstring. ``meta`` carries ``trials``, ``accepted``, ``f``."""
    if target.kind != "traps":
        raise ValueError("M09 supports trap targets only (targets: 'traps'); got a shaped field")
    if levels < 2 or int(levels) != levels:
        raise ValueError("levels must be an integer >= 2")
    if f < 0 or not math.isfinite(f):
        raise ValueError("f must be finite and >= 0")
    traps = target.traps
    n = setup.n_pix
    t0 = time.perf_counter()
    deadline = deadline_of(budget.time_s)
    phi = sr_start(setup, traps, rng) if init is None else np.asarray(init, dtype=np.float64).copy()
    if phi.shape != (n, n):
        raise ValueError(f"init must have shape {(n, n)}")
    step = 2.0 * math.pi / levels
    phi = np.mod(np.rint(phi / step), levels) * step                       # an SLM with P grey levels
    gx, gy = _separable_factors(setup, traps, slice(None), -1.0)          # exp(-i (c_z x^2 + k x_m x)), (M, n)
    design = traps.weight / np.mean(traps.weight)
    amp = input_amplitude(setup)
    xs, ys = slm_grid(setup)
    theta = np.arctan2(ys, xs)
    has_vortex = bool(np.any(traps.charge != 0))
    charge = traps.charge.astype(np.float64)
    lev = np.exp(2j * math.pi * np.arange(levels) / levels)
    n_pix2 = float(n * n)
    trials = accepted = 0
    history: list = []
    stop = False
    v = point_trap_projection(slm_field(phi, setup), setup, traps)
    for sweep in range(1, budget.iterations + 1):
        order = permutation(rng, n * n)
        cur = float(polin_cost(np.abs(v) ** 2, design, f))
        for count, flat in enumerate(order):
            if max_trials is not None and trials + levels > max_trials:
                stop = True
                break
            if count % 512 == 0 and expired(deadline):
                stop = True
                break
            jy, jx = divmod(int(flat), n)
            row = gy[:, jy] * gx[:, jx]
            if has_vortex:
                row = row * np.exp(-1j * charge * theta[jy, jx])
            zc = np.exp(1j * phi[jy, jx])
            coef = (amp[jy, jx] / n_pix2) * (lev - zc)
            vt = v[None, :] + coef[:, None] * row[None, :]
            costs = polin_cost(vt.real**2 + vt.imag**2, design, f)
            trials += levels
            k = int(np.argmin(costs))
            if costs[k] < cur:
                v = vt[k]
                phi[jy, jx] = 2.0 * math.pi * k / levels
                cur = float(costs[k])
                accepted += 1
        v = point_trap_projection(slm_field(phi, setup), setup, traps)      # drop incremental rounding drift
        history.append(trap_history(sweep, v, traps.weight, t0, cost=float(polin_cost(np.abs(v) ** 2, design, f)),
                                    trials=trials))
        if stop:
            break
    return Result(phi=np.mod(phi, 2.0 * math.pi), history=history, fields=v,
                  meta={"trials": trials, "accepted": accepted, "f": f, "levels": levels, "sweeps": len(history)})
