r"""M06: weighted Gerchberg-Saxton (GSW).

Update rule (R2 D3.4 and dossier D1.2, Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913, Eq. (18) and the
iteration that follows), started from the SR hologram with $w_m^0 = 1$:
$$w_m^k = w_m^{k-1}\frac{\langle |V^{k-1}|\rangle}{|V_m^{k-1}|},\qquad
\phi_j^k = \arg \sum_m e^{+i\Delta_j^m}\, w_m^k \frac{V_m^{k-1}}{|V_m^{k-1}|}.$$
With target weights $w_m^{\rm target}$: $a_m = \sqrt{w_m^{\rm target}}$, $w_m^0 = a_m$ and $|V_m|$ is replaced by $|V_m|/a_m$
(identical for equal weights). Published: e = 0.93, u = 0.99 after 30 iterations, above 0.9 in 10; 3x3x3 lattice 0.91/0.99.
Forms as M04 (``form='auto'`` default, ``'fft'`` for large arrays). Defaults: ``form='auto'``.
"""
from __future__ import annotations

from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _gs
from ._common import require_kinds

SPEC = MethodSpec(id="M06", name="Weighted GS", family="GS", lane="live", targets=("traps",), dims=(2, 3))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, form: str = "auto") -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    return _gs.run_traps(SPEC.id, setup, target.traps, budget, rng, init, form, _gs.rule_gsw, {})
