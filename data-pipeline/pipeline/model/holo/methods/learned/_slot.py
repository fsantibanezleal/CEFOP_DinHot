"""Shared loader of a released model slot for the learned methods (no ``SPEC``: the registry skips this module).

A slot answers with its ONNX graph only when it is released (``io.model_card.is_valid_slot``: card validates, graph present with
the card's size and SHA-256); otherwise the slot's baseline answers and the result says so in ``meta['provenance']``
(``'real'`` or ``'baseline'``, catalog missing-data states). onnxruntime is imported on first use, so importing a method
module costs nothing and works where onnxruntime is absent (the baseline then answers).
"""
from __future__ import annotations

import json
from pathlib import Path

from .....io import model_card
from .....io.contract import REPO_ROOT

_CACHE: dict[tuple[str, str], object] = {}


def default_models_dir() -> Path:
    return REPO_ROOT / "models"


def load(slot: str, models_dir: str | Path | None = None):
    """``(onnxruntime session, card dict)`` of the released slot, or ``None`` (no valid model, or no onnxruntime)."""
    models = Path(models_dir) if models_dir else default_models_dir()
    if not model_card.is_valid_slot(models, slot):
        return None
    card = json.loads(model_card.card_path(models, slot).read_text(encoding="utf-8"))
    key = (slot, card["sha256"])
    if key not in _CACHE:
        try:
            import onnxruntime as ort
        except ImportError:
            return None
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        _CACHE[key] = ort.InferenceSession(str(models.parent / card["onnx"]), so, providers=["CPUExecutionProvider"])
    return _CACHE[key], card
