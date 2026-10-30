"""Gerchberg-Saxton family in the point-trap form, used inside E3's beyond methods and as the in-test baselines.

This is the loop that B1, B2, B4 and B5 build on and are compared with. Each variant runs the rule of the registered
ladder method (M04, M05, M06, M07) through the engine's own loop (``baseline/_gs.py``, point form), so the baselines and warm
starts of the beyond methods are those methods, and a correction of a rule (2026-10-29: M06 and M07 project the start's
field unweighted, as slmsuite does) reaches them at once.

With ``V_m`` the trap fields (``core/forward.py``), ``a_m = sqrt(w_m / mean(w))`` the design amplitudes and
``r_m = |V_m| / a_m``, one iteration computes the coefficients ``c_m`` and the new phase
``phi_j = arg sum_m c_m exp(+i Delta_j^m)`` (``point_trap_backproject``; the dossier writes ``e^{-i delta}`` in the
convention where ``V`` carries ``e^{+i delta}``; the physical condition is the adjoint pair of ``core/forward.py``):

- ``gs`` (Gerchberg and Saxton 1972; Di Leonardo et al. 2007): ``c_m = a_m V_m / |V_m|``.
- ``gaa`` (generalized adaptive additive, Di Leonardo et al. 2007 eq (16), R2 D3.4):
  ``c_m = a_m (V_m / |V_m|) [(1 - alpha) + alpha <r> / r_m]`` with ``alpha = 0.5``. UNVERIFIED: the dossier prints the
  bracket as ``(1 - alpha) + alpha / |V_m|``; the ratio ``<r> / r_m`` is the dimensionless reading used here.
- ``gsw`` (weighted GS, Di Leonardo et al. 2007 eq (18), D1.2): ``w_m <- w_m <r> / r_m`` from the second iteration on,
  then ``c_m = w_m a_m V_m / |V_m|``.
- ``pfwgs`` (phase-fixed WGS, Kim et al. 2019, D1.3): as ``gsw`` (``g_0 = 1``), and at iteration ``n_fix`` (Kim used 12) the
  trap phases ``theta_m = arg V_m`` are frozen, ``c_m = w_m a_m e^{i theta_m}``, while the weights keep updating.

Every variant starts from the superposition of random-phase prisms and lenses (SR: ``phi = arg sum_m e^{i(Delta^m +
theta_m)}``, ``theta_m`` uniform from ``rng``; Di Leonardo et al. 2007).
"""
from __future__ import annotations

import numpy as np

from ...core.forward import point_trap_backproject
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget
from ..baseline import _gs

VARIANTS = ("gs", "gaa", "gsw", "pfwgs")


def sr_start(setup: Setup, traps: TrapSet, rng: Rng) -> np.ndarray:
    """Random superposition (SR) phase: ``arg sum_m exp(i (Delta_j^m + theta_m))`` with random ``theta_m``."""
    theta = rng.phases(len(traps))
    return np.angle(point_trap_backproject(np.exp(1j * theta), setup, traps))


def weighted_gs(setup: Setup, traps: TrapSet, iterations: int, rng: Rng, *, variant: str = "gsw", alpha: float = 0.5,
                n_fix: int = 12, init: np.ndarray | None = None) -> tuple[np.ndarray, list]:
    """Run ``iterations`` iterations of the chosen variant in the point-trap form; returns ``(phi, history)``.

    Each variant is the registered method's own rule run by the same loop (``baseline/_gs.py``): ``gs`` is M04,
    ``gaa`` M05 (``scale='mean'``), ``gsw`` M06 and ``pfwgs`` M07, so a beyond method's baseline or warm start is the
    ladder method itself, never a second copy of its equations. ``init`` is a starting phase (None: the SR start drawn from
    ``rng``). ``history[k]`` describes the hologram after ``k + 1`` iterations (keys of ``core.types.HISTORY_KEYS``).
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; use one of {VARIANTS}")
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    rule, state = {
        "gs": (_gs.rule_gs, {}),
        "gaa": (_gs.rule_gaa, {"alpha": float(alpha), "scale": "mean"}),
        "gsw": (_gs.rule_gsw, {}),
        "pfwgs": (_gs.rule_wgs_fixed, {"n_fix": int(n_fix)}),
    }[variant]
    res = _gs.run_traps(f"gs-family:{variant}", setup, traps, Budget(iterations), rng, init, "point", rule, state)
    return res.phi, res.history
