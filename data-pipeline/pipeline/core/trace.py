"""The compact TRACE = the web-replay artifact (catalog row trace, schema ``dinhot.trace/v1``), at most 256 KiB.

Decimation (as the trace schema says): a method's history at most ``MAX_HISTORY`` = 200 points, uniform in the iteration
index with the first and the last kept; the bead or atom trajectory at most 4000 points; the power spectrum at most 200
points (log-spaced bins, averaged); at most 120 rearrangement frames. Base64 fields: ``phase_u8`` is ``n_pix x n_pix``
bytes (the phase quantized to 256 levels over ``[0, 2 pi)``), ``focal.intensity_db_u8`` is ``size x size`` bytes (dB
relative to the mean trap, ``db_floor..0`` mapped to ``0..255``; blocks of ``step x step`` focal bins are max-pooled so a
peak is never lost), ``axial.xz_u8`` is ``nz x nx`` bytes in the same dB scale.

A trace that would exceed ``TRACE_BYTES_GATE`` is squeezed in fixed steps (``SQUEEZE``): fewer decimals, a shorter history,
a smaller focal crop, no axial cut; the step used is returned so the lane gate can state it. Nothing is dropped silently
beyond that: a trace that still does not fit raises ``TraceTooLarge``.
"""
from __future__ import annotations

import base64
import json
import math
from typing import Any

import numpy as np

from .gate import TRACE_BYTES_GATE

TRACE_SCHEMA = "dinhot.trace/v1"
MAX_HISTORY = 200
MAX_TRAJECTORY = 4000
MAX_PSD = 200
MAX_FRAMES = 120
DB_FLOOR = -40.0
FOCAL_MAX = 128
FOCAL_PAD_BINS = 6
# (decimals of trap intensity, history points, focal size cap, axial kept, trajectory points)
SQUEEZE = ((4, MAX_HISTORY, FOCAL_MAX, True, MAX_TRAJECTORY), (3, 60, FOCAL_MAX, True, MAX_TRAJECTORY),
           (3, 40, 96, True, 2000), (2, 20, 64, True, 1000), (2, 20, 64, False, 500))


class TraceTooLarge(ValueError):
    """A trace exceeds the lane gate's byte budget even at the last squeeze step."""


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decimate_indices(n: int, limit: int) -> list[int]:
    """At most ``limit`` indices of ``range(n)``, uniform, first and last kept."""
    if n <= limit:
        return list(range(n))
    return sorted({round(i * (n - 1) / (limit - 1)) for i in range(limit)})


def decimate_history(history: list[dict], limit: int, decimals: int = 5) -> list[dict]:
    """The trace form of a method's history: ``rel_std`` becomes ``rel_std_pct``; first and last point kept."""
    return [{"iteration": int(history[i]["iteration"]), "efficiency": round(float(history[i]["efficiency"]), decimals),
             "uniformity": round(float(history[i]["uniformity"]), decimals),
             "rel_std_pct": round(float(history[i]["rel_std"]), decimals - 1)}
            for i in decimate_indices(len(history), limit)]


def phase_u8(phi: np.ndarray) -> bytes:
    """The phase wrapped to ``[0, 2 pi)`` and quantized to 256 levels (row-major, ``n_pix x n_pix`` bytes)."""
    w = np.mod(np.asarray(phi, dtype=np.float64), 2.0 * math.pi)
    return (np.floor(w / (2.0 * math.pi) * 256.0).astype(np.int64) % 256).astype(np.uint8).tobytes()


def db_u8(intensity: np.ndarray, reference: float) -> bytes:
    """dB relative to ``reference`` clipped to ``[DB_FLOOR, 0]`` and mapped to ``0..255`` (row-major)."""
    ref = max(float(reference), 1e-300)
    db = 10.0 * np.log10(np.maximum(np.asarray(intensity, dtype=np.float64), 1e-300) / ref)
    return np.rint((np.clip(db, DB_FLOOR, 0.0) - DB_FLOOR) / (-DB_FLOOR) * 255.0).astype(np.uint8).tobytes()


