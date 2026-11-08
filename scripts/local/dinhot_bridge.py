#!/usr/bin/env python3
"""DinHot's steps of the numbered local workflow (scripts/local/workflow.json) around its real producers.

The learned models are trained offline and released as a card and a graph in ``models/``; generation never retrains them. A sandbox bake
of ``data-pipeline/run.py --output <derived>`` reads the released graph from ``<derived>/models`` (where it also writes the model
evidence the readiness rows read), so generation stages them there first and moves the released files back to ``<stage>/models`` at the
end, the repository's own layout, before the stage is validated and promoted.

    python scripts/local/dinhot_bridge.py stage-learned <stage>   # before the bake
    python scripts/local/dinhot_bridge.py evaluate <stage>        # the held-out metrics of the released models at this version
    python scripts/local/dinhot_bridge.py finalize <stage>        # after the readiness document
    python scripts/local/dinhot_bridge.py validate <stage>        # a validator: the released files unchanged, every case present

The model metrics (contract model-metrics, ``data/derived/models/metrics.json``) carry the version that measured them, so a stage
of a new version measures them again (``pipeline.stages.evaluate`` on the staged released graphs and the held-out files of the data
root, ``<CAOS_DATA_ROOT>/dinhot/learned`` unless ``DINHOT_LEARNED_DIR`` names another), instead of carrying the previous version's copy.

Standard library only. Exit 0 on success, 1 with the reason otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
EVIDENCE = ROOT / "data" / "derived" / "models"


def released() -> list[Path]:
    """The files of the released models: every card in models/ and the graph it names."""
    out: list[Path] = []
    for card in sorted(MODELS.glob("*.json")):
        out.append(card)
        graph = json.loads(card.read_text(encoding="utf-8")).get("onnx")
        if graph:
            out.append(ROOT / graph)
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_learned(stage: Path) -> None:
    target = stage / "data" / "derived" / "models"
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(EVIDENCE.glob("*.json")):
        if path.name != "metrics.json" or not (target / path.name).exists():
            shutil.copyfile(path, target / path.name)
    for path in released():
        shutil.copyfile(path, target / path.name)


def evaluation_command(stage: Path, environ: dict) -> tuple[list[str], Path, dict]:
    """The command, working folder and environment of the evaluation stage on this stage's released graphs."""
    learned = environ.get("DINHOT_LEARNED_DIR", "").strip()
    if not learned:
        data_root = environ.get("CAOS_DATA_ROOT", "").strip()
        if not data_root:
            raise SystemExit("dinhot_bridge: set CAOS_DATA_ROOT (the data root holding dinhot/learned) or DINHOT_LEARNED_DIR")
        learned = str(Path(data_root) / "dinhot" / "learned")
    models = stage / "data" / "derived" / "models"
    command = [sys.executable, "-m", "pipeline.stages.evaluate", "--models-dir", str(models), "--out", str(models)]
    return command, ROOT / "data-pipeline", {**environ, "DINHOT_LEARNED_DIR": learned}


def evaluate(stage: Path) -> None:
    command, cwd, env = evaluation_command(stage, dict(os.environ))
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode:
        raise SystemExit(f"dinhot_bridge: the evaluation of the released models failed (exit {result.returncode})")


def finalize(stage: Path) -> None:
    source = stage / "data" / "derived" / "models"
    target = stage / "models"
    target.mkdir(parents=True, exist_ok=True)
    for path in released():
        staged = source / path.name
        if not staged.is_file():
            raise SystemExit(f"dinhot_bridge: the released file {path.name} is not in the stage")
        shutil.move(str(staged), target / path.name)


def validate(stage: Path) -> None:
    problems = []
    for path in released():
        staged = stage / "models" / path.name
        if not staged.is_file() or digest(staged) != digest(path):
            problems.append(f"models/{path.name} is absent or not the released file")
        if (stage / "data" / "derived" / "models" / path.name).exists():
            problems.append(f"data/derived/models/{path.name}: a released file left inside the bake")
    cases = json.loads((ROOT / "data" / "examples" / "cases.json").read_text(encoding="utf-8"))
    index = json.loads((stage / "data" / "derived" / "manifests" / "index.json").read_text(encoding="utf-8"))
    want = sorted(c["case_id"] for c in cases)
    have = sorted(c["case_id"] for c in index["cases"])
    if want != have:
        problems.append(f"the stage's case index {have} is not the authored case set {want}")
    if problems:
        raise SystemExit("dinhot_bridge: " + "; ".join(problems))


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("stage-learned", "evaluate", "finalize", "validate"):
        print(__doc__, file=sys.stderr)
        return 2
    {"stage-learned": stage_learned, "evaluate": evaluate, "finalize": finalize, "validate": validate}[argv[0]](Path(argv[1]).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
