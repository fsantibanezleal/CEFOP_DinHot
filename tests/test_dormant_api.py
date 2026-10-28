"""The dormant app/ serves the committed contract-2 documents as they are, in either manifest form, and nothing
outside data/derived (it used to read the template example's manifest shape, so it broke in every product
whose manifests differ). The service layer is stdlib only, so this runs without the API lane installed."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import content  # noqa: E402


def test_serves_the_index_every_manifest_and_every_artifact_it_names():
    index = content.load_index()
    assert index is not None and index["cases"], "the committed index lists the baked cases"
    for entry in index["cases"]:
        m = content.load_manifest(entry["case_id"])
        assert m is not None and m["case_id"] == entry["case_id"]
        paths = content.artifact_paths(m)
        assert paths, f"{entry['case_id']}: the manifest names no artifact"
        for rel in paths:
            assert content.load_artifact(rel) is not None, rel


def test_reads_both_forms_of_a_manifest():
    assert content.artifact_paths({"artifact": {"path": "A/trace.json"}}) == ["A/trace.json"]
    assert content.artifact_paths({"artifacts": [{"path": "B/v1.json"}, {"path": "B/v2.json"}]}) == ["B/v1.json", "B/v2.json"]
    assert content.artifact_paths({}) == []


def test_nothing_outside_the_derived_root():
    assert content.load_artifact("../../VERSION") is None
    assert content.load_artifact("manifests/../../../pyproject.toml") is None
    assert content.load_artifact("../../package.json") is None
    assert content.load_manifest("../index") is None
    assert content.load_manifest("..\\index") is None


def test_an_absent_index_is_none_not_an_empty_index(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert content.load_index() is None
    assert content.load_readiness() is None
    assert content.load_manifest("EX01_subcritical") is None


def test_readiness_is_the_committed_document_with_the_api_row_available():
    doc = content.load_readiness()
    assert doc is not None
    api = next(e for e in doc["contracts"] if e["id"] == "api")
    assert (api["state"], api["provenance"], api["reason"], api["missing"]) == ("available", "real", None, [])
    others = [e["state"] for e in doc["contracts"] if e["id"] != "api"]
    assert others  # the other rows are served unchanged
