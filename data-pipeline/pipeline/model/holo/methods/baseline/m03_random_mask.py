r"""M03: random mask encoding (Montes-Usategui et al. 2006).

Pixel assignment rule (R2 D3.3, Montes-Usategui, Pleguezuelos, Andilla and Martin-Badosa, Opt. Express 14, 2101,
https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101, Eqs. (4) to (6)): the SLM is partitioned into disjoint random
subdomains ``I_k``, one per trap, of equal share (``N / M`` pixels each; a share proportional to the trap weight when the
weights differ), and each pixel shows the phase of its trap only:

$$\phi_j = \Delta_j^{m(j)},\qquad I_l \cap I_m = \emptyset,\quad \textstyle\bigcup_k I_k = \text{SLM}$$

The partition is a random permutation of the pixels drawn through ``rng`` (uniform keys, sorted). The dossier D1.1 rule
``phi_j = Delta_j^{m_j}`` with independent draws (Di Leonardo 2007, Table 1) is the same method with a binomial instead
of an exact share. Published on the 10x10 task: e = 0.01 (about 1/M), u = 0.58, sigma = 16 percent at 768 x 768. Defaults: none.
``meta['owner']`` is the ``n_pix x n_pix`` array of trap indices.
"""
from __future__ import annotations

import numpy as np

from ...core.forward import point_trap_fields
from ...core.geometry import wrap_phase
from ...core.modes import grating_phase, lens_phase, vortex_phase
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ._common import Recorder, require_kinds

SPEC = MethodSpec(id="M03", name="Random mask", family="analytic", lane="live", targets=("traps",), dims=(2, 3))


def _owner(n_pix: int, weights: np.ndarray, rng: Rng) -> np.ndarray:
    n = n_pix * n_pix
    order = np.argsort(rng.uniform_array(n), kind="stable")          # a random permutation of the pixels
    edges = np.rint(np.cumsum(weights) / weights.sum() * n).astype(np.int64)
    edges[-1] = n
    trap_of_rank = np.searchsorted(edges, np.arange(n), side="right")
    owner = np.empty(n, dtype=np.int64)
    owner[order] = trap_of_rank
    return owner.reshape(n_pix, n_pix)


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    traps = target.traps
    rec = Recorder(budget, traps.weight)
    owner = _owner(setup.n_pix, traps.weight, rng)
    phi = np.zeros((setup.n_pix, setup.n_pix))
    for k in range(len(traps)):
        sel = owner == k
        if not sel.any():
            continue
        d = grating_phase(setup, traps.x_m[k], traps.y_m[k])
        if traps.z_m[k] != 0.0:
            d = d + lens_phase(setup, traps.z_m[k])
        if traps.charge[k] != 0:
            d = d + vortex_phase(setup, int(traps.charge[k]))
        phi[sel] = d[sel]
    phi = wrap_phase(phi)
    v = point_trap_fields(phi, setup, traps)
    rec.add(1, v)
    return Result(phi=phi, history=rec.history, fields=v, meta={"method": SPEC.id, "owner": owner})
