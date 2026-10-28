r"""M02: random superposition (SR), the analytic baseline with random trap phases.

Update rule (dossier D1.1, Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913, Table 1; Bianchi and Di Leonardo
2010, https://arxiv.org/abs/0907.4027):

$$\phi_j = \arg \sum_m \sqrt{w_m}\, e^{\,i (\Delta_j^m + \theta_m)},\qquad \theta_m \sim U[0, 2\pi)$$

The phases ``theta_m`` are drawn through ``rng``. Published on the 10x10 task: e = 0.69, u = 0.01, sigma = 89 percent.
DinHot's grid (256 x 256, Gaussian beam) measures e about 0.75 and u about 0.25: the intensity spread is intrinsic to the
method (about 35 percent whatever N and the beam), the gap to the published u is reported in the E2 report. Defaults: none.
"""
from __future__ import annotations

import numpy as np

from ...core.forward import point_trap_fields
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ._common import Recorder, require_kinds, sr_start

SPEC = MethodSpec(id="M02", name="Random superposition", family="analytic", lane="live",
                  targets=("traps",), dims=(2, 3))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    traps = target.traps
    rec = Recorder(budget, traps.weight)
    phi = np.asarray(sr_start(setup, traps, rng))
    v = point_trap_fields(phi, setup, traps)
    rec.add(1, v)
    return Result(phi=phi, history=rec.history, fields=v, meta={"method": SPEC.id})
