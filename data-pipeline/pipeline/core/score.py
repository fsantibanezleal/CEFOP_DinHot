"""Scoring of a hologram against the case it was made for: one definition for every method.

A method reports its own history; the verdict the manifest carries is recomputed here from the final phase, through the
same forward model for every method (algorithms D1.0 definitions, ``model.holo.core.metrics``) and through the case's
device and aberration, so methods are compared on one footing and a method cannot grade itself.

- Traps, ideal device: ``V_m`` from the point-trap form (exact off the FFT bins, with z and vortex charge), so a 3D case is
  scored in its own planes. With a device: ``V_m`` is read from the device's focal field at the nearest bin (contract 1
  restricts a device case to z = 0 and no vortex).
- ``efficiency = sum I_m`` (fraction of the input power in the trap peaks), ``uniformity`` and ``rel_std_pct`` on
  ``I_m / w_m``, ``zero_order`` the peak fraction at bin (0, 0), ``ghost`` the power outside the trap and zero-order
  discs (``power_budget``); in a 3D case ghost is ``max(0, 1 - efficiency - zero_order)`` because the other planes' light
  is not a ghost of the focal plane.
- Shaped target: ``efficiency`` is the power inside the shape, ``uniformity`` and ``rel_std_pct`` are taken over the
  shape's interior (its 4-neighbour core, the edge bins carry partial values), ``zero_order`` as above and ``ghost`` the
  power outside the signal region (shape plus margin).
- The aberration of the record multiplies the SLM field (added to the phase) in an ideal-device case.
"""
from __future__ import annotations

import numpy as np

from ..cases import build
from ..model.holo.core import metrics
from ..model.holo.core.device import Device, device_focal_field
from ..model.holo.core.forward import fft_focal_field, point_trap_fields, trap_fields_from_fft
from ..model.holo.core.geometry import Setup
from ..model.holo.core.rng import Rng
from ..model.holo.core.traps import TrapSet

FLICKER_STREAM = 0x0F11C


def focal_field(phi: np.ndarray, setup: Setup, device: Device | None, ab: np.ndarray | None, seed: int) -> np.ndarray:
    """The centred focal field of what the SLM displays, through the device when there is one."""
    if device is not None:
        return device_focal_field(phi, setup, device, Rng((seed ^ FLICKER_STREAM) & 0x7FFFFFFF))
    return fft_focal_field(phi if ab is None else phi + ab, setup)


def _interior(mask: np.ndarray) -> np.ndarray:
    core = mask.copy()
    core[1:, :] &= mask[:-1, :]
    core[:-1, :] &= mask[1:, :]
    core[:, 1:] &= mask[:, :-1]
    core[:, :-1] &= mask[:, 1:]
    core[0, :] = core[-1, :] = False
    core[:, 0] = core[:, -1] = False
    return core if core.any() else mask


def intensity_map(e: np.ndarray, setup: Setup) -> np.ndarray:
    """``|E|^2 pad^2 / n_pix^2``: the focal intensity in the units of ``I_m`` (fraction of the input power per peak)."""
    return np.abs(e) ** 2 * (setup.pad**2 / setup.n_pix**2)


def score_traps(phi: np.ndarray, setup: Setup, device: Device | None, ab: np.ndarray | None, traps: TrapSet,
                three_d: bool, seed: int) -> dict:
    e = focal_field(phi, setup, device, ab, seed)
    if device is not None:
        v = trap_fields_from_fft(e, setup, traps)
    else:
        v = point_trap_fields(phi if ab is None else phi + ab, setup, traps)
    raw = metrics.trap_intensities(v)
    rel = metrics.trap_intensities(v, traps.weight)
    eff, zero = metrics.efficiency(raw), metrics.zero_order_fraction(e, setup)
    ghost = max(0.0, 1.0 - eff - zero) if three_d else max(0.0, metrics.power_budget(e, setup, traps)["ghosts"])
    order = np.argsort(traps.ids)
    mean = float(raw.mean())
    return {"efficiency": eff, "uniformity": metrics.uniformity(rel), "rel_std_pct": metrics.rel_std(rel),
            "zero_order": zero, "ghost": ghost, "trap_intensity": (raw[order] / mean).tolist() if mean > 0 else
            [0.0] * len(raw), "field": e}


def score_field(phi: np.ndarray, setup: Setup, device: Device | None, shape: np.ndarray, region: np.ndarray,
                seed: int) -> dict:
    e = focal_field(phi, setup, device, None, seed)
    power = np.abs(e) ** 2 / setup.n_pix**2
    inten = intensity_map(e, setup)
    core = inten[_interior(shape)]
    mx, mn = float(core.max()), float(core.min())
    return {"efficiency": float(power[shape].sum()),
            "uniformity": 1.0 - (mx - mn) / (mx + mn) if mx + mn > 0 else 0.0,
            "rel_std_pct": 100.0 * float(core.std() / core.mean()) if core.mean() > 0 else 0.0,
            "zero_order": metrics.zero_order_fraction(e, setup),
            "ghost": max(0.0, 1.0 - float(power[region].sum())), "trap_intensity": [], "field": e}


def score(rec: dict, phi: np.ndarray, *, setup: Setup | None = None, device: Device | None = None,
          shape_and_region: tuple[np.ndarray, np.ndarray] | None = None) -> dict:
    """The final metrics of ``phi`` for the record's case (``field`` is the focal field, for the maps)."""
    setup = setup or build.setup_of(rec)
    device = device if device is not None else build.device_of(rec)
    if rec["target"]["kind"] == "traps":
        return score_traps(phi, setup, device, build.aberration_phase(rec, setup), build.traps_of(rec),
                           build.is_3d(rec), rec["seed"])
    shape, region = shape_and_region or (build.shape_mask(rec), build.target_of(rec).mask)
    return score_field(phi, setup, device, shape, region, rec["seed"])
