r"""B3: learned warm start for phase-fixed WGS (beyond the state of the art, SDD BS-3), the slot ``warmstart-model``.

A permutation-equivariant set transformer maps the trap list (x and y in focal bins, z in SLM-limited Rayleigh ranges, weight;
up to 1024 traps) to one phase $\theta_m$ per trap. The SLM start is the superposition hologram with those phases,
$$\phi^{(0)}_j = \arg \sum_m \sqrt{w_m}\, e^{\,i(\Delta_j^m + \theta_m)}$$
(the form of M02/``_common.sr_start`` with learned instead of random $\theta_m$), and M07 (phase-fixed WGS, Kim et al. 2019)
runs from it. The network was trained without labels: its loss is the relative standard deviation of the trap intensities along
14 unrolled M07 iterations (a differentiable copy of the rule, checked against M07 in the tests), so what it learns is a start
from which M07 converges sooner; it is not a regression onto converged phases, which are not unique (the global phase and the
many WGS fixed points would make labels ambiguous).

Missing data: with no released model the random trap phases of the portable RNG answer (the M02 start, identical to M07's own
start; ``meta['provenance']`` is ``'baseline'``). ``init`` (a start hologram) overrides the model. Vortex traps and more than
1024 traps are a ``ValueError``. Defaults: ``n_fix=12`` (see ``N_FIX``), ``form='point'`` (the 3D traps need it).
"""
from __future__ import annotations

import numpy as np

from ...core.forward import point_trap_backproject
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ..baseline import m07_phase_fixed_wgs
from ..baseline._common import amp_targets
from . import _slot
from ...learned import convert

N_FIX = 12   # M07's (Kim 2019). Freezing at 3 was measured with the trained candidate and did not help: see the M1 report
SPEC = MethodSpec(id="B3", name="Learned warm start for phase-fixed WGS", family="learned", lane="live", targets=("traps",),
                  dims=(2, 3))


def predict_phases(session, setup, traps) -> np.ndarray:
    """The network's trap phases (float64, length ``len(traps)``)."""
    arr, mask = convert.traps_to_input(setup, traps)
    return session.run(None, {"traps": arr, "mask": mask})[0][0, : len(traps)].astype(np.float64)


def start_hologram(setup, traps, theta: np.ndarray) -> np.ndarray:
    return np.angle(point_trap_backproject(amp_targets(traps) * np.exp(1j * theta), setup, traps))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, n_fix: int = N_FIX, form: str = "point",
        models_dir=None) -> Result:
    if target.kind != "traps":
        raise ValueError(f"{SPEC.id} supports the target kinds ['traps'], got {target.kind!r}")
    traps = target.traps
    provenance = "given"
    if init is None:
        slot = _slot.load("warmstart-model", models_dir)
        if slot is None:
            provenance, init = "baseline", None   # M07 draws the random start itself, from the same stream
        else:
            provenance, init = "real", start_hologram(setup, traps, predict_phases(slot[0], setup, traps))
    res = m07_phase_fixed_wgs.run(setup, target, budget=budget, rng=rng, init=init, n_fix=n_fix, form=form)
    res.meta.update({"method": SPEC.id, "provenance": provenance})
    return res
