r"""B4 aberration-robust hologram by expected-cost optimisation (dossier D5.1 B4, SDD BS-4, narrowed by the main session).

Claim (narrowed 2026-10-28): robustness against *residual aberrations*. Pointing robustness is available as an option
(default off) and is reported as a measured negative result, not claimed.

Gap: aberrations vary across the field and are corrected per site (Zernike per trap) or with one global set
(Ebadi et al. 2021, Manetsch et al. 2025); no source optimises the hologram for a *distribution* of residual
aberration (arXiv 2512.15967 is the nearest, per the SDD).

Method. Minimise the expected loss over residual Zernike coefficients ``a_k ~ N(0, s_a^2)`` (Noll 4 to 11, waves,
piston and tilts excluded),

.. math:: \min_\phi \; \mathbb E_a\, Lig(\phi + 2\pi W(a)ig),\qquad
          L = rac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2},

with ``W`` the wavefront (``core.zernike.phase_from_coeffs``) added to the SLM phase as in the total-phase sum of
Nogrette et al. 2014 (dossier S9) and ``T_m = 0.9 e_nom w_m / sum w`` (``e_nom``: efficiency of the starting hologram).
Default design ``"sigma"``: the expectation is replaced by a deterministic sigma-point set, ``+-s_a sqrt(8)`` on one mode at
a time (16 points, covariance exactly ``s_a^2 I``), so the loss has no sampling noise and Fletcher-Reeves CG with a
strong-Wolfe line search converges on it (``_common.cg_minimize``). Design ``"sample"`` (used automatically when
``pointing_bins > 0``): ``Q`` seeded random draws (default 8, dossier 8 to 32) resampled at every iteration, Adam
(``lr = 0.02``), with independent trap displacements ``d_m ~ N(0, s_p^2)`` in x and y added to each draw. Gradients are the
closed form of ``_common.TrapCost`` (the aberration is a phase offset, so ``dL/dphi`` is the unperturbed formula at the
shifted phase). The inner solver is phase-fixed WGS (``warm`` = 30 iterations, Kim's 12 fixed phases; ``level_fraction`` = 0.9 sets the target level), whose hologram
starts the expected-cost steps.

Measured (10x10 task, 256 pixels, 200-sample ensemble, seed 999; ``ensemble_stats``): see the E3 report D4 and
``test_b4_robust.py``. Aberration-only (0.02 waves per mode, rms 0.057 waves, Strehl about 0.88): p95 sigma of the
nominal phase-fixed WGS 6.27 percent, robust 4.05 percent (1.55x, 40 CG iterations, target level 0.9 of the starting
efficiency), mean efficiency 0.717 to 0.703 (-1.9 percent). A level of 0.937 gave 4.89 percent (1.28x), 0.95 with 80
iterations 5.10 percent (1.23x): the level trades a little efficiency for robustness. With a 0.15 bin pointing error added
the p95 falls only from 7.46 to 7.31 percent (1.02x): a displaced trap loses intensity in proportion to the curvature
of its spot, which the spot width fixes, and halving the loss needs a spot 1.4x wider, i.e. about half the peak
efficiency. That is why pointing robustness is not claimed.
Perturbation priors are device dependent (dossier risk); ``s_a = 0.02`` waves per mode is this unit's choice, stated,
not sourced.
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
DEFAULT_POINTING_BINS = 0.0
DEFAULT_Q = 8
DEFAULT_LR = 0.02
DEFAULT_WARM = 30
DEFAULT_LEVEL_FRACTION = 0.9


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


def sigma_point_phases(setup: Setup, aberration: float = DEFAULT_ABERRATION) -> list[np.ndarray]:
    """The 16 sigma-point aberration phases: ``+-aberration * sqrt(8)`` waves on one of Noll 4 to 11 at a time
    (mean zero, covariance ``aberration^2 I`` over the 8 modes)."""
    out = []
    for k in range(3, 11):
        for sg in (1.0, -1.0):
            c = np.zeros(11)
            c[k] = sg * aberration * np.sqrt(8.0)
            out.append(phase_from_coeffs(c, setup))
    return out


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
        aberration: float = DEFAULT_ABERRATION, pointing_bins: float = DEFAULT_POINTING_BINS,
        design: str | None = None, level_fraction: float = DEFAULT_LEVEL_FRACTION) -> Result:
    """``budget.iterations`` expected-cost steps from a phase-fixed WGS start (module docstring).

    ``design`` is ``"sigma"`` (deterministic sigma points, CG; aberration only, the default when ``pointing_bins`` is 0)
    or ``"sample"`` (random draws, Adam; the default when ``pointing_bins > 0``).
    """
    if target.kind != "traps":
        raise ValueError("B4 supports trap targets only (targets: 'traps'); got a shaped field")
    if q < 1:
        raise ValueError("q must be >= 1")
    design = ("sigma" if pointing_bins == 0 else "sample") if design is None else design
    if design not in ("sigma", "sample"):
        raise ValueError("design must be 'sigma' or 'sample'")
    if design == "sigma" and pointing_bins != 0:
        raise ValueError("the sigma-point design covers aberrations only; use design='sample' with pointing_bins > 0")
    traps = target.traps
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    if init is not None:
        phi0 = C.start_phase(setup, rng, init)
    else:
        phi0, _ = weighted_gs(setup, traps, warm, rng, variant="pfwgs")
    v0 = point_trap_projection(slm_field(phi0, setup), setup, traps)
    level = level_fraction * efficiency(trap_intensities(v0))
    history: list = []
    points = sigma_point_phases(setup, aberration)

    def fun_sigma(x):
        cost = C.TrapCost(setup, traps, t=2, efficiency=level)
        total, grad = 0.0, 0.0
        for ab in points:
            val, g, _ = cost.value_grad(x + ab)
            total += val / len(points)
            grad = grad + g / len(points)
        return total, grad, None

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

    if design == "sigma":
        res = C.cg_minimize(fun_sigma, phi0, budget.iterations, callback=record, deadline=deadline)
    else:
        res = C.adam_minimize(fun, phi0, budget.iterations, lr=lr, callback=record, deadline=deadline)
    phi = res.x
    v = point_trap_projection(slm_field(phi, setup), setup, traps)
    return Result(phi=np.mod(phi, 2.0 * np.pi), history=history, fields=v,
                  meta={"design": design, "q": q, "lr": lr, "aberration": aberration, "pointing_bins": pointing_bins,
                        "start_phi": np.mod(phi0, 2.0 * np.pi), "level": level})
