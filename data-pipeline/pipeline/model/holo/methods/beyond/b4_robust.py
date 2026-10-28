r"""B4 aberration- and pointing-robust hologram by expected-cost optimisation (dossier D5.1 B4, SDD BS-4).

Gap: aberrations vary across the field and are corrected per site (Zernike per trap) or with one global set
(Ebadi et al. 2021, Manetsch et al. 2025); no source optimises the hologram for a *distribution* of residual
aberration or pointing error (arXiv 2512.15967 is the nearest, per the SDD).

Method. Minimise the sample-average loss over residual Zernike coefficients ``a_k ~ N(0, s_a^2)`` (Noll 4 to 11,
waves, piston and tilts excluded) and independent trap displacements ``d_m ~ N(0, s_p^2)`` in x and y,

.. math:: \min_\phi \frac1Q \sum_{q=1}^{Q} L\big(\phi + 2\pi W(a^{(q)});\ x + d^{(q)}\big),\qquad
          L = \frac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2},

where ``W`` is the wavefront (``core.zernike.phase_from_coeffs``) added to the SLM phase as in the total-phase sum of
Nogrette et al. 2014 (dossier S9) and ``T_m = 0.95 e_nom w_m / sum w`` with ``e_nom`` the efficiency of the starting
hologram. ``Q`` samples (default 8; dossier: 8 to 32) are *resampled at every iteration* from the seeded ``rng``, so the
run is a stochastic-gradient method: Adam (``lr = 0.02``) on the closed-form gradients of ``_common.TrapCost`` (one
point-trap forward and adjoint per sample; the perturbed trap set changes the delays, the aberration is a phase
offset, so ``dL/dphi`` is the unperturbed formula evaluated at the shifted phase). The inner solver of the dossier is
phase-fixed WGS: it produces the starting hologram (``warm`` iterations, Kim's 12 fixed phases), which the
expected-cost steps then refine. Cost: ``Q`` times one WGS iteration per step.

``ensemble_stats`` evaluates a hologram over a seeded perturbation ensemble (default 200 samples): mean efficiency and
the relative standard deviation ``sigma`` of ``I_m / w_m`` per sample (95th percentile reported). Perturbation
priors are device dependent (dossier risk); the defaults ``s_a = 0.02`` waves per mode (rms 0.057 waves over the 8
modes, Strehl about 0.88) and ``s_p = 0.15`` FFT bin are this unit's choice, stated, not sourced.
"""
from __future__ import annotations

import time
from dataclasses import replace

import numpy as np

from ...core.device import Device
from ...core.forward import point_trap_projection, slm_field
from ...core.geometry import Setup, focal_bin_m
from ...core.metrics import efficiency, rel_std, trap_intensities
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ...core.zernike import phase_from_coeffs
from ..optim import _common as C
from ..optim._gs_family import weighted_gs

SPEC = MethodSpec(id="B4", name="Aberration- and pointing-robust hologram", family="beyond", lane="baked",
                  targets=("traps",), dims=(2,))
DEFAULT_ABERRATION = 0.02
DEFAULT_POINTING_BINS = 0.15
DEFAULT_Q = 8
DEFAULT_LR = 0.02
DEFAULT_WARM = 30


def sample_perturbation(setup: Setup, traps: TrapSet, rng: Rng, aberration: float = DEFAULT_ABERRATION,
                        pointing_bins: float = DEFAULT_POINTING_BINS) -> tuple[np.ndarray, TrapSet]:
    """One draw: the aberration phase on the SLM grid (Noll 4 to 11) and the displaced trap set (x, y per trap)."""
    c = np.zeros(11)
    c[3:11] = aberration * rng.normal_array(8)
    ab = phase_from_coeffs(c, setup)
    b = pointing_bins * focal_bin_m(setup)
    dx, dy = b * rng.normal_array(len(traps)), b * rng.normal_array(len(traps))
    moved = TrapSet(replace(t, x_m=t.x_m + dx[i], y_m=t.y_m + dy[i]) for i, t in enumerate(traps))
    return ab, moved


def ensemble_stats(setup: Setup, phi: np.ndarray, traps: TrapSet, *, seed: int = 999, n: int = 200,
                   aberration: float = DEFAULT_ABERRATION, pointing_bins: float = DEFAULT_POINTING_BINS) -> dict:
    """Efficiency and relative std over ``n`` seeded perturbations (the hologram evaluated at the displaced traps)."""
    rng = Rng(seed)
    eff, sig = [], []
    for _ in range(n):
        ab, moved = sample_perturbation(setup, traps, rng, aberration, pointing_bins)
        i = trap_intensities(point_trap_projection(slm_field(phi + ab, setup), setup, moved))
        eff.append(efficiency(i))
        sig.append(rel_std(i / traps.weight))
    sig = np.array(sig)
    return {"efficiency_mean": float(np.mean(eff)), "sigma_p95": float(np.percentile(sig, 95)),
            "sigma_mean": float(sig.mean()), "sigmas": sig}


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, q: int = DEFAULT_Q, lr: float = DEFAULT_LR, warm: int = DEFAULT_WARM,
        aberration: float = DEFAULT_ABERRATION, pointing_bins: float = DEFAULT_POINTING_BINS) -> Result:
    """``budget.iterations`` stochastic expected-cost steps from a phase-fixed WGS start (module docstring)."""
    if target.kind != "traps":
        raise ValueError("B4 supports trap targets only (targets: 'traps'); got a shaped field")
    if q < 1:
        raise ValueError("q must be >= 1")
    traps = target.traps
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    if init is not None:
        phi0 = C.start_phase(setup, rng, init)
    else:
        phi0, _ = weighted_gs(setup, traps, warm, rng, variant="pfwgs")
    v0 = point_trap_projection(slm_field(phi0, setup), setup, traps)
    level = 0.95 * efficiency(trap_intensities(v0))
    history: list = []

    def fun(x):
        total, grad = 0.0, 0.0
        for _ in range(q):
            ab, moved = sample_perturbation(setup, traps, rng, aberration, pointing_bins)
            cost = C.TrapCost(setup, moved, t=2, efficiency=level)
            val, g, _ = cost.value_grad(x + ab)
            total += val / q
            grad = grad + g / q
        return total, grad, None

    def record(it, x, f, aux):
        v = point_trap_projection(slm_field(x, setup), setup, traps)
        history.append(C.trap_history(it, v, traps.weight, t0, loss=f))
        return False

    res = C.adam_minimize(fun, phi0, budget.iterations, lr=lr, callback=record, deadline=deadline)
    phi = res.x
    v = point_trap_projection(slm_field(phi, setup), setup, traps)
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=v,
                  meta={"q": q, "lr": lr, "aberration": aberration, "pointing_bins": pointing_bins,
                        "start_phi": np.mod(phi0, 2.0 * np.pi), "level": level})
