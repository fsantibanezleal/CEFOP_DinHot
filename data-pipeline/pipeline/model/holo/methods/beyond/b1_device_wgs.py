r"""B1 device-aware weighted Gerchberg-Saxton (beyond the state of the art; algorithms dossier D5.1 B1, SDD BS-1).

Gap (dossier D5.1 B1): Schroff et al. 2023 (https://doi.org/10.1038/s41598-023-30296-6) put the crosstalk model into
conjugate gradient on shaped potentials (10 min per hologram, no WGS comparison); Persson, Engstrom, Goksor 2012
(Opt. Express 20, 22334) convolve the phase inside a weighted GS but replace amplitudes only; Kim et al. 2019
(arXiv 1903.09286) and Ebadi et al. 2021 use no device model in the solver and rely on camera feedback.

Method. Keep the weights of Di Leonardo et al. 2007 eq (18), ``w_m <- w_m <r> / r_m`` with ``r_m = |V_m| / a_m`` the
trap amplitude relative to its design amplitude, measured on the *device's* focal field. Replace the projection
``phi_j = arg sum_m c_m e^{+i Delta_j^m}`` of the phase update by ``K`` conjugate-gradient steps on the device-aware
loss

.. math::
    L(\phi) = \frac{\sum_m \left(|V_m(\phi)|^2 - T_m\right)^2}{\sum_m T_m^2},\qquad
    T_m = \eta\,\frac{(w_m a_m)^2}{\sum_k (w_k a_k)^2},\quad \eta = \sum_m |V_m|^2 \text{ (current efficiency)},

where ``V = Op(phi)`` runs through the straight-through quantizer, the crosstalk operator ``K * U`` (3 x 3 upsampling,
circular convolution with the Schroff kernel) and the FFT of the upsampled grid, and the pixel-aperture envelope.
The gradient is the closed form of ``_common.FocalForward.adjoint`` (the adjoint of the crosstalk operator is the
convolution with the reversed kernel followed by the sum over each 3 x 3 block): no autodiff, so the TypeScript
port needs no more than the forward model. The target level is the current efficiency ``eta``, so the steps
flatten the traps without trading efficiency away; the weights supply the integral feedback that the few steps
per iteration lack (a pure one-shot fit would need many more steps). Fletcher-Reeves CG with a strong-Wolfe line
search restarts at every outer iteration, because the target changes with the weights.

Start: ``warm`` (default 12, Kim's N) iterations of ideal-model weighted GS from the SR superposition, then
``budget.iterations`` outer iterations of ``steps`` (default 3) CG steps each. Cost per CG step: one forward and one
adjoint evaluation of the upsampled model (about 3x3 the pixels of the plain FFT). ``init`` overrides the warm start.
Reading the traps off the device's focal field uses the nearest FFT bin (traps on bins, z = 0, no vortex).
Defaults and measured numbers: tests ``test_b1_device_wgs.py`` and the E3 report.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.device import Device
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ..optim import _common as C
from ..optim._gs_family import sr_start, weighted_gs

SPEC = MethodSpec(id="B1", name="Device-aware weighted GS", family="beyond", lane="baked", targets=("traps",),
                  dims=(2,))
DEFAULT_STEPS = 3
DEFAULT_WARM = 12
DEFAULT_OUTER = 4


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, steps: int = DEFAULT_STEPS, warm: int = DEFAULT_WARM) -> Result:
    """``budget.iterations`` outer iterations of weight update plus ``steps`` CG steps on the device-aware loss."""
    if target.kind != "traps":
        raise ValueError("B1 supports trap targets only (targets: 'traps'); got a shaped field")
    if steps < 1 or warm < 0:
        raise ValueError("steps must be >= 1 and warm >= 0")
    traps = target.traps
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    if init is not None:
        phi = C.start_phase(setup, rng, init)
    elif warm > 0:
        phi, _ = weighted_gs(setup, traps, warm, rng, variant="gsw")
    else:
        phi = sr_start(setup, traps, rng)
    cost = C.TrapCost(setup, traps, device, t=2, efficiency=0.9)
    a = np.sqrt(traps.weight / np.mean(traps.weight))
    w = np.ones(len(traps))
    history: list = []
    evals = 0
    v = None
    for it in range(1, budget.iterations + 1):
        if C.expired(deadline):
            break
        v, _ = cost.fwd.fields(phi)
        r = np.maximum(np.abs(v), 1e-300) / a
        w = w * np.mean(r) / r
        amp2 = (w * a) ** 2
        cost.target = float(np.sum(np.abs(v) ** 2)) * amp2 / amp2.sum()
        res = C.cg_minimize(cost.value_grad, phi, steps, deadline=deadline)
        phi = res.x
        evals += res.evaluations
        v, _ = cost.fwd.fields(phi)
        history.append(C.trap_history(it, v, traps.weight, t0, loss=res.f))
    if v is None:
        v, _ = cost.fwd.fields(phi)
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=v,
                  meta={"steps": steps, "warm": warm, "evaluations": evals, "weights": w.tolist(),
                        "device_aware": device is not None})
