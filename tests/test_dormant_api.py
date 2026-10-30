"""The dormant app/ serves the committed contract-2 documents as they are and nothing outside data/derived. The service layer is
standard library only, so this runs without the API lane installed; DATA_DIR selects the tree (a sandbox bake, the provider tree)."""
# ruff: noqa: F811  (pytest fixtures imported from tests/bake/bakefix.py are used by name)
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "bake"))

from bakefix import planted_registry, sandbox_bake  # noqa: E402,F401

from app.services import content  # noqa: E402

FIXTURE = ROOT / "docs" / "contracts" / "fixtures" / "data" / "derived"


def point(monkeypatch, root) -> None:
    monkeypatch.setenv("DATA_DIR", str(root))


def test_serves_the_index_every_baked_manifest_and_the_trace_it_names(monkeypatch, sandbox_bake):
    for root in (sandbox_bake[0], FIXTURE):
        point(monkeypatch, root)
        index = content.load_index()
        assert index is not None and index["cases"]
        baked = [e for e in index["cases"] if e["status"] == "baked"]
        assert baked
        for entry in baked:
            m = content.load_manifest(entry["case_id"])
            assert m is not None and m["case_id"] == entry["case_id"]
            paths = content.artifact_paths(m)
            assert paths, entry["case_id"]
            for rel in paths:
                assert content.load_artifact(rel) is not None, rel
        for entry in index["cases"]:
            if entry["status"] == "refused":
                assert content.load_manifest(entry["case_id"]) is None        # a refused case has no manifest


def test_reads_both_forms_of_a_manifest():
    assert content.artifact_paths({"artifact": {"path": "A/trace.json"}}) == ["A/trace.json"]
    assert content.artifact_paths({"artifacts": [{"path": "B/v1.json"}, {"path": "B/v2.json"}]}) == ["B/v1.json", "B/v2.json"]
    assert content.artifact_paths({}) == []


def test_nothing_outside_the_derived_root(monkeypatch, sandbox_bake):
    point(monkeypatch, sandbox_bake[0])
    assert content.load_artifact("../../VERSION") is None
    assert content.load_artifact("manifests/../../../pyproject.toml") is None
    assert content.load_manifest("../index") is None
    assert content.load_manifest("..\index") is None


def test_an_absent_document_is_none_not_an_empty_body(tmp_path, monkeypatch):
    point(monkeypatch, tmp_path)
    assert content.load_index() is None and content.load_readiness() is None
    assert content.load_benchmark() is None and content.load_metrics() is None
    assert content.load_manifest("C01_square_grid") is None


def test_benchmark_and_metrics_are_served_unchanged(monkeypatch):
    point(monkeypatch, FIXTURE)
    assert content.load_benchmark()["schema"] == "dinhot.benchmark/v1"
    assert content.load_metrics()["schema"] == "dinhot.model-metrics/v1"


def test_readiness_is_the_committed_document_with_the_api_row_available(monkeypatch):
    point(monkeypatch, FIXTURE)
    doc = content.load_readiness()
    assert doc is not None
    api = next(e for e in doc["contracts"] if e["id"] == "api")
    assert (api["state"], api["provenance"], api["reason"], api["missing"]) == ("available", "real", None, [])
    assert [e for e in doc["contracts"] if e["id"] != "api"]
