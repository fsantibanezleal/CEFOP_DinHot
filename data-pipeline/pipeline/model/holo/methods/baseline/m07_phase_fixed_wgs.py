r"""M07: phase-fixed weighted GS (Kim et al. 2019), the practical state of the art for large point arrays.

Update rule (dossier D1.3, Kim, Kim, Lee and Ahn, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178,
https://arxiv.org/abs/1903.09286). At iteration $i$ with focal-plane amplitudes $B_i(\mathbf u_m) = |V_m|/a_m$:
$$g_i(\mathbf u_m) = \frac{\langle B_i\rangle_N}{B_i(\mathbf u_m)}\, g_{i-1}(\mathbf u_m),\quad g_0 = 1,\qquad
\mathcal F[A_{i+1} e^{i\phi_{i+1}}] = g_i T\, e^{i\psi_i},\quad \psi_i = \psi_N\ \ (i \ge N)$$
so the focal phase $\psi$ follows the field ($\psi_i = \arg V_m$) for the first $N$ iterations and is then frozen at $\psi_N$.
$T_m = a_m = \sqrt{w_m}$. ``n_fix`` $= N$ defaults to 12 (Kim: 12 WGS iterations before fixing, 91.2 percent modulation
efficiency, 1500 foci). UNVERIFIED: the dossier does not define $B_i$ (taken as the field amplitude, as in M06) nor whether
the N-th iteration already uses the frozen phase (here it computes it). The camera correction of the paper (M12, ``kim``
variant) is in ``control/m12_closed_loop.py``. Default form is ``'auto'``: the FFT form (the paper form) when every trap is on a bin with z = 0 and charge 0, else the point form (identical on bins); the choice is in ``meta['form']``.
Defaults: ``n_fix=12``, ``form='auto'``.
"""
from __future__ import annotations

from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _gs
from ._common import require_kinds

SPEC = MethodSpec(id="M07", name="Phase-fixed weighted GS", family="GS", lane="live", targets=("traps",), dims=(2,))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, n_fix: int = 12,
        form: str = "auto") -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    if isinstance(n_fix, bool) or int(n_fix) != n_fix or n_fix < 1:
        raise ValueError(f"n_fix must be a positive integer, got {n_fix!r}")
    state = {"n_fix": int(n_fix)}
    res = _gs.run_traps(SPEC.id, setup, target.traps, budget, rng, init, form, _gs.rule_wgs_fixed, state)
    res.meta["n_fix"] = int(n_fix)
    res.meta["psi"] = state.get("psi", state.get("psi_last"))
    return res
