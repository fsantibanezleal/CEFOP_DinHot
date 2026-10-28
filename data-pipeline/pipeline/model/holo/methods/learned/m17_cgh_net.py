r"""M17: multi-plane CNN hologram (DeepCGH form), the slot ``cgh-net`` of the catalog.

DeepCGH (Eybposh et al., Opt. Express 28, 26636 (2020), https://doi.org/10.1364/OE.399624) reports its advantage on volumes: a
U-Net maps the target amplitudes of several planes to one SLM phase, unsupervised, with a loss through a differentiable
propagation to every plane. This is that setting at DinHot's size: the input is the unit-energy amplitude of THREE planes on the
128 x 128 focal crop at the depths ``-8, 0, +8`` SLM-limited Rayleigh ranges (``learned/convert.rayleigh_range_m``; the edge defocus of
the aperture is 8 rad), the output one phase for the 128 x 128 SLM (``n_pix = 128``, ``pad = 1``). The network predicts one complex
focal field per plane, a constant inverse DFT and the plane's lens phase carry each to the SLM, they are summed and the output is the
phase of the sum. The loss is ``1 - AC`` with ``AC`` the mean over the planes of
``2 sum(T I) / (sum T^2 + sum I^2)`` (unit-sum plane intensities ``T`` of the target and ``I`` of the hologram, the plane field being
the centred orthonormal FFT of ``A exp(i (phi - Z q))``); DeepCGH's own accuracy formula was not read (UNVERIFIED), this definition is
used for the loss, the baseline and the evaluation alike.

Targets are point voxels (equal weights, integer lateral bins, equal counts per plane), the form M19 takes: ``Target.from_traps`` with
traps on the three plane depths. The hybrid runs M19 (volumetric 3D GS, Whyte and Courtial 2005) from the network's phase in what is
left of ``budget.time_s`` after the network pass (at most ``budget.iterations`` iterations, at least one); ``refine=False`` returns the
network's phase alone. The acceptance criterion compares the hybrid with M19 alone at the same wall-clock.

Missing data: with no released model the baseline answers, M19 at 30 iterations (``meta['provenance']`` is ``'baseline'``), as the catalog
row ``cgh-net`` states. A setup other than 128 x 128 pad 1, a vortex trap, a depth that is not one of the three planes, or a lateral
position beyond 60 bins from the axis is a ``ValueError``.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.forward import point_trap_fields
from ...core.geometry import focal_bin_m
from ...core.metrics import efficiency, rel_std, trap_intensities, uniformity
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ...learned import convert, generators
from ..baseline import m19_multiplane
from . import _slot

SPEC = MethodSpec(id="M17", name="Multi-plane CNN hologram", family="learned", lane="live", targets=("traps",), dims=(3,))
GRID = 128
BASELINE_ITERATIONS = 30   # the baseline of the slot (M19 at 30 iterations)
LIMIT_BINS = 60.0
PLANE_Z = generators.PLANE_Z


def check_geometry(setup) -> None:
    if setup.n_pix != GRID or setup.pad != 1:
        raise ValueError(f"M17 is trained for the {GRID} x {GRID} SLM with padding 1 (focal crop {GRID} x {GRID}), got "
                         f"n_pix={setup.n_pix}, pad={setup.pad}")


def plane_dz_m(setup) -> float:
    return PLANE_Z * convert.rayleigh_range_m(setup)


def planes_from_traps(setup, traps) -> np.ndarray:
    """The network input ``[1, 3, 128, 128]``: unit-energy amplitudes of the three planes (Gaussian spots of sigma 1 bin)."""
    if np.any(traps.charge != 0):
        raise ValueError("M17 does not take vortex traps")
    b, zr = focal_bin_m(setup), convert.rayleigh_range_m(setup)
    x, y, z = traps.x_m / b, traps.y_m / b, traps.z_m / zr
    if np.abs(x).max() > LIMIT_BINS or np.abs(y).max() > LIMIT_BINS:
        raise ValueError(f"M17 takes traps within {LIMIT_BINS:g} bins of the axis")
    plane = np.rint(z / PLANE_Z).astype(int)
    if np.any(np.abs(z - plane * PLANE_Z) > 0.05) or np.any(np.abs(plane) > 1):
        raise ValueError(f"M17 takes traps on the planes z = -{PLANE_Z:g}, 0, +{PLANE_Z:g} Rayleigh ranges")
    out = np.zeros((1, 3, GRID, GRID), dtype=np.float32)
    for k, p in enumerate(generators.PLANE_INDEX):
        sel = plane == p
        if sel.any():
            xy = np.column_stack([np.rint(x[sel]), np.rint(y[sel])])
            out[0, k] = np.sqrt(generators.render_spots(xy, traps.weight[sel])).astype(np.float32)
    return out


def predict(session, amps: np.ndarray) -> np.ndarray:
    """The network's phase mask (float64, 128 x 128)."""
    return session.run(None, {"target": amps})[0][0, 0].astype(np.float64)


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, models_dir=None, refine: bool = True) -> Result:
    if target.kind != "traps":
        raise ValueError(f"{SPEC.id} supports the target kinds ['traps'], got {target.kind!r}")
    check_geometry(setup)
    dz = plane_dz_m(setup)
    amps = planes_from_traps(setup, target.traps)
    slot = _slot.load("cgh-net", models_dir)
    if slot is None:   # no released model: the baseline (M19, 30 iterations) answers
        res = m19_multiplane.run(setup, target, budget=Budget(BASELINE_ITERATIONS), rng=rng, dz_m=dz)
        res.meta.update({"method": SPEC.id, "provenance": "baseline"})
        return res
    session, _card = slot
    t0 = time.perf_counter()
    phi = predict(session, amps)
    dt = time.perf_counter() - t0
    if refine:
        remaining = None if budget.time_s is None else budget.time_s - dt
        if remaining is None or remaining > 0:
            res = m19_multiplane.run(setup, target, budget=Budget(budget.iterations, remaining), rng=rng, init=phi, dz_m=dz)
            res.meta.update({"method": SPEC.id, "provenance": "real", "network_s": dt, "refine_iterations": res.meta["iterations"]})
            for h in res.history:
                h["time_s"] += dt
            return res
    v = point_trap_fields(phi, setup, target.traps)
    i_w = trap_intensities(v, target.traps.weight)
    entry = {"iteration": 0, "efficiency": efficiency(trap_intensities(v)), "uniformity": uniformity(i_w), "rel_std": rel_std(i_w), "time_s": dt}
    return Result(phi=phi, history=[entry], fields=v,
                  meta={"method": SPEC.id, "provenance": "real", "network_s": dt, "refine_iterations": 0, "iterations": 0})


__all__ = ["SPEC", "run", "planes_from_traps", "predict"]
