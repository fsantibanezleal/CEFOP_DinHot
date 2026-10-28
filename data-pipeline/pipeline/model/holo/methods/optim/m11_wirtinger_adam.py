"""M11 Wirtinger gradient descent with Adam (Chakravarthula et al. 2019; algorithms dossier D2.3).

Source: Chakravarthula, Peng, Kollin, Fuchs, Heide, Wetzstein, "Wirtinger Holography for Near-Eye Displays", ACM TOG
38(6), 213 (2019), https://doi.org/10.1145/3355089.3356539, eqs (5) to (8): minimise ``f(|P(H(phi))|^2, I) + ||phi||^2``
over the phase ``phi`` with a differentiable propagation ``P``, ``H = c exp(i phi)``; the gradient of the real loss with
respect to the complex field is the Wirtinger derivative ``dL/dz*`` and is pulled back through ``P`` by the chain rule,

.. math:: \\frac{\\partial L}{\\partial\\phi_j} = 2\\,\\mathrm{Re}\\!\\left(i\\, f_j\\, \\overline{(P^H G)_j}\\right),
          \\qquad G = \\frac{\\partial L}{\\partial z^*} = L'(I)\\, z,

so any linear forward model works (``_common.TrapForward``: point-trap form with z and vortex charge, or the device
FFT form; ``FocalForward`` for shaped fields). The paper uses L-BFGS for quadratic losses and Adam with ``lr = 0.001``
for learned losses; ``PAPER_LR`` records that value. The loss here is the quadratic intensity loss of ``_common``
(``C_2``: ``sum (I_m - T_m)^2 / sum T_m^2`` with the design efficiency 0.9 for traps, 0.4 for fields). The paper's
``||phi||^2`` term has zero weight here (a phase penalty has no role for a phase-only hologram of traps).

Optimizer: Adam (``beta1 = 0.9``, ``beta2 = 0.999``, ``eps = 1e-8``) with the learning rate ``DEFAULT_LR``, tuned for
this loss: the paper's 0.001 moves a pixel at most 0.03 rad in 30 iterations. The tuning record (10x10 task, 256 x 256
pixels, 30 iterations, relative std of ``I_m / w_m`` in percent) is in the E3 report
(``wip/dinhot/e3-methods-advanced-2026-10-28.md``, D1). Start: uniform random phases from ``rng`` (``init``
overrides). The model is the ideal device unless ``device`` is given (traps then on FFT bins with z = 0).
"""
from __future__ import annotations

import time

import numpy as np

from ...core.device import Device
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _common as C

SPEC = MethodSpec(id="M11", name="Wirtinger gradient descent with Adam", family="optimization", lane="both",
                  targets=("traps", "field"), dims=(2, 3))
PAPER_LR = 0.001
DEFAULT_LR = 1.0


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, lr: float = DEFAULT_LR, efficiency: float | None = None) -> Result:
    """Adam on the Wirtinger gradient of the quadratic intensity loss; ``history[k]`` is the state before step k+1."""
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    phi = C.start_phase(setup, rng, init)
    if target.kind == "traps":
        cost = C.TrapCost(setup, target.traps, device, t=2, efficiency=0.9 if efficiency is None else efficiency)
    else:
        cost = C.FieldCost(setup, target.amplitude, target.mask, device, t=2,
                           efficiency=0.4 if efficiency is None else efficiency)
    history: list = []

    def record(it, x, f, aux):
        if target.kind == "traps":
            history.append(C.trap_history(it, aux, target.traps.weight, t0, loss=f))
        else:
            history.append(C.field_history(it, aux, target.amplitude, target.mask, t0, loss=f))
        return False

    res = C.adam_minimize(cost.value_grad, phi, budget.iterations, lr=lr, callback=record, deadline=deadline)
    phi = res.x
    _, _, fields = cost.value_grad(phi)
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=fields,
                  meta={"lr": lr, "paper_lr": PAPER_LR, "device_aware": device is not None})
