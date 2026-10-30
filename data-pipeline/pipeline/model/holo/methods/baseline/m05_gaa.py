r"""M05: generalized adaptive additive GS (GAA).

Update rule (R2 D3.4, Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913, Eqs. (15) and (16)): GAA maximises
$(1-\alpha)\sum_m |V_m| + \alpha \sum_m \log|V_m|$, whose stationarity condition iterated gives
$$\phi_j = \arg \sum_m e^{+i\Delta_j^m}\,\frac{V_m}{|V_m|}\Big[(1-\alpha) + \frac{\alpha}{|V_m|}\Big]$$
(with trap weights, $V_m/|V_m|$ is scaled by $a_m = \sqrt{w_m}$ and $|V_m|$ becomes $|V_m|/a_m$). ``alpha = 0`` is GS.
Default ``alpha = 0.5`` (the paper value, e = 0.93, u = 0.79 at 30 iterations). UNVERIFIED: the bracket is reconstructed
by R2 against Eq. (15) (Greek glyphs lost in the extraction), and the original adaptive-additive text of Soifer, Kotlyar and
Doskolovich was not opened. The printed bracket depends on the absolute scale of $|V_m|$ (fractions of the input power,
about 0.1 on the 10x10 task, so $lpha/|V_m|$ dominates and the iteration oscillates: u = 0.04 to 0.4, below GS, measured).
``scale='mean'`` (default) expresses $|V_m|$ in units of its mean over the traps, which reproduces the published trend
(u about 0.68 against 0.60 for GS at the same efficiency); ``scale='absolute'`` is the bracket exactly as printed.
Same SR start and forms as M04. Defaults: ``alpha=0.5``, ``scale='mean'``, ``form='auto'``.
"""
from __future__ import annotations

from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _gs
from ._common import require_kinds

SPEC = MethodSpec(id="M05", name="Generalized adaptive additive GS", family="GS", lane="live",
                  targets=("traps",), dims=(2, 3))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, alpha: float = 0.5,
        form: str = "auto", scale: str = "mean") -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha!r}")
    if scale not in ("mean", "absolute"):
        raise ValueError(f"scale must be 'mean' or 'absolute', got {scale!r}")
    meta = {"alpha": float(alpha), "scale": scale}
    return _gs.run_traps(SPEC.id, setup, target.traps, budget, rng, init, form, _gs.rule_gaa, dict(meta), meta)
