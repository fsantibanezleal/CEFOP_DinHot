"""Gerchberg-Saxton family in the point-trap form, used inside E3's beyond methods and as the in-test baselines.

This is the reference loop that B1, B2, B4 and B5 build on and are compared with. The registered, benchmarked
versions of these baselines are unit E2's modules (M04, M05, M06, M07); this module implements the same equations
from the dossier text so that E3 is independent of E2's branch (the main session re-runs the comparisons against E2's
modules after the merge).

With ``V_m`` the trap fields (``core/forward.py``), ``a_m = sqrt(w_m / mean(w))`` the design amplitudes and
``r_m = |V_m| / a_m``, one iteration computes the coefficients ``c_m`` and the new phase
``phi_j = arg sum_m c_m exp(+i Delta_j^m)`` (``point_trap_backproject``; the dossier writes ``e^{-i delta}`` in the
convention where ``V`` carries ``e^{+i delta}``; the physical condition is the adjoint pair of ``core/forward.py``):

- ``gs`` (Gerchberg and Saxton 1972; Di Leonardo et al. 2007): ``c_m = a_m V_m / |V_m|``.
- ``gaa`` (generalized adaptive additive, Di Leonardo et al. 2007 eq (16), R2 D3.4):
  ``c_m = a_m (V_m / |V_m|) [(1 - alpha) + alpha <r> / r_m]`` with ``alpha = 0.5``. UNVERIFIED: the dossier prints the
  bracket as ``(1 - alpha) + alpha / |V_m|``; the ratio ``<r> / r_m`` is the dimensionless reading used here.
- ``gsw`` (weighted GS, Di Leonardo et al. 2007 eq (18), D1.2): ``w_m <- w_m <r> / r_m`` then
  ``c_m = w_m a_m V_m / |V_m|``.
- ``pfwgs`` (phase-fixed WGS, Kim et al. 2019, D1.3): as ``gsw`` for ``n_fix`` iterations (Kim used 12), then the trap
  phases ``theta_m = arg V_m`` are frozen and ``c_m = w_m a_m e^{i theta_m}`` while the weights keep updating.

Every variant starts from the superposition of random-phase prisms and lenses (SR: ``phi = arg sum_m e^{i(Delta^m +
theta_m)}``, ``theta_m`` uniform from ``rng``; Di Leonardo et al. 2007).
"""
from __future__ import annotations

import time

import numpy as np

from ...core.forward import point_trap_backproject, point_trap_projection, slm_field
from ...core.geometry import Setup
from ...core.rng import Rng
from ...core.traps import TrapSet
from ._common import trap_history

VARIANTS = ("gs", "gaa", "gsw", "pfwgs")


def sr_start(setup: Setup, traps: TrapSet, rng: Rng) -> np.ndarray:
    """Random superposition (SR) phase: ``arg sum_m exp(i (Delta_j^m + theta_m))`` with random ``theta_m``."""
    theta = rng.phases(len(traps))
    return np.angle(point_trap_backproject(np.exp(1j * theta), setup, traps))


def weighted_gs(setup: Setup, traps: TrapSet, iterations: int, rng: Rng, *, variant: str = "gsw", alpha: float = 0.5,
                n_fix: int = 12, init: np.ndarray | None = None) -> tuple[np.ndarray, list]:
    """Run ``iterations`` iterations of the chosen variant; returns ``(phi, history)``.

    ``init`` is a starting phase (None: SR drawn from ``rng``). ``history[k]`` describes the hologram after ``k + 1``
    iterations (keys of ``core.types.HISTORY_KEYS``).
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; use one of {VARIANTS}")
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    t0 = time.perf_counter()
    a = np.sqrt(traps.weight / np.mean(traps.weight))
    w = np.ones(len(traps))
    theta = None
    phi = sr_start(setup, traps, rng) if init is None else np.asarray(init, dtype=np.float64).copy()
    history = []
    for k in range(1, iterations + 1):
        v = point_trap_projection(slm_field(phi, setup), setup, traps)
        mag = np.maximum(np.abs(v), 1e-300)
        r = mag / a
        unit = v / mag
        if variant == "gs":
            c = a * unit
        elif variant == "gaa":
            c = a * unit * ((1.0 - alpha) + alpha * np.mean(r) / r)
        else:
            w = w * np.mean(r) / r
            if variant == "pfwgs" and k > n_fix:
                if theta is None:
                    theta = np.exp(1j * np.angle(v))           # phases of the hologram after iteration n_fix
                c = w * a * theta
            else:
                c = w * a * unit
        phi = np.angle(point_trap_backproject(c, setup, traps))
        v_new = point_trap_projection(slm_field(phi, setup), setup, traps)
        history.append(trap_history(k, v_new, traps.weight, t0))
    return phi, history
