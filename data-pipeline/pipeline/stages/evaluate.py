"""Stage 5, evaluate (the TEST stage): held-out metrics of the two learned model slots, from the RELEASED graphs.

    .venv-gpu/Scripts/python.exe -m pipeline.stages.evaluate [--slot cgh-net|warmstart-model|all] [--models-dir DIR]

It loads ``models/<stem>.onnx`` through onnxruntime (by the method modules), runs them on the held-out files of the data root
(``$DINHOT_LEARNED_DIR``, written before training), and writes ``data/derived/models/metrics.json`` (contract
``model-metrics``) and ``data/derived/models/evaluation-detail.json`` (per-target and per-geometry rows, secondary comparisons).
A slot with no released model has no entry (its baseline answers). Offline, never in CI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..io.contract import REPO_ROOT
from ..io.formats import write_json
from ..io.model_card import is_valid_slot

SLOTS = ("cgh-net", "warmstart-model")


def engine_version(repo_root: Path = REPO_ROOT) -> str:
    return (repo_root / "VERSION").read_text(encoding="utf-8").strip()


def run(slots=SLOTS, models_dir: Path | None = None, heldout_root: Path | None = None, out_dir: Path | None = None,
        seeds=(301, 302, 303), budget: int = 60) -> dict:
    from ..model.holo.learned import evaluation, heldout
    models = Path(models_dir) if models_dir else REPO_ROOT / "models"
    root = Path(heldout_root) if heldout_root else heldout.learned_root()
    out = Path(out_dir) if out_dir else REPO_ROOT / "data" / "derived" / "models"
    mpath, dpath = out / "metrics.json", out / "evaluation-detail.json"
    doc = json.loads(mpath.read_text(encoding="utf-8")) if mpath.is_file() else {"schema": "dinhot.model-metrics/v1", "slots": {}}
    detail = json.loads(dpath.read_text(encoding="utf-8")) if dpath.is_file() else {}
    doc["engine_version"] = engine_version()
    for slot in slots:
        if not is_valid_slot(models, slot):
            doc["slots"].pop(slot, None)
            detail.pop(slot, None)
            continue
        if slot == "cgh-net":
            entry, det = evaluation.evaluate_cgh(models, root / "cgh-heldout.npz")
        else:
            entry, det = evaluation.evaluate_warm(models, root / "warmstart-heldout.npz", seeds, budget)
        doc["slots"][slot], detail[slot] = entry, det
    out.mkdir(parents=True, exist_ok=True)
    write_json(mpath, doc)
    write_json(dpath, detail)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--slot", default="all", choices=("all",) + SLOTS)
    ap.add_argument("--models-dir", type=Path, default=None)
    ap.add_argument("--heldout-root", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--budget", type=int, default=60)
    a = ap.parse_args(argv)
    doc = run(SLOTS if a.slot == "all" else (a.slot,), a.models_dir, a.heldout_root, a.out, budget=a.budget)
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
