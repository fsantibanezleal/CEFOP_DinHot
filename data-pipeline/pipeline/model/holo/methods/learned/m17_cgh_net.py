r"""M17: unsupervised CNN hologram (DeepCGH form), the slot ``cgh-net`` of the catalog.

One forward pass of a small U-Net maps the unit-energy target amplitude on the 128 x 128 focal crop to a phase mask on the
128 x 128 SLM (geometry: ``n_pix = 128``, ``pad = 1``, so the focal grid is the crop and one bin is one resolution cell). It
was trained without labels (loss $1 - AC$ through the differentiable FFT model, Eybposh et al., Opt. Express 28, 26636 (2020),
https://doi.org/10.1364/OE.399624; the network predicts a focal-plane field that a constant inverse DFT carries to the SLM, and
the output is its phase). ``AC = 2 \sum T I / (\sum T^2 + \sum I^2)`` with unit-sum intensities, ``core/../learned/torch_forward``;
DeepCGH's own accuracy formula was not read (UNVERIFIED), this definition is used for the loss, GS and the evaluation alike.

Missing data: with no released model the baseline answers (Gerchberg-Saxton, M04, 30 iterations; ``meta['provenance']`` is
``'baseline'``), exactly as the catalog row ``cgh-net`` states. ``budget`` is ignored by the network (one pass); it caps the
baseline's iterations only. ``init`` is not used. A setup other than 128 x 128, pad 1, or a trap target is a ``ValueError``.
"""
from __future__ import annotations

import time

import numpy as np

from ...core.forward import fft_focal_field
from ...core.rng import Rng
from ...core.types import Budget, MethodSpec, Result, Target
from ..baseline import _gs, m04_gs
from . import _slot

SPEC = MethodSpec(id="M17", name="Unsupervised CNN hologram", family="learned", lane="live", targets=("field",), dims=(2,))
GRID = 128
BASELINE_ITERATIONS = 30   # the catalog baseline of the slot (model/baseline.py GS_ITERATIONS)


def check_geometry(setup) -> None:
    if setup.n_pix != GRID or setup.pad != 1:
        raise ValueError(f"M17 is trained for the {GRID} x {GRID} SLM with padding 1 (focal crop {GRID} x {GRID}), got "
                         f"n_pix={setup.n_pix}, pad={setup.pad}")


def network_input(target: Target) -> np.ndarray:
    """The target amplitude normalised to unit energy (``sum a^2 = 1``), float32 ``[1, 1, 128, 128]``; the amplitude is used
    as given (the network was trained on full-crop amplitudes, the mask only selects the GS signal region)."""
    a = np.asarray(target.amplitude, dtype=np.float64)
    return (a / np.sqrt(np.sum(a**2))).astype(np.float32)[None, None]


def predict(session, target: Target) -> np.ndarray:
    """The network's phase mask (float64, 128 x 128)."""
    return session.run(None, {"target": network_input(target)})[0][0, 0].astype(np.float64)


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, models_dir=None) -> Result:
    if target.kind != "field":
        raise ValueError(f"{SPEC.id} supports the target kinds ['field'], got {target.kind!r}")
    check_geometry(setup)
    if target.mask.shape != (GRID, GRID):
        raise ValueError(f"the shaped target must be {GRID} x {GRID}, got {target.mask.shape}")
    slot = _slot.load("cgh-net", models_dir)
    if slot is None:   # no released model: the catalog baseline (GS, 30 iterations) answers
        res = m04_gs.run(setup, target, budget=Budget(BASELINE_ITERATIONS), rng=rng)
        res.meta.update({"method": SPEC.id, "provenance": "baseline"})
        return res
    session, _card = slot
    t0 = time.perf_counter()
    phi = predict(session, target)
    dt = time.perf_counter() - t0
    e = fft_focal_field(phi, setup)
    region = _gs.measure_region(setup, target)
    t = target.amplitude * np.sqrt(setup.n_pix**2 / np.sum(np.where(target.mask, target.amplitude, 0.0) ** 2))
    ratio = np.abs(e[region]) ** 2 / (t[region] ** 2)
    entry = {"iteration": 1, "efficiency": float(np.sum(np.abs(e[target.mask]) ** 2) / setup.n_pix**2),
             "uniformity": float(1.0 - (ratio.max() - ratio.min()) / (ratio.max() + ratio.min())),
             "rel_std": float(100.0 * ratio.std() / ratio.mean()), "time_s": dt, "error": _gs.field_error(e, target, region)}
    return Result(phi=phi, history=[entry], fields=e, meta={"method": SPEC.id, "provenance": "real", "iterations": 1})
