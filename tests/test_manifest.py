"""CONTRACT 2 (artifact) tests: the manifest points to a real artifact with the recorded byte size, the lane verdict is consistent
with the gate, the manifest is a pure function of (params, seed), and no trace exceeds the lane gate."""
# ruff: noqa: F811  (pytest fixtures imported from tests/bake/bakefix.py are used by name)
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "bake"))

import bakefix  # noqa: E402,F401  (the fixtures sandbox_bake and planted_registry come from tests/bake/conftest.py's import)
from bakefix import planted_registry, sandbox_bake, write_cases  # noqa: E402,F401

from pipeline import pipeline  # noqa: E402
from pipeline.core.gate import RUN_MS_GATE, TRACE_BYTES_GATE  # noqa: E402


def manifests(root: Path):
    for p in sorted((root / "manifests").glob("C*.json")):
        yield json.loads(p.read_text(encoding="utf-8"))


def test_manifest_matches_artifact_and_gate(sandbox_bake):
    root = sandbox_bake[0]
    found = list(manifests(root))
    assert {m["case_id"] for m in found} == {"C91_mini", "C92_disc", "C93_rearr"}
    for m in found:
        artifact = root / m["artifact"]["path"]
        assert artifact.stat().st_size == m["artifact"]["bytes"], "manifest byte size drifted from the artifact"
        assert m["schema"] == "dinhot.manifest/v1" and m["engine"]["package"] == "dinhot-holo"
        assert m["lane"] in ("live", "precompute") and m["gate"]["lane"] == m["lane"]
        assert m["gate"]["run_ms_budget"] == RUN_MS_GATE and m["gate"]["trace_bytes_budget"] == TRACE_BYTES_GATE


def test_every_trace_is_within_the_lane_gate(sandbox_bake):
    for m in manifests(sandbox_bake[0]):
        assert 0 < m["artifact"]["bytes"] <= TRACE_BYTES_GATE, m["case_id"]


def test_lane_follows_the_reference_method_spec(sandbox_bake):
    by = {m["case_id"]: m for m in manifests(sandbox_bake[0])}
    assert by["C91_mini"]["lane"] == "live" and by["C91_mini"]["methods"]["M06"]["lane"] == "live"
    disc = by["C92_disc"]            # M08 is baked-lane in the planted registry
    assert disc["lane"] == "precompute" and disc["methods"]["M08"]["lane"] == "baked"
    assert any("baked-lane" in r for r in disc["gate"]["reasons"])


def test_models_record_what_produced_the_metrics(sandbox_bake):
    for m in manifests(sandbox_bake[0]):
        assert m["models"] == {"cgh-net": "baseline", "warmstart-model": "baseline"}


def test_adversarial_two_bakes_of_the_same_inputs_write_identical_bytes(tmp_path, planted_registry):
    """Must refute: a manifest (or trace) that changes between two bakes of the same inputs."""
    cases = write_cases(tmp_path / "cases.json", [bakefix.record(), bakefix.shaped_record()])
    pipeline.run_all(output_root=tmp_path / "a", cases_path=cases)
    pipeline.run_all(output_root=tmp_path / "b", cases_path=cases)
    files = sorted(p.relative_to(tmp_path / "a") for p in (tmp_path / "a").rglob("*.json"))
    assert len(files) >= 5
    for rel in files:
        a, b = (tmp_path / "a" / rel).read_bytes(), (tmp_path / "b" / rel).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), rel
