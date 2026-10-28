"""Stage 3, train (OFFLINE): fit a tiny surrogate (numpy least-squares) mapping R0 -> peak-infected fraction,
using the SIR engine as ground truth on the TRAINING params. Saves coeffs to models/surrogate.json. Skippable for
products with no learned tier. (EXAMPLE, a real product trains its research-chosen model here, exporting ONNX.)"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from ..io.formats import write_json
from ..io.schema import SIRParams
from ..model.baseline import BASIS, is_valid_bundle
from ..model.sir import simulate


def _design(r0: float) -> list[float]:
    r0 = max(1e-6, r0)
    return [1.0, r0, math.log(r0), 1.0 / r0]


def run(train_params: list[SIRParams], models_dir: str) -> dict:
    X, y = [], []
    for p in train_params:
        r0 = (p.beta / p.gamma) if p.gamma > 0 else 1e-6
        X.append(_design(r0))
        y.append((simulate(p).peak_I / p.N) if p.N > 0 else 0.0)
    coeffs, _res, _rank, _sv = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
    model = {"kind": "linear-lstsq", "basis": list(BASIS), "coeffs": coeffs.tolist()}
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    write_json(Path(models_dir) / "surrogate.json", model)
    return model


def predict(model: dict, r0: float) -> float:
    """The peak infected fraction, clamped to the slot's output range [0, 1]."""
    raw = float(np.dot(np.array(model["coeffs"]), np.array(_design(r0))))
    return min(1.0, max(0.0, raw))


def load_released(models_dir: str | Path) -> dict | None:
    """The released bundle ``<models_dir>/surrogate.json`` when it exists, parses and is valid, else None (the
    baseline answers)."""
    path = Path(models_dir) / "surrogate.json"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return obj if is_valid_bundle(obj) else None


__all__ = ["is_valid_bundle", "load_released", "predict", "run"]
