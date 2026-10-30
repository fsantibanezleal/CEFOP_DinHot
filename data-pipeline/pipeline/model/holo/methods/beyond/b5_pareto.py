r"""B5 efficiency-uniformity Pareto front by continuation (algorithms dossier D5.1 B5, SDD BS-5).

Gap: every method trades efficiency against uniformity and reports single points (Di Leonardo et al. 2007: DS at
``f = 0.5`` and ``0.25``, GAA at 0.5; Polin et al. 2005 use one scalar weight ``f``; MRAF one mixing parameter); no
source reports a whole front on the same task.

Method. Continuation over ``lambda`` in [0, 1] of the loss

.. math::
    L_\lambda(\phi) = (1-\lambda)\,\frac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2} \;-\; \lambda\,\frac{\sum_m I_m}{e_0},
    \qquad T_m = e_0\, \frac{w_m}{\sum_k w_k},

with ``I_m = |V_m|^2`` and ``e_0`` the efficiency of the weighted-GS hologram at the uniform end. The dossier writes
``(1-\lambda)\sum(|V|^2 - w_m T_m)^2 - \lambda\sum|V|^2``; the two terms are divided by ``\sum T^2`` and ``e_0`` so that
both are dimensionless and of order one (UNVERIFIED reading: the dossier does not state the scaling). The start
(``lambda = 0``) is phase-fixed WGS (Kim 2019: Di Leonardo's GSW point ``e = 0.93``, ``u = 0.99`` on flat
illumination), refined by the same CG; each next ``lambda`` is warm-started from its neighbour and solved with
``budget.iterations`` Fletcher-Reeves/strong-Wolfe CG iterations (``_common.cg_minimize``). The gradient is the
closed form ``G_m = [2(1-\lambda)(I_m - T_m)/\sum T^2 - \lambda/e_0]\, V_m`` pulled back by the point-trap adjoint
(any trap z and vortex charge; the ideal device). ``run`` returns the point with the largest ``e * u`` (the knee of the
front) as ``phi``, and in ``meta``: ``lambdas``, ``front`` (the (e, u, sigma) of every lambda), ``pareto`` (indices of the
non-dominated points), ``hypervolume`` against the reference point (0, 0) and ``phis`` (all holograms). ``hypervolume``
and ``pareto_indices`` are public for the benchmark.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.device import Device
from ...core.geometry import Setup
from ...core.metrics import efficiency, rel_std, trap_intensities, uniformity
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ..optim import _common as C
from ..optim._gs_family import weighted_gs

SPEC = MethodSpec(id="B5", name="Efficiency-uniformity Pareto front", family="beyond", lane="baked",
                  targets=("traps",), dims=(2, 3))
DEFAULT_LAMBDAS = 20
DEFAULT_WARM = 30


def pareto_indices(points: np.ndarray) -> list[int]:
    """Indices of the non-dominated rows of ``points`` (columns maximised: efficiency, uniformity)."""
    pts = np.asarray(points, dtype=np.float64)
    keep = []
    for i, p in enumerate(pts):
        dominated = np.any(np.all(pts >= p, axis=1) & np.any(pts > p, axis=1))
        if not dominated:
            keep.append(i)
    return keep


def hypervolume(points: np.ndarray, ref: tuple[float, float] = (0.0, 0.0)) -> float:
    """Area of the union of the rectangles ``[ref, p]`` over the points ``p = (e, u)`` (both maximised)."""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    pts = pts[(pts[:, 0] > ref[0]) & (pts[:, 1] > ref[1])]
    if pts.size == 0:
        return 0.0
    order = np.argsort(-pts[:, 0])
    area, best_u = 0.0, ref[1]
    xs = pts[order, 0]
    us = pts[order, 1]
    for k in range(len(xs)):
        best_u = max(best_u, us[k])
        nxt = xs[k + 1] if k + 1 < len(xs) else ref[0]
        area += (xs[k] - max(nxt, ref[0])) * (best_u - ref[1])
    return float(area)


class _FrontCost:
    """``L_lambda`` of the module docstring with its gradient."""

    def __init__(self, setup: Setup, traps: TrapSet, e0: float):
        self.fwd = C.TrapForward(setup, traps)
        self.e0 = e0
        self.target = e0 * traps.weight / np.sum(traps.weight)
        self.tt = float(np.sum(self.target**2))
        self.lam = 0.0

    def value_grad(self, phi: np.ndarray):
        v, cache = self.fwd.fields(phi)
        i = np.abs(v) ** 2
        d = i - self.target
        lam = self.lam
        value = (1.0 - lam) * float(np.sum(d**2)) / self.tt - lam * float(np.sum(i)) / self.e0
        g_i = 2.0 * (1.0 - lam) * d / self.tt - lam / self.e0
        return value, self.fwd.adjoint(g_i * v, cache), v


def run(setup: Setup, target: Target, *, device: Device | None = None, budget: Budget, rng: Rng,
        init: np.ndarray | None = None, n_lambda: int = DEFAULT_LAMBDAS, warm: int = DEFAULT_WARM) -> Result:
    """The front over ``n_lambda`` values of ``lambda`` in [0, 1]; ``budget.iterations`` CG iterations per value."""
    if target.kind != "traps":
        raise ValueError("B5 supports trap targets only (targets: 'traps'); got a shaped field")
    if n_lambda < 2:
        raise ValueError("n_lambda must be >= 2")
    traps = target.traps
    t0 = time.perf_counter()
    deadline = C.deadline_of(budget.time_s)
    if init is not None:
        phi = C.start_phase(setup, rng, init)
    else:
        phi, _ = weighted_gs(setup, traps, warm, rng, variant="pfwgs")
    fwd = C.TrapForward(setup, traps)
    v, _ = fwd.fields(phi)
    cost = _FrontCost(setup, traps, efficiency(trap_intensities(v)))
    lambdas = np.linspace(0.0, 1.0, n_lambda)
    phis, front, history = [], [], []
    for k, lam in enumerate(lambdas):
        if C.expired(deadline) and k > 0:
            lambdas = lambdas[:k]
            break
        cost.lam = float(lam)
        res = C.cg_minimize(cost.value_grad, phi, budget.iterations, deadline=deadline)
        phi = res.x
        v, _ = fwd.fields(phi)
        iw = trap_intensities(v, traps.weight)
        front.append((efficiency(trap_intensities(v)), uniformity(iw), rel_std(iw)))
        phis.append(np.mod(phi, 2.0 * np.pi))
        history.append(C.trap_history(k + 1, v, traps.weight, t0, lam=float(lam)))
    front_a = np.array(front)
    knee = int(np.argmax(front_a[:, 0] * front_a[:, 1]))
    v_knee, _ = fwd.fields(phis[knee])
    return Result(phi=phis[knee], history=history, fields=v_knee,
                  meta={"lambdas": lambdas.tolist(), "front": front_a, "pareto": pareto_indices(front_a[:, :2]),
                        "hypervolume": hypervolume(front_a[:, :2]), "knee": knee, "phis": np.array(phis),
                        "e0": cost.e0})
