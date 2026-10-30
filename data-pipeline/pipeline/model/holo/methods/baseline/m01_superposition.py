r"""M01: superposition of prisms and lenses (analytic baseline).

Update rule (dossier D1.1, Di Leonardo, Ianni and Ruocco 2007, https://doi.org/10.1364/OE.15.001913, Table 1):

$$\phi_j = \arg \sum_m \sqrt{w_m}\, e^{\,i \Delta_j^m}$$

with ``Delta_j^m`` the single-trap delay of ``core.forward`` (lens, grating and optional vortex terms) and ``w_m`` the target
weight of the trap (all 1 in the paper). Cost ``N x M``. No randomness: ``rng`` is unused and the result is identical for
every seed. Published on the 10x10 task: e = 0.29, u = 0.01, sigma = 257 percent (768 x 768, 8 bit). Defaults: none.
"""
from __future__ import annotations

import numpy as np

from ...core.forward import point_trap_backproject, point_trap_fields
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ._common import Recorder, amp_targets, require_kinds

SPEC = MethodSpec(id="M01", name="Superposition of prisms and lenses", family="analytic", lane="live",
                  targets=("traps",), dims=(2, 3))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    traps = target.traps
    rec = Recorder(budget, traps.weight)
    phi = np.angle(point_trap_backproject(amp_targets(traps), setup, traps))
    v = point_trap_fields(phi, setup, traps)
    rec.add(1, v)
    return Result(phi=phi, history=rec.history, fields=v, meta={"method": SPEC.id})
