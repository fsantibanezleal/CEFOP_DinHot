"""Plants of template 0.15.004 (CAOS_DinHot's promotion of its 0.02.003 bake, 2026-11-07; issues #112 and #113).

#112: ``scripts/local/workflow.py`` required every document the contract catalog names under ``data/derived/`` or ``models/``,
including those of a contract that ``readiness_exceptions`` declares not shipped (``training``, ``missing``), so a product with an
unreleased model could never promote a complete stage and ``01_init`` started a generation for it. Each test builds a throwaway
product (catalog, workflow config, stage) and runs the real ``validate_stage``, ``initialize`` or ``required_paths``.

#113: ``frontend/scripts/declared.mjs`` read only ``manifest_path`` and failed on a refused case; its plants are the cases of
``frontend/src/lib/declared.test.ts`` (a base test, taken verbatim), run here through vitest."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES, ROOT

needs_web = pytest.mark.skipif(NODE is None or not (NODE_MODULES / "vitest").is_dir(),
                               reason="needs node and `npm ci` in frontend/")

HEADER = ("id", "version", "kind", "schema file", "producer", "consumer", "example", "missing-data behavior",
          "producer test", "consumer test", "model io", "provider", "documents")
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def load_workflow():
    spec = importlib.util.spec_from_file_location("planted_workflow_0_15_004", ROOT / "scripts/local/workflow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# id, documents, readiness state
ROWS = [
    ("index", "data/derived/manifests/index.json", "available"),
    ("ready", "data/derived/readiness.json", "available"),
    ("warm", "models/warm.json, models/warm.onnx", "training"),
    ("avail", "models/avail.json", "available"),
]


def build(tmp_path: Path, exceptions: dict, rows=ROWS):
    """A throwaway product with a catalog, a workflow config and a complete stage (the documents of every row that is shipped)."""
    root = tmp_path / "product"
    write(root / "VERSION", VERSION)
    write(root / ".env.example", "APP_ENV=dev\n")
    write(root / "frontend/package-lock.json", "{}")
    write(root / "check.py", "raise SystemExit(0)\n")
    lines = ["| " + " | ".join(HEADER) + " |", "| " + " | ".join(["---"] * len(HEADER)) + " |"]
    for rid, docs, _ in rows:
        cells = [rid] + ["-"] * (len(HEADER) - 2) + [docs]
        lines.append("| " + " | ".join(cells) + " |")
    catalog = "\n".join(lines) + "\n"
    write(root / "docs/contracts/catalog.md", catalog)
    config = {
        "primary_environment": ".venv", "generation_environments": [], "environments": [], "node_stamp": ".stamp",
        "promote": ["data/derived", "models"],
        "required": ["data/derived/manifests/index.json", "data/derived/readiness.json"],
        "generation": [], "validators": [], "readiness_exceptions": exceptions, "readiness_check": "check.py",
        "api": {"active": False, "port": 8000, "health": "/health", "command": []}, "web_port": 5173,
        "frontend_command": [], "frontend_prepare": [],
    }
    write(root / "scripts/local/workflow.json", json.dumps(config))
    stage = tmp_path / "stage"
    for rid, docs, state in rows:
        if state in ("training", "missing"):
            continue
        for name in docs.split(","):
            write(stage / name.strip(), json.dumps({"engine_version": VERSION}))
    write(stage / "VERSION", VERSION)
    shutil.copytree(root / "docs/contracts", stage / "docs/contracts")
    ready = {"product_version": VERSION, "catalog_sha256": hashlib.sha256(catalog.encode()).hexdigest(),
             "contracts": [{"id": rid, "state": state} for rid, _, state in rows]}
    write(stage / "data/derived/readiness.json", json.dumps(ready))
    return root, config, stage


def validate(workflow, root, config, stage, tmp_path):
    env = {**os.environ, "CAOS_TEMP_ROOT": str(tmp_path / "scratch"), "PYTHONDONTWRITEBYTECODE": "1"}
    return workflow.validate_stage(root, config, stage, sys.executable, env)


def test_a_stage_without_the_documents_of_a_training_contract_is_admitted(tmp_path: Path) -> None:
    workflow = load_workflow()
    root, config, stage = build(tmp_path, {"warm": "training"})
    assert "models/warm.json" not in workflow.required_paths(root, config)
    assert validate(workflow, root, config, stage, tmp_path)["files"]


def test_a_stage_without_the_documents_of_a_missing_contract_is_admitted(tmp_path: Path) -> None:
    workflow = load_workflow()
    rows = [(i, d, "missing" if i == "warm" else s) for i, d, s in ROWS]
    root, config, stage = build(tmp_path, {"warm": "missing"}, rows)
    assert validate(workflow, root, config, stage, tmp_path)["files"]


def test_adversarial_a_stage_missing_a_document_of_an_available_contract_is_still_refused(tmp_path: Path) -> None:
    workflow = load_workflow()
    root, config, stage = build(tmp_path, {"warm": "training"})
    (stage / "models/avail.json").unlink()
    with pytest.raises(workflow.Failure, match=r"Partial stage: models/avail\.json"):
        validate(workflow, root, config, stage, tmp_path)


def test_adversarial_a_partial_contract_still_requires_its_documents(tmp_path: Path) -> None:
    workflow = load_workflow()
    rows = [(i, d, "partial" if i == "warm" else s) for i, d, s in ROWS]
    root, config, stage = build(tmp_path, {"warm": "partial"}, rows)
    assert {"models/warm.json", "models/warm.onnx"} <= set(workflow.required_paths(root, config))
    for name in ("models/warm.json", "models/warm.onnx"):
        (stage / name).unlink(missing_ok=True)
    with pytest.raises(workflow.Failure, match=r"Partial stage: models/warm\.json, models/warm\.onnx"):
        validate(workflow, root, config, stage, tmp_path)


def test_adversarial_a_contract_without_an_exception_still_requires_its_documents(tmp_path: Path) -> None:
    workflow = load_workflow()
    root, config, stage = build(tmp_path, {})
    assert "models/warm.json" in workflow.required_paths(root, config)


def test_adversarial_an_exception_that_does_not_say_not_shipped_does_not_lift_the_requirement(tmp_path: Path) -> None:
    workflow = load_workflow()
    root, config, _ = build(tmp_path, {"warm": "stale"})
    assert "models/warm.json" in workflow.required_paths(root, config)


def test_the_init_check_does_not_start_a_generation_for_a_training_contract(tmp_path: Path, monkeypatch) -> None:
    workflow = load_workflow()
    root, config, stage = build(tmp_path, {"warm": "training"})
    for name in ("data/derived/manifests/index.json", "data/derived/readiness.json", "models/avail.json"):
        write(root / name, (stage / name).read_text(encoding="utf-8"))
    calls = []
    monkeypatch.setattr(workflow, "prerequisites", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "install_frontend", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "generate", lambda *a, **k: calls.append("generate") or stage)
    monkeypatch.setattr(workflow, "check_shipped", lambda *a, **k: calls.append("shipped"))
    workflow.initialize(root, config)
    assert calls == ["shipped"]


def test_adversarial_the_init_check_still_generates_for_a_missing_available_document(tmp_path: Path, monkeypatch) -> None:
    workflow = load_workflow()
    root, config, stage = build(tmp_path, {"warm": "training"})
    for name in ("data/derived/manifests/index.json", "data/derived/readiness.json"):
        write(root / name, (stage / name).read_text(encoding="utf-8"))
    monkeypatch.setattr(workflow, "prerequisites", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "install_frontend", lambda *a, **k: None)
    monkeypatch.setattr(workflow, "generate", lambda *a, **k: stage)
    with pytest.raises(workflow.Failure, match="Complete sandbox prepared"):
        workflow.initialize(root, config)


@needs_web
def test_the_base_declared_test_covers_path_and_refused_cases() -> None:
    # runs in the checkout itself (its real node_modules); never link_node_modules here, which replaces the folder it is given
    r = subprocess.run([NODE, str(NODE_MODULES / "vitest" / "vitest.mjs"), "run", "src/lib/declared.test.ts"],
                       cwd=ROOT / "frontend", capture_output=True, encoding="utf-8", errors="replace", timeout=900)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    text = (ROOT / "frontend/src/lib/declared.test.ts").read_text(encoding="utf-8")
    assert "A product takes this file verbatim" in text
    for case in ("names its manifest path", "refused case", "available case with no manifest"):
        assert case in text, case
