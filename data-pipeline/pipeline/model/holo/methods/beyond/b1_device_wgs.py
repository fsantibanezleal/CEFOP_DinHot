r"""B1 device-aware conjugate-gradient refinement (beyond the state of the art; algorithms dossier D5.1 B1, SDD BS-1).

Named "device-aware weighted GS" until 0.02.003; the id B1 is unchanged. The weight update of weighted GS is an option, off by
default (section "Weights" below).

Gap (dossier D5.1 B1): Schroff et al. 2023 (https://doi.org/10.1038/s41598-023-30296-6) put the crosstalk model into
conjugate gradient on shaped potentials (10 min per hologram, no WGS comparison); Persson, Engstrom, Goksor 2012
(Opt. Express 20, 22334) convolve the phase inside a weighted GS but replace amplitudes only; Kim et al. 2019
(arXiv 1903.09286) and Ebadi et al. 2021 use no device model in the solver and rely on camera feedback.

Method. Warm-start with weighted GS (Di Leonardo et al. 2007 eq (18), ``w_m <- w_m <r> / r_m`` with ``r_m = |V_m| / a_m`` the trap
amplitude relative to its design amplitude), then run ``K`` conjugate-gradient steps per outer iteration on the device-aware loss

.. math::
    L(\phi) = \frac{\sum_m \left(|V_m(\phi)|^2 - T_m\right)^2}{\sum_m T_m^2},\qquad
    T_m = \eta\,\frac{(w_m a_m)^2}{\sum_k (w_k a_k)^2},\quad \eta = \sum_m |V_m|^2 \text{ (current efficiency)},

where ``V = Op(phi)`` runs through the straight-through quantizer, the crosstalk operator ``K * U`` (3 x 3 upsampling,
circular convolution with the Schroff kernel) and the FFT of the upsampled grid, and the pixel-aperture envelope.
The gradient is the closed form of ``_common.FocalForward.adjoint`` (the adjoint of the crosstalk operator is the
convolution with the reversed kernel followed by the sum over each 3 x 3 block): no autodiff, so the TypeScript
port needs no more than the forward model. The target level is the current efficiency ``eta`` (loss ``'efficiency-level'``,
the default), so the steps flatten the traps without trading efficiency away. Fletcher-Reeves CG with a strong-Wolfe line
search restarts at every outer iteration, because the target is set again at each of them (it changes with the weights when
they are on).

Weights (option ``weights``, default False since 0.02.004). ``weights=True`` runs the multiplicative weight update of weighted GS
before every outer iteration, as 0.02.003 did, and reproduces that run exactly (test
``test_weights_true_reproduces_the_run_recorded_before_the_default_changed``). ``weights=False`` keeps every weight at one, so the
steps fit the current efficiency level with equal targets. Reason for the default, measured by the ablation of the
device-aware paper (``manuscripts/device-aware-refinement/data/tab_abl_b1.tex`` and ``tab_abl_b1_full.tex``, five seeds): on
the 10 x 10 acceptance task the median spread without the update is 0.030 percent against 0.205 percent with it (7 times
lower, efficiency ratio 0.999 against 0.995), and on the full device 0.242 against 0.724 percent (3 times lower). On the
benchmark's lattices the result is mixed (below), so the update stays available.

Loss (option ``loss``). ``'efficiency-level'`` (default) is the loss above. ``'normalized-error'`` is the loss of Schroff et al. 2023
(Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6), the closest published method: conjugate gradient through a
fitted crosstalk model with the mean-squared error between the normalized simulated and target intensities, their eq (3),
read on p. 3 of the paper:

.. math::
    C(\phi) = s \sum_{k,l \in S} \left(\tilde T_{kl} - \tilde I_{kl}\right)^2,\qquad
    \tilde I_{kl} = \frac{I_{kl}}{\sum_{k,l \in S} I_{kl}},\quad \tilde T_{kl} = \frac{T_{kl}}{\sum_{k,l \in S} T_{kl}}

with ``s`` the steepness "to aid convergence" (Methods, p. 7: ``s = 1e12`` for their pixel grid). Here ``S`` is the set of target traps and
``I_m = |V_m|^2`` the intensity of trap ``m`` through the same device model, so the two losses run through the same operator, warm start,
conjugate-gradient optimizer, outer-iteration structure and best-iterate safeguard and only the loss and its gradient differ. The
loss is invariant to the total power, so unlike the efficiency-level loss it does not hold the efficiency up; the safeguard does. The
gradient, with ``d_m = T~_m - I~_m`` and ``P = sum_m I_m``, is ``dC/dI_k = (2 s / P) (sum_m d_m I~_m - d_k)``, returned
through the adjoint like the other loss (test: finite differences, ``test_normalized_error_gradient_matches_finite_differences``).
``steepness`` (default ``1 / sum_m T~_m^2``, so that ``C`` is the relative squared error and has the scale of the efficiency-level loss;
Schroff's constant is a pixel-grid scale that only rescales ``C``) is an option. Their target is a continuous light potential
convolved with the point-spread function and their runs use camera feedback; neither enters here: the targets are points.

Start: ``warm`` (default 12, Kim's N) iterations of ideal-model weighted GS from the SR superposition, then
``budget.iterations`` outer iterations of ``steps`` (default 3) CG steps each. Cost per CG step: one forward and one
adjoint evaluation of the upsampled model (about 3x3 the pixels of the plain FFT). ``init`` overrides the warm start.
Reading the traps off the device's focal field uses the nearest FFT bin (traps on bins, z = 0, no vortex).

Safeguard (2026-10-30). The multiplicative weight update is an integrator, and three CG steps per outer iteration may not
follow it on a device whose trap response is quantized and blurred: on the benchmark's square lattice on the C08 device one
seed in two ran away (the loss rose from 0.044 to 0.53 between iterations 2 and 4, the weights spread to a ratio of about
1000 and the efficiency fell from 0.50 to 0.03). B1 therefore returns its best iterate, the warm start included: the phase of
lowest relative standard deviation on its own device model among the iterates that keep at least ``EFFICIENCY_FLOOR`` of the
warm start's efficiency, the ten percent of the claim's own criterion. The history keeps every iterate; ``meta`` names the
returned one (``best_iteration``) and the floor. A run that converges returns its last iterate or one close to it.
Measured on the benchmark's C08 device at 10 iterations (median over three seeds, BL-046, 2026-11-05) the weight update raises the spread on
the square lattice (29 against 14 percent without it, at an efficiency of 0.60 against 0.56), lowers it on the ring of 36 (7.8
against 8.9), and leaves the random and quasi-periodic sets unchanged: no form dominates there.
Equal work (2026-11-14). ``budget.time_s`` is a deadline in every phase: the warm start stops at it (``weighted_gs`` takes the
deadline), the outer loop checks it, and inside a CG run every value-and-gradient evaluation of a line search checks it
(``deadline_fun``), so no phase starts new work once the deadline has passed; the work in progress still finishes, and the
0.02.004 benchmark's 1 s rows of this method on the C08 device end 0.11 to 0.40 s after the deadline (several evaluations of the
device model, not one; the over-budget rule of the report reads them). A run cut by the deadline keeps the
iterates it reached (the last accepted CG point) and the safeguard above still picks the returned one. ``meta['iterations']`` is the
work done, the warm iterations plus the accepted CG steps, and the benchmark row's ``evaluations`` is the engine's count of
forward and adjoint evaluations of the run.
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
from ..optim._gs_family import DeadlineHit, deadline_fun, sr_start, weighted_gs

SPEC = MethodSpec(id="B1", name="Device-aware conjugate-gradient refinement", family="beyond", lane="baked", targets=("traps",),
                  dims=(2,))
DEFAULT_STEPS = 3
DEFAULT_WARM = 12
DEFAULT_OUTER = 4
LOSSES = ("efficiency-level", "normalized-error")
EFFICIENCY_FLOOR = 0.9  # an iterate below this share of the warm start's efficiency is never returned (BS-1's 10 percent)


class NormalizedErrorCost(C.TrapCost):
    """Schroff et al. 2023 eq (3) on the trap intensities: ``C = s sum_m (T_m / sum T - I_m / sum I)^2`` (module docstring).

    Same interface as ``TrapCost``: ``target`` holds the (unnormalized) target levels, ``value_grad(phi)`` returns
    ``(C, dC/dphi, V)`` through the device model. ``steepness`` None: ``1 / sum_m (T_m / sum T)^2``, from the current target.
    """

    def __init__(self, setup: Setup, traps, device: Device | None = None, *, steepness: float | None = None, **kw):
        if steepness is not None and not (np.isfinite(steepness) and steepness > 0):
            raise ValueError(f"steepness must be finite and positive, got {steepness!r}")
        super().__init__(setup, traps, device, **kw)
        self._steepness = steepness

    @property
    def steepness(self) -> float:
        if self._steepness is not None:
            return float(self._steepness)
        t = self.target / np.sum(self.target)
        return float(1.0 / np.sum(t**2))

    def value_grad(self, phi: np.ndarray):
        v, cache = self.fwd.fields(phi)
        i = np.abs(v) ** 2
        p = float(np.sum(i))
        t_n = self.target / np.sum(self.target)
        i_n = i / p
        d = t_n - i_n
        s = self.steepness
        value = float(s * np.sum(d**2))
        g_i = (2.0 * s / p) * (np.sum(d * i_n) - d)           # dC / dI_k
        return value, self.fwd.adjoint(g_i * v, cache), v


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, steps: int = DEFAULT_STEPS, warm: int = DEFAULT_WARM, weights: bool = False,
        loss: str = "efficiency-level", steepness: float | None = None) -> Result:
    """``budget.iterations`` outer iterations of ``steps`` CG steps on the device-aware loss (``weights``: the weight update first)."""
    if target.kind != "traps":
        raise ValueError("B1 supports trap targets only (targets: 'traps'); got a shaped field")
    if steps < 1 or warm < 0:
        raise ValueError("steps must be >= 1 and warm >= 0")
    if loss not in LOSSES:
        raise ValueError(f"unknown loss {loss!r}; use one of {LOSSES}")
    traps = target.traps
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    warm_its = 0
    if init is not None:
        phi = C.start_phase(setup, rng, init)
    elif warm > 0:
        phi, warm_hist = weighted_gs(setup, traps, warm, rng, variant="gsw", deadline=deadline)
        warm_its = len(warm_hist)
    else:
        phi = sr_start(setup, traps, rng)
    loss_kind = loss                 # the loop below reuses the name `loss` for the value of the last CG run
    cost = (C.TrapCost(setup, traps, device, t=2, efficiency=0.9) if loss_kind == "efficiency-level"
            else NormalizedErrorCost(setup, traps, device, steepness=steepness, t=2, efficiency=0.9))
    a = np.sqrt(traps.weight / np.mean(traps.weight))
    w = np.ones(len(traps))
    history: list = []
    evals = 0
    cg_steps = 0
    v, _ = cost.fwd.fields(phi)
    start = C.trap_history(0, v, traps.weight, t0)
    floor = EFFICIENCY_FLOOR * start["efficiency"]
    best = (phi.copy(), v, 0, start["rel_std"])
    for it in range(1, budget.iterations + 1):
        if C.expired(deadline):
            break
        v, _ = cost.fwd.fields(phi)
        if weights:
            r = np.maximum(np.abs(v), 1e-300) / a
            w = w * np.mean(r) / r
        amp2 = (w * a) ** 2
        cost.target = float(np.sum(np.abs(v) ** 2)) * amp2 / amp2.sum()
        accepted: list = []

        def keep(i, x, f, aux, accepted=accepted):
            accepted.append((i, x.copy(), f))
            return False

        cut = False
        try:
            res = C.cg_minimize(deadline_fun(cost.value_grad, deadline), phi, steps, deadline=deadline, callback=keep)
            phi, loss, n_steps = res.x, res.f, res.iterations
            evals += res.evaluations
        except DeadlineHit:      # inside a line search: the last accepted point is the iterate reached
            cut = True
            n_steps = len(accepted)
            if accepted:
                phi, loss = accepted[-1][1], accepted[-1][2]
        cg_steps += n_steps
        if cut and not accepted:
            break
        v, _ = cost.fwd.fields(phi)
        entry = C.trap_history(it, v, traps.weight, t0, loss=loss)
        history.append(entry)
        if entry["efficiency"] >= floor and entry["rel_std"] < best[3]:
            best = (phi.copy(), v, it, entry["rel_std"])
        if cut:
            break
    phi, v, best_it, _ = best
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=v,
                  meta={"iterations": warm_its + cg_steps, "warm_iterations": warm_its, "cg_steps": cg_steps, "steps": steps, "warm": warm, "evaluations": evals, "weights": w.tolist(), "weight_update": weights, "loss": loss_kind,
                        "device_aware": device is not None, "best_iteration": best_it, "efficiency_floor": floor,
                        "start_rel_std": start["rel_std"], "start_efficiency": start["efficiency"]})
