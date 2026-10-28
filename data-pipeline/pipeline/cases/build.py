"""From an accepted params record to the engine's objects (``pipeline.model.holo.core``).

The record is JSON-typed (micrometres, nanometres, millimetres); the engine is SI. Conversions happen here and only here.
A shaped target is drawn on the centred focal FFT grid (bin ``(0, 0)`` at index ``n_fft // 2``): amplitude 1 on the shape,
0 elsewhere; the signal region (``mask``) is the shape dilated by ``signal_margin_bins`` (the dark margin around the shape
belongs to the signal region, so light spilling next to the shape counts against a method).
"""
from __future__ import annotations

import numpy as np

from ..io.contract import bin_um
from ..model.holo.core.device import Device
from ..model.holo.core.geometry import Setup
from ..model.holo.core.traps import Trap, TrapSet
from ..model.holo.core.types import Target
from ..model.holo.core.zernike import phase_from_coeffs


def setup_of(rec: dict) -> Setup:
    s = rec["setup"]
    beam = s["beam"]
    return Setup(wavelength_m=s["wavelength_nm"] * 1e-9, focal_m=s["focal_mm"] * 1e-3, na=s["na"], n_imm=s["n_imm"],
                 n_pix=s["n_pix"], pitch_m=s["pitch_um"] * 1e-6, pad=s["pad"], beam=beam["kind"],
                 waist_frac=beam.get("waist_frac", 1.0))


def device_of(rec: dict) -> Device | None:
    d = rec["device"]
    if d is None:
        return None
    ct = d["crosstalk"]
    return Device(bit_depth=d["bit_depth"], crosstalk=None if ct is None else (ct["sigma_per_px"], ct["q"]),
                  upsample=d["upsample"], fill_factor=d["fill_factor"], flicker_rad=d["flicker_rad"],
                  lut_gamma=d["lut_gamma"])


def trapset_of(traps: list[dict], weights: dict[int, float] | None = None) -> TrapSet:
    w = weights or {}
    return TrapSet(Trap(t["id"], t["x_um"] * 1e-6, t["y_um"] * 1e-6, t["z_um"] * 1e-6, w.get(t["id"], t["weight"]),
                        t["charge"]) for t in traps)


def traps_of(rec: dict) -> TrapSet | None:
    return trapset_of(rec["target"]["traps"]) if rec["target"]["kind"] == "traps" else None


def focal_axes_um(rec: dict) -> np.ndarray:
    """Bin centres of the focal grid in micrometres, index ``i`` at ``(i - n_fft // 2) * bin``."""
    s = rec["setup"]
    n = s["n_pix"] * s["pad"]
    return (np.arange(n) - n // 2) * bin_um(s)


def _dilate(mask: np.ndarray, bins: int) -> np.ndarray:
    out = mask.copy()
    for _ in range(bins):
        grown = out.copy()
        grown[1:, :] |= out[:-1, :]
        grown[:-1, :] |= out[1:, :]
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def shape_mask(rec: dict) -> np.ndarray:
    """The boolean shape (without margin) on the focal grid, ``[iy, ix]``."""
    t = rec["target"]
    ax = focal_axes_um(rec)
    x, y = np.meshgrid(ax, ax)
    r = np.hypot(x, y)
    shape = t["shape"]
    if shape in ("disc", "top_hat"):
        return r <= t["radius_um"]
    if shape in ("ring", "lg_ring"):
        return np.abs(r - t["radius_um"]) <= t["width_um"] / 2.0
    if shape == "line":
        return (np.abs(x) <= t["length_um"] / 2.0) & (np.abs(y) <= t["width_um"] / 2.0)
    raise ValueError(f"unknown shape {shape!r}")


def target_of(rec: dict) -> Target:
    t = rec["target"]
    if t["kind"] == "traps":
        return Target.from_traps(traps_of(rec))
    shape = shape_mask(rec)
    return Target.from_field(shape.astype(np.float64), _dilate(shape, t["signal_margin_bins"]))


def aberration_phase(rec: dict, setup: Setup) -> np.ndarray | None:
    """The system aberration as a phase on the SLM grid (radians), None when the record has none."""
    ab = rec["aberration"]
    if ab is None:
        return None
    return phase_from_coeffs(aberration_coeffs(rec), setup)


def aberration_coeffs(rec: dict) -> list[float]:
    """Noll coefficients in waves as a list indexed from Noll j = 1 (piston) to the highest index given."""
    noll = rec["aberration"]["noll"]
    top = max((int(k) for k in noll), default=1)
    c = [0.0] * top
    for k, v in noll.items():
        c[int(k) - 1] = float(v)
    return c


def is_3d(rec: dict) -> bool:
    return rec["target"]["kind"] == "traps" and any(t["z_um"] != 0 for t in rec["target"]["traps"])
