r"""M15: Laguerre-Gaussian (optical vortex) traps by the point-trap model with orbital angular momentum.

Rule (dossier D3.3, Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913, text after Eq. (2); Polin et al. 2005 make
12 vortices of $l = 8$ inside a 51-trap array): the delay of a charged trap carries one more term,
$$\Delta_j^m = \frac{\pi z_m}{\lambda f^2}(x_j^2 + y_j^2) + \frac{2\pi}{\lambda f}(x_j x_m + y_j y_m) + l_m \operatorname{atan2}(y_j, x_j),$$
(``core.forward``), and the field $V_m$ of a charged trap is the overlap of the focal field with the vortex mode of
charge $l_m$ (it is the projection that is equalised; the intensity at the centre of the trap is dark). The hologram is the
weighted GS of M06 (``Eq. (18)`` of the same paper; ``core.forward.point_trap_backproject`` carries the charges), so the
traps' mode powers equalise. Charges come from ``Trap.charge``; ``charge=`` overrides all traps (the vortex of that charge at
every trap); a target with no charged trap and no ``charge`` raises ``ValueError``.

``ring_phase_profile`` measures the acceptance quantity: the phase of the focal field on a ring of ``radius_bins`` around the
trap (default: the radius of maximum mean intensity between 0.5 and 5 bins), its total winding (sum of wrapped phase steps,
$2\pi l$ times a fixed sign), and the maximum deviation from the best-fit line $\pm l\theta + c$ (rad). The field at a ring point
is the plain (charge 0) point-trap projection there. Only the point form exists (charged traps are off the FFT bins).
Defaults: ``charge=None``.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ...core.forward import point_trap_fields, point_trap_projection, slm_field
from ...core.rng import Rng
from ...core.traps import Trap, TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ..baseline import _gs
from ..baseline._common import require_kinds

SPEC = MethodSpec(id="M15", name="Laguerre-Gaussian vortex traps", family="GS", lane="live",
                  targets=("traps",), dims=(2, 3))

_N_RING = 48


def _ring_traps(setup, trap: Trap, radius_bins: float) -> TrapSet:
    from ...core.geometry import focal_bin_m
    r = radius_bins * focal_bin_m(setup)
    th = 2 * math.pi * np.arange(_N_RING) / _N_RING
    return TrapSet(Trap(i, trap.x_m + r * math.cos(t), trap.y_m + r * math.sin(t), trap.z_m)
                   for i, t in enumerate(th))


def ring_phase_profile(phi: np.ndarray, setup, trap: Trap, radius_bins: float | None = None) -> dict:
    """Winding and line-fit error of the focal phase on a ring around ``trap`` (see the module docstring)."""
    field = slm_field(phi, setup)

    def sample(rad):
        return point_trap_projection(field, setup, _ring_traps(setup, trap, rad))

    if radius_bins is None:
        radii = np.arange(0.5, 5.01, 0.25)
        radius_bins = float(radii[int(np.argmax([np.mean(np.abs(sample(r)) ** 2) for r in radii]))])
    v = sample(radius_bins)
    ph = np.angle(v)
    steps = np.angle(np.exp(1j * np.diff(np.append(ph, ph[0]))))
    winding = float(steps.sum())
    sign = 1.0 if winding >= 0 else -1.0
    l = abs(int(round(winding / (2 * math.pi))))
    th = 2 * math.pi * np.arange(_N_RING) / _N_RING
    resid = np.angle(np.exp(1j * (ph - sign * l * th)))
    c = np.angle(np.mean(np.exp(1j * resid)))
    err = np.abs(np.angle(np.exp(1j * (resid - c))))
    return {"winding": winding, "sign": sign, "radius_bins": radius_bins, "max_error": float(err.max()),
            "rms_error": float(np.sqrt(np.mean(err**2))),
            "ring_intensity": float(np.mean(np.abs(v) ** 2))}


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, charge: int | None = None) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    traps = target.traps
    if charge is not None:
        if isinstance(charge, bool) or int(charge) != charge or charge == 0:
            raise ValueError(f"charge must be a non-zero integer, got {charge!r}")
        traps = TrapSet(replace(t, charge=int(charge)) for t in traps)
    if not np.any(traps.charge != 0):
        raise ValueError("M15 needs at least one trap with a non-zero charge (Trap.charge or the charge keyword)")
    res = _gs.run_traps(SPEC.id, setup, traps, budget, rng, init, "point", _gs.rule_gsw, {})
    res.meta["traps"] = traps
    res.fields = point_trap_fields(res.phi, setup, traps)
    return res