def max_pool(a: np.ndarray, step: int) -> np.ndarray:
    n = (a.shape[0] // step) * step
    m = (a.shape[1] // step) * step
    return a[:n, :m].reshape(n // step, step, m // step, step).max(axis=(1, 3))


def focal_window(extent_bins: float, n_fft: int, size_cap: int) -> tuple[int, int, int]:
    """``(half-width in bins, step, size)`` of the focal crop centred on bin (0, 0)."""
    hw = min(int(math.ceil(extent_bins + FOCAL_PAD_BINS)), n_fft // 2 - 1)
    step = max(1, math.ceil(2 * hw / size_cap))
    size = (2 * hw) // step
    return (size * step) // 2, step, size


def focal_crop(intensity: np.ndarray, extent_bins: float, size_cap: int) -> tuple[np.ndarray, int]:
    """The max-pooled crop of the focal intensity map and its ``step`` (bins per crop cell)."""
    n = intensity.shape[0]
    hw, step, size = focal_window(extent_bins, n, size_cap)
    h = n // 2
    win = intensity[h - hw:h + hw, h - hw:h + hw]
    crop = max_pool(win, step)
    assert crop.shape == (size, size)
    return crop, step


def mask_rle(mask: np.ndarray) -> list[int]:
    """Run lengths of the flattened boolean mask (row-major), alternating False, True, ..., starting with a False run
    (possibly 0)."""
    flat = np.asarray(mask, dtype=bool).ravel()
    runs: list[int] = []
    cur, n = False, 0
    for v in flat:
        if bool(v) == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = bool(v), 1
    runs.append(n)
    return runs


def log_psd(f: np.ndarray, p: np.ndarray, limit: int = MAX_PSD) -> tuple[list[float], list[float]]:
    """At most ``limit`` points: log-spaced frequency bins, geometric-mean-free arithmetic average of the power."""
    f, p = np.asarray(f, dtype=np.float64), np.asarray(p, dtype=np.float64)
    if f.size <= limit:
        return [float(v) for v in f], [float(v) for v in p]
    edges = np.unique(np.rint(np.geomspace(1, f.size + 1, limit + 1)).astype(int)) - 1
    of, op = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        if b > a:
            of.append(float(np.exp(np.log(f[a:b]).mean())))
            op.append(float(p[a:b].mean()))
    return of, op


def _sig(v: float, digits: int = 6) -> float:
    return float(f"{v:.{digits}g}")


def build_trace(parts: dict[str, Any], step: int = 0) -> dict:
    """The trace of one case at squeeze ``step`` (see the module docstring).

    ``parts``: ``case_id``, ``grid`` (n_pix, pad, bin_um, half_field_um), ``traps`` (record dicts), ``shape`` (None or
    ``{kind, mask}`` with the boolean shape on the full focal grid), ``methods``
    (id -> history list, final metrics dict, trap_intensity list), ``reference`` (method, phi, intensity map, ref_level,
    extent_bins, axial dict or None), ``feedback``, ``dynamics``, ``rearrangement``, ``summary``.
    """
    dec, hist_n, size_cap, keep_axial, traj_n = SQUEEZE[step]
    ref = parts["reference"]
    crop, cstep = focal_crop(ref["intensity"], ref["extent_bins"], size_cap)
    methods = {}
    for mid in sorted(parts["methods"]):
        m = parts["methods"][mid]
        methods[mid] = {"history": decimate_history(m["history"], hist_n),
                        "final": {k: round(float(m["final"][k]), 6) for k in
                                  ("efficiency", "uniformity", "rel_std_pct", "zero_order", "ghost")},
                        "trap_intensity": [round(float(v), dec) for v in m["trap_intensity"]]}
    axial = None
    if keep_axial and ref.get("axial") is not None:
        a = ref["axial"]
        hw, cs, size = focal_window(ref["extent_bins"], a["xz"].shape[1], size_cap)
        h = a["xz"].shape[1] // 2
        win = a["xz"][:, h - hw:h + hw]
        pooled = win.reshape(win.shape[0], size, cs).max(axis=2)
        axial = {"trap_id": int(a["trap_id"]), "z_um": [round(float(a["z_um"][0]), 3), round(float(a["z_um"][1]), 3)],
                 "nz": int(pooled.shape[0]), "nx": int(pooled.shape[1]), "xz_u8": b64(db_u8(pooled, ref["ref_level"]))}
    shape = parts["shape"]
    out = {
        "schema": TRACE_SCHEMA, "case_id": parts["case_id"],
        "grid": {"n_pix": int(parts["grid"]["n_pix"]), "pad": int(parts["grid"]["pad"]),
                 "bin_um": _sig(parts["grid"]["bin_um"]), "half_field_um": _sig(parts["grid"]["half_field_um"])},
        "traps": parts["traps"],
        "shape": None if shape is None else {"kind": shape["kind"], "mask_rle": mask_rle(
            focal_crop(shape["mask"].astype(np.float64), ref["extent_bins"], size_cap)[0] > 0.5)},
        "methods": methods,
        "reference": {"method": ref["method"], "phase_u8": b64(phase_u8(ref["phi"])),
                      "focal": {"size": int(crop.shape[0]), "bin_um": _sig(parts["grid"]["bin_um"] * cstep),
                                "db_floor": DB_FLOOR, "intensity_db_u8": b64(db_u8(crop, ref["ref_level"]))},
                      "axial": axial},
        "feedback": parts["feedback"], "dynamics": _thin(parts["dynamics"], traj_n), "rearrangement": parts["rearrangement"],
        "summary": parts["summary"],
    }
    return out


def _thin(dyn: dict | None, limit: int) -> dict | None:
    """The dynamics block with the trajectory cut to at most ``limit`` points (a larger stride, ``t_decimation`` follows)."""
    if dyn is None or len(dyn["x_um"]) <= limit:
        return dyn
    stride = math.ceil(len(dyn["x_um"]) / limit)
    return {**dyn, "x_um": dyn["x_um"][::stride], "y_um": dyn["y_um"][::stride], "t_decimation": dyn["t_decimation"] * stride}


def dumps(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def fit(parts: dict[str, Any]) -> tuple[dict, int, int]:
    """The first trace that fits the gate: ``(trace, bytes, squeeze step)``; ``TraceTooLarge`` when none does."""
    last = 0
    for step in range(len(SQUEEZE)):
        trace = build_trace(parts, step)
        n = len(dumps(trace))
        last = n
        if n <= TRACE_BYTES_GATE:
            return trace, n, step
    raise TraceTooLarge(f"{parts['case_id']}: the trace is {last} bytes at the last squeeze step, over the "
                        f"{TRACE_BYTES_GATE} byte gate")
