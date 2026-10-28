"""Pipeline smoke and determinism: a case regenerates deterministically, a refused case is indexed with its reason, a method that
raises or is missing is recorded and fails the bake, the CLI runs, and nothing writes the committed data/derived."""
# ruff: noqa: F811  (pytest fixtures imported from tests/bake/bakefix.py are used by name)
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "bake"))

import bakefix  # noqa: E402
from bakefix import Planted, planted_registry, sandbox_bake, write_cases  # noqa: E402,F401,F811

from pipeline import pipeline  # noqa: E402
from pipeline.bake import BakeFailed  # noqa: E402


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_run_all_writes_index_manifests_traces_and_readiness(sandbox_bake):
    root, _cases, entries = sandbox_bake
    assert [(e["case_id"], e["status"]) for e in entries] == [
        ("C91_mini", "baked"), ("C92_disc", "baked"), ("C93_rearr", "baked"), ("C94_far", "refused")]
    idx = json.loads((root / "manifests" / "index.json").read_text(encoding="utf-8"))
    assert idx["schema"] == "dinhot.index/v1" and idx["default_case"] == "C91_mini"
    assert (root / "readiness.json").is_file() and (root / "C91_mini" / "trace.json").is_file()


def test_same_seed_bakes_identical_bytes_and_a_different_seed_differs(tmp_path, planted_registry):
    cases = write_cases(tmp_path / "c.json", [bakefix.record(feedback=None, dynamics=None)])
    a = pipeline.precompute("C91_mini", output_root=tmp_path / "a", cases_path=cases)
    b = pipeline.precompute("C91_mini", output_root=tmp_path / "b", cases_path=cases)
    c = pipeline.precompute("C91_mini", seed=8, output_root=tmp_path / "c", cases_path=cases)
    first, second = tmp_path / "a" / a["artifact"]["path"], tmp_path / "b" / b["artifact"]["path"]
    assert first.read_bytes() == second.read_bytes() and sha(first) == sha(second)
    assert a["seed"] == b["seed"] == 20261028 and c["seed"] == 8
    assert (tmp_path / "c" / c["artifact"]["path"]).read_bytes() != first.read_bytes()
    raw = bytearray(first.read_bytes())
    at = next(i for i in range(len(raw) - 1, -1, -1) if chr(raw[i]).isdigit())
    raw[at] = ord("0") if raw[at] != ord("0") else ord("1")
    changed = tmp_path / "changed.json"
    changed.write_bytes(bytes(raw))
    assert changed.stat().st_size == first.stat().st_size and sha(changed) != sha(first)   # a byte of equal size is seen


def test_a_refused_case_is_not_computed(tmp_path, planted_registry):
    cases = write_cases(tmp_path / "c.json", [bakefix.refused_record()])
    with pytest.raises(ValueError, match="refused by contract 1"):
        pipeline.precompute("C94_far", output_root=tmp_path / "o", cases_path=cases)
    assert not (tmp_path / "o" / "C94_far").exists()
    with pytest.raises(KeyError):
        pipeline.precompute("C00_unknown", output_root=tmp_path / "o", cases_path=cases)


def test_only_and_resume(tmp_path, planted_registry):
    cases = write_cases(tmp_path / "c.json", [bakefix.record(feedback=None, dynamics=None), bakefix.shaped_record()])
    out = tmp_path / "o"
    pipeline.run_all(output_root=out, cases_path=cases, only=["C92_disc"])
    assert not (out / "C91_mini").exists() and (out / "C92_disc" / "trace.json").is_file()
    idx = json.loads((out / "manifests" / "index.json").read_text(encoding="utf-8"))
    assert [e["case_id"] for e in idx["cases"]] == ["C92_disc"]
    pipeline.run_all(output_root=out, cases_path=cases)
    stamp = (out / "C92_disc" / "trace.json").stat().st_mtime_ns
    pipeline.run_all(output_root=out, cases_path=cases, resume=True)
    assert (out / "C92_disc" / "trace.json").stat().st_mtime_ns == stamp          # unchanged inputs and version: skipped
    with pytest.raises(KeyError, match="unknown case"):
        pipeline.run_all(output_root=out, cases_path=cases, only=["C77_nope"])


def test_adversarial_a_method_that_is_not_registered_fails_unless_allowed(tmp_path, planted_registry):
    rec = bakefix.record(feedback=None, dynamics=None, methods=["M02", "M04", "M06", "M07"])
    cases = write_cases(tmp_path / "c.json", [rec])
    with pytest.raises(BakeFailed, match="C91_mini: methods not registered: M07"):
        pipeline.run_all(output_root=tmp_path / "strict", cases_path=cases)
    pipeline.run_all(output_root=tmp_path / "lenient", cases_path=cases, allow_missing=True)
    m = json.loads((tmp_path / "lenient" / "manifests" / "C91_mini.json").read_text(encoding="utf-8"))
    assert sorted(m["methods"]) == ["M02", "M04", "M06"] == sorted(m["params"]["methods"])
    assert any("not registered" in f["flag"] and "M07" in f["flag"] for f in m["flags"])


def test_adversarial_a_method_that_raises_is_flagged_omitted_and_fails_the_bake(tmp_path):
    with Planted(tmp_path / "pl", ("M02", "M04", "M06", "M09"), "failpkg"):
        rec = bakefix.record(feedback=None, dynamics=None, methods=["M02", "M06", "M09"])
        cases = write_cases(tmp_path / "c.json", [rec])
        with pytest.raises(BakeFailed, match=r"C91_mini method M09: RuntimeError: planted failure"):
            pipeline.run_all(output_root=tmp_path / "o", cases_path=cases)
        m = json.loads((tmp_path / "o" / "manifests" / "C91_mini.json").read_text(encoding="utf-8"))
        t = json.loads((tmp_path / "o" / "C91_mini" / "trace.json").read_text(encoding="utf-8"))
        assert "M09" not in m["methods"] and "M09" not in t["methods"] and "M09" not in m["params"]["methods"]
        assert any("M09" in f["flag"] and "planted failure" in f["flag"] for f in m["flags"])


def test_a_value_outside_its_expected_range_fails_the_bake_naming_it(tmp_path, planted_registry):
    rec = bakefix.record(feedback=None, dynamics=None, expect={"M06.efficiency": [0.99, 1.0]})
    cases = write_cases(tmp_path / "c.json", [rec])
    with pytest.raises(BakeFailed, match=r"C91_mini: method M06 efficiency=.* outside \[0\.99, 1\.0\]"):
        pipeline.run_all(output_root=tmp_path / "o", cases_path=cases)


def test_cli_cases_units_and_readiness(tmp_path, planted_registry, capsys):
    assert pipeline.main(["readiness", "--output", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o" / "readiness.json").is_file()
    assert pipeline.main(["units", "--output", str(tmp_path / "o")]) == 0
    assert "units gate: OK" in capsys.readouterr().out


def test_the_default_output_is_the_sandbox_never_the_repository(tmp_path, planted_registry, _sandboxed_pipeline):
    cases = write_cases(tmp_path / "c.json", [bakefix.record(feedback=None, dynamics=None)])
    m = pipeline.precompute("C91_mini", cases_path=cases)
    assert (_sandboxed_pipeline / m["artifact"]["path"]).is_file()
    assert not (pipeline.REPO / "data" / "derived" / "C91_mini").exists()
