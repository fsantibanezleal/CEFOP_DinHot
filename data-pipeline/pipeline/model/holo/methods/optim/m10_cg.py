"""M10 conjugate-gradient minimization of the intensity cost (Harte et al. 2014; algorithms dossier D2.2).

Source: Harte, Bruce, Belmonte, Arnold, Opt. Express 22, 26548 (2014), https://doi.org/10.1364/OE.22.026548
(arXiv 1408.0188, eqs (1) to (11)). The SLM field is ``E_in = A_j exp(i phi_j)``, the focal field ``E_out`` its
zero-padded Fourier transform, and the cost over the signal region (the noise region is free)

.. math::
    C_t = \\sum_{nm} \\left(T_{nm} - |\\tilde\\psi_{nm}|^2\\right)^t,\\qquad
    \\frac{\\partial C_t}{\\partial\\phi_{rs}} = 2 t\\,\\mathrm{Re}\\!\\left(i\\,\\psi_{rs}^* X_{rs}\\right),\\quad
    X_{rs} = \\sum_{nm} (T_{nm} - I_{nm})^{t-1}\\,\\tilde\\psi_{nm}^*\\, e^{+2\\pi i (rn + sm)/N}

(in the conventions of ``_common``: the gradient is two Fourier transforms, ``FocalForward.forward`` and
``.adjoint``). ``t = 2`` is the basic cost; the powered cost ``t = 4`` suppresses the vortices that the basic cost leaves
(Harte: 26 percent error with ``t = 2``; sequential ``t = 4`` then ``t = 2`` gives 0.07 percent on a ring/power-law
target after 13000 iterations). ``t`` may be an int or a tuple (stages, equal share of ``budget.iterations`` each,
Harte's sequential scheme); the default is ``(4, 2)`` for shaped fields and ``2`` for traps.

Optimizer: Fletcher-Reeves conjugate gradient (``gamma_i = g_i.g_i / g_{i-1}.g_{i-1}``, Harte eqs (3) to (5)) with a
strong-Wolfe line search (``_common.cg_minimize``: cubic interpolation, ``c1 = 1e-4``, ``c2 = 0.1``); Harte does not
state the line search. The cost is normalised by ``sum T^t`` (scale free, same minimizers) and the target carries the
requested ``efficiency`` (default 0.4 for fields, 0.9 for traps; Harte: 45 to 64 percent in the trapping region).
Start: uniform random phases from ``rng`` (``init`` overrides). The model is the ideal device: ``device`` is not part
of M10's model (M13 is the device-aware variant); the caller scores M10 on a device with ``core.device``.
Results are pure functions of (inputs, seed). Square lattice (Harte): 0.58 percent after 4000 iterations.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.device import Device
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _common as C

SPEC = MethodSpec(id="M10", name="Conjugate-gradient minimization", family="optimization", lane="both",
                  targets=("traps", "field"), dims=(2, 3))
DEFAULT_LATTICE_ITERATIONS = 1500


def _stages(t, kind: str, iterations: int) -> list[tuple[int, int]]:
    if t is None:
        ts = (4, 2) if kind == "field" else (2,)
    else:
        ts = tuple(t) if isinstance(t, (tuple, list)) else (t,)
    if not ts:
        raise ValueError("t must be an even integer >= 2 or a non-empty tuple of them")
    share = max(1, iterations // len(ts))
    out = [(int(tt), share) for tt in ts]
    out[-1] = (out[-1][0], max(1, iterations - share * (len(ts) - 1)))
    return out


def optimize(setup: Setup, target: Target, *, device: Device | None, budget: Budget, rng: Rng,
             init: np.ndarray | None, t=None, efficiency: float | None = None, label: str = "M10") -> Result:
    """The shared driver of M10 and M13: ``device`` is the optimization model (None: ideal)."""
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    phi = C.start_phase(setup, rng, init)
    history: list = []
    done = 0
    last = None
    cost = None
    for tt, iters in _stages(t, target.kind, budget.iterations):
        if target.kind == "traps":
            cost = C.TrapCost(setup, target.traps, device, t=tt, efficiency=0.9 if efficiency is None else efficiency)
        else:
            cost = C.FieldCost(setup, target.amplitude, target.mask, device, t=tt,
                               efficiency=0.4 if efficiency is None else efficiency)

        def record(it, x, f, aux, tt=tt, base=done):
            nonlocal last
            last = aux
            if target.kind == "traps":
                history.append(C.trap_history(base + it, aux, target.traps.weight, t0, cost=f, t=tt))
            else:
                history.append(C.field_history(base + it, aux, target.amplitude, target.mask, t0, cost=f, t=tt))
            return False

        res = C.cg_minimize(cost.value_grad, phi, iters, callback=record, deadline=deadline)
        phi = res.x
        done += res.iterations
        if C.expired(deadline):
            break
    if last is None:                    # a zero-iteration run (deadline already passed): evaluate the start
        _, _, last = cost.value_grad(phi)
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=last,
                  meta={"method": label, "iterations": done, "device_aware": device is not None})


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, t=None, efficiency: float | None = None) -> Result:
    """Conjugate-gradient minimization on the ideal model (see the module docstring); ``device`` is ignored."""
    return optimize(setup, target, device=None, budget=budget, rng=rng, init=init, t=t, efficiency=efficiency)
