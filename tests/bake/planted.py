"""Test-only method modules, planted in a temporary package (never in the product tree).

The bake and the benchmark run whatever the method registry holds; the real methods (E2, E3) are separate units. These
planted methods are small, correct implementations of the interface of ``core/types.py`` built from the engine's own
forward models: a random superposition (M02), Gerchberg-Saxton (M04, point-trap form), weighted GS (M06), an FFT-form GS for
shaped fields (M08, baked lane) and a method that always raises (X01 style tests plant it with ``plant_failing``). They
let the pipeline be tested end to end without the unit that owns the real methods.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

HEADER = '''
import time

import numpy as np

from pipeline.model.holo.core import metrics
from pipeline.model.holo.core.forward import (fft_focal_field, fft_inverse, point_trap_backproject, point_trap_fields)
from pipeline.model.holo.core.types import MethodSpec, Result


def _hist(it, v, weights, t0):
    raw = metrics.trap_intensities(v)
    rel = metrics.trap_intensities(v, weights)
    return {"iteration": it, "efficiency": metrics.efficiency(raw), "uniformity": metrics.uniformity(rel),
            "rel_std": metrics.rel_std(rel), "time_s": time.perf_counter() - t0}


def _start(setup, rng, init):
    return np.array(init, dtype=float) if init is not None else rng.phases(setup.n_pix**2).reshape(setup.n_pix, setup.n_pix)
'''

M02 = HEADER + '''
SPEC = MethodSpec(id="M02", name="Random superposition (test)", family="analytic", lane="live", targets=("traps",), dims=(2, 3))


def run(setup, target, *, device=None, budget, rng, init=None):
    t0 = time.perf_counter()
    traps = target.traps
    c = np.exp(1j * rng.phases(len(traps)))
    phi = np.angle(point_trap_backproject(c, setup, traps))
    v = point_trap_fields(phi, setup, traps)
    return Result(phi, [_hist(0, v, traps.weight, t0)], v)
'''

M04 = HEADER + '''
SPEC = MethodSpec(id="M04", name="Gerchberg-Saxton (test)", family="GS", lane="live", targets=("traps",), dims=(2, 3))


def run(setup, target, *, device=None, budget, rng, init=None):
    t0 = time.perf_counter()
    traps = target.traps
    phi = _start(setup, rng, init)
    hist = []
    for it in range(budget.iterations):
        v = point_trap_fields(phi, setup, traps)
        hist.append(_hist(it, v, traps.weight, t0))
        phi = np.angle(point_trap_backproject(np.exp(1j * np.angle(v)), setup, traps))
        if budget.time_s is not None and time.perf_counter() - t0 > budget.time_s:
            break
    v = point_trap_fields(phi, setup, traps)
    hist.append(_hist(len(hist), v, traps.weight, t0))
    return Result(phi, hist, v)
'''

M06 = HEADER + '''
SPEC = MethodSpec(id="M06", name="Weighted GS (test)", family="GS", lane="live", targets=("traps",), dims=(2, 3))


def run(setup, target, *, device=None, budget, rng, init=None):
    t0 = time.perf_counter()
    traps = target.traps
    phi = _start(setup, rng, init)
    w = np.sqrt(traps.weight)
    hist = []
    for it in range(budget.iterations):
        v = point_trap_fields(phi, setup, traps)
        hist.append(_hist(it, v, traps.weight, t0))
        a = np.abs(v)
        w = w * (np.sqrt(traps.weight) * a.mean() / np.maximum(a, 1e-12) / np.sqrt(traps.weight).mean()) ** 1.0
        phi = np.angle(point_trap_backproject(w * np.exp(1j * np.angle(v)), setup, traps))
        if budget.time_s is not None and time.perf_counter() - t0 > budget.time_s:
            break
    v = point_trap_fields(phi, setup, traps)
    hist.append(_hist(len(hist), v, traps.weight, t0))
    return Result(phi, hist, v)
'''

M08 = HEADER + '''
SPEC = MethodSpec(id="M08", name="FFT GS for shaped fields (test)", family="full-field", lane="baked", targets=("field",),
                  dims=(2,))


def run(setup, target, *, device=None, budget, rng, init=None):
    t0 = time.perf_counter()
    phi = _start(setup, rng, init)
    amp = target.amplitude * np.sqrt(setup.n_pix**2 / np.sum(target.amplitude**2))
    hist = []
    for it in range(budget.iterations):
        e = fft_focal_field(phi, setup)
        inside = np.abs(e[target.mask]) ** 2 * setup.pad**2 / setup.n_pix**2
        hist.append({"iteration": it, "efficiency": float(inside.sum() / setup.pad**2), "uniformity": 0.5, "rel_std": 10.0, "error": 0.1,
                     "time_s": time.perf_counter() - t0})
        phi = np.angle(fft_inverse(amp * np.exp(1j * np.angle(e)), setup))
    e = fft_focal_field(phi, setup)
    hist.append({"iteration": len(hist), "efficiency": 0.5, "uniformity": 0.5, "rel_std": 10.0, "error": 0.1, "time_s": time.perf_counter() - t0})
    return Result(phi, hist, e)
'''

M05 = HEADER + '''
SPEC = MethodSpec(id="M05", name="Tunable GS (test)", family="GS", lane="live", targets=("traps",), dims=(2, 3))
TUNING = [{"gamma": g} for g in (0.25, 0.5, 0.75, 1.0)]


def run(setup, target, *, device=None, budget, rng, init=None, gamma=0.5):
    """GS whose phase is perturbed by (1 - gamma) of random noise: a larger gamma is strictly better."""
    t0 = time.perf_counter()
    traps = target.traps
    phi = _start(setup, rng, init)
    hist = []
    for it in range(budget.iterations):
        v = point_trap_fields(phi, setup, traps)
        hist.append(_hist(it, v, traps.weight, t0))
        phi = np.angle(point_trap_backproject(np.exp(1j * np.angle(v)), setup, traps))
    phi = phi + (1.0 - gamma) * 0.8 * rng.normal_array(phi.size).reshape(phi.shape)
    v = point_trap_fields(phi, setup, traps)
    hist.append(_hist(len(hist), v, traps.weight, t0))
    return Result(phi, hist, v)
'''

RAISES = HEADER + '''
SPEC = MethodSpec(id="M09", name="Always raises (test)", family="optimization", lane="baked", targets=("traps",), dims=(2,))


def run(setup, target, *, device=None, budget, rng, init=None):
    raise RuntimeError("planted failure")
'''

SOURCES = {"M02": ("baseline", M02), "M04": ("baseline", M04), "M05": ("baseline", M05), "M06": ("baseline", M06), "M08": ("baseline", M08),
           "M09": ("optim", RAISES)}


def plant(root: Path, ids: tuple[str, ...] = ("M02", "M04", "M06"), name: str = "plantpkg") -> tuple[str, str]:
    """Write a method package with the planted ``ids`` under ``root``; return ``(base package name, sys.path entry)``.

    The caller passes the name to ``methods.reload`` and puts the path on ``sys.path`` (a fixture does both)."""
    pkg = root / name
    for sub in ("baseline", "control", "optim", "beyond"):
        (pkg / sub).mkdir(parents=True, exist_ok=True)
        (pkg / sub / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for mid in ids:
        sub, src = SOURCES[mid]
        (pkg / sub / f"{mid.lower()}_test.py").write_text(textwrap.dedent(src), encoding="utf-8")
    for mod in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
        del sys.modules[mod]
    return name, str(root)
