r"""M08: mixed-region amplitude freedom (MRAF) for shaped potentials.

Update rule (dossier D1.4, Pasienski and DeMarco, Opt. Express 16, 2176, https://doi.org/10.1364/OE.16.002176,
https://arxiv.org/abs/0712.0794, Eq. (1); the same in Holland et al. with parameter p): with signal region SR, noise region
NR and mixing parameter $m$,
$$G^{(n)} = \Big\{ m\, T\big|_{SR} + (1-m)\,\big|E^{(n)}_{\rm out}\big|\,\Big|_{NR} \Big\}\, e^{\,i \arg E^{(n)}_{\rm out}},\qquad
\phi^{(n+1)} = \arg \mathcal F^{-1} G^{(n)}$$
and the SLM amplitude is reset to the beam. The signal amplitude $T$ (``Target.amplitude`` inside ``Target.mask``) is rescaled
to the input power. In the signal region the amplitude is forced to $m T$, in the noise region it is kept (scaled by
$1-m$), so power not needed for the shape drains into the noise region; $m = 1$ is plain GS (zero noise region).
Default ``mixing = 0.3`` (the paper reports 0.30 to 0.40 for MRAF; on DinHot's grid 0.3 gives error 0.03 and 0.4 gives
0.10 for a disc of 60 bins radius, efficiency 0.18 against 0.41). Start: a Fresnel-lens phase of ``start_waves`` = 20 waves
at the aperture edge (the paper states no start, UNVERIFIED; a random start leaves speckle that MRAF removes slowly, error
0.3 after 100 iterations); ``start_waves=None`` draws a uniform random phase through ``rng``; ``init`` overrides both. Offset-MRAF variants (Gaunt, Bruce, van Bijnen) are not implemented:
their primary papers were not opened (dossier D1.4).
History per iteration: ``efficiency`` = power fraction in the signal region, ``uniformity`` and ``rel_std`` of the ratio
$I/T^2$ over the measure region ($T > 0$ inside the signal region), and ``error`` = the paper RMS fractional error $\eta$
(Eq. (2), intensity rescaled to the target) over the measure region: the shape eroded by one resolution cell (``pad`` bins). ``fields`` is the focal field. Targets: shaped fields only.
Published: error 0.015 to 0.039 against 0.21 to 0.36 for GS, efficiency 0.18 to 0.45 against 0.96 to 0.99 (768 x 768).
"""
from __future__ import annotations

from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _gs
from ._common import require_kinds

SPEC = MethodSpec(id="M08", name="Mixed-region amplitude freedom", family="GS", lane="live",
                  targets=("field",), dims=(2,))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, mixing: float = 0.3,
        start_waves: float | None = _gs.START_WAVES) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    return _gs.run_field(SPEC.id, setup, target, budget, rng, init, mixing, start_waves)
