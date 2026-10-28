r"""M04: Gerchberg-Saxton, point-trap and FFT forms.

Update rule (dossier D1.2, Di Leonardo, Ianni and Ruocco 2007, https://doi.org/10.1364/OE.15.001913, Table 1; Gerchberg and
Saxton 1972 is UNVERIFIED, not opened): with $V_m = \frac1N\sum_j A_j e^{i(\phi_j - \Delta_j^m)}$ and target amplitudes
$a_m = \sqrt{w_m}$,
$$\phi_j^{k} = \arg \sum_m a_m \frac{V_m^{k-1}}{|V_m^{k-1}|}\, e^{+i\Delta_j^m}.$$
The start is the SR hologram (``init`` overrides). ``form='point'`` (default) is the direct sum of ``core.forward``;
``form='fft'`` places the constraint on the FFT bins of the zero-padded transform (traps on bins, z = 0, no vortex); the two
are the same map and agree to rounding. A shaped ``Target`` (signal mask and amplitude on the FFT grid) is accepted in the
FFT form and iterated as GS with a zero noise region (``_gs.run_field`` with mixing 1), the baseline of M08.
Published: e = 0.94, u = 0.60, sigma = 17 percent after 30 iterations on the 10x10 task. Defaults: ``form='point'`` for traps, ``'fft'`` for a shaped target.
"""
from __future__ import annotations

from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from . import _gs

SPEC = MethodSpec(id="M04", name="Gerchberg-Saxton", family="GS", lane="live", targets=("traps", "field"), dims=(2, 3))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None,
        form: str | None = None) -> Result:
    if form is None:
        form = "fft" if target.kind == "field" else "point"
    _gs.check_form(form)
    if target.kind == "field":
        if form != "fft":
            raise ValueError("a shaped-field target needs form='fft'")
        return _gs.run_field(SPEC.id, setup, target, budget, rng, init, mixing=1.0)
    return _gs.run_traps(SPEC.id, setup, target.traps, budget, rng, init, form, _gs.rule_gs, {})
