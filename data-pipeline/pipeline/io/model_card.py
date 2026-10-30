"""The validity of a released model slot (catalog rows cgh-net and warmstart-model), standard library only.

A slot is *released* iff its card (``models/<slot file>.json``) validates against ``model-card.schema.json``, names its own
slot, and the ONNX file it points at exists with the card's byte size and SHA-256. Anything else (card absent, unreadable,
failing the schema, graph absent or altered) means no released model: the slot's baseline answers and readiness says
``training`` (catalog, Missing-data states). ``tests/contracts/test_documents.py::test_model_cards_validate`` holds the
card to the schema with ``jsonschema``; this module is the run-time check that CI can run with nothing installed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import jsonschema_lite
from .contract import REPO_ROOT

CARD_SCHEMA_REL = "docs/contracts/schemas/model-card.schema.json"
SLOT_FILES = {"cgh-net": "cgh-net", "warmstart-model": "warmstart"}   # slot -> file stem under models/


def card_path(models_dir: Path, slot: str) -> Path:
    return models_dir / f"{SLOT_FILES[slot]}.json"


def marker_path(models_dir: Path, slot: str) -> Path:
    return models_dir / "training" / slot


def is_valid_slot(models_dir: str | Path, slot: str, repo_root: str | Path | None = None) -> bool:
    """True iff the slot has a released model (the rules above). ``onnx`` is resolved against the parent of ``models_dir``."""
    models = Path(models_dir)
    try:
        card = json.loads(card_path(models, slot).read_text(encoding="utf-8"))
        root = Path(repo_root) if repo_root and (Path(repo_root) / CARD_SCHEMA_REL).is_file() else REPO_ROOT
        schema = json.loads((root / CARD_SCHEMA_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if jsonschema_lite.errors(schema, card) or card.get("slot") != slot:
        return False
    onnx = models.parent / card["onnx"]
    try:
        data = onnx.read_bytes()
    except OSError:
        return False
    return len(data) == card["bytes"] and hashlib.sha256(data).hexdigest() == card["sha256"]
