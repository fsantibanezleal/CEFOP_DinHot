"""The artifact guard (scripts/check_artifacts.py) for DinHot's contract 2: it passes on a bake and fails on each kind of drift
(byte drift, lane/gate mismatch, an oversize trace, a refused case with a manifest, a units violation, a missing trace)."""
# ruff: noqa: F811  (pytest fixtures imported from tests/bake/bakefix.py are used by name)
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "bake"))

from bakefix import planted_registry, sandbox_bake  # noqa: E402,F401


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_artifacts.py"), str(root)], capture_output=True, text=True)


@pytest.fixture()
def tree(tmp_path, sandbox_bake):
    d = tmp_path / "data" / "derived"
    shutil.copytree(sandbox_bake[0], d)
    return tmp_path


def edit(path: Path, change) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def test_passes_on_a_bake(tree):
    p = run(tree)
    assert p.returncode == 0, p.stdout
    assert "3 baked and 1 refused cases, 3 artifacts" in p.stdout and "units gate holds" in p.stdout


def test_adversarial_each_drift_is_reported(tree):
    d = tree / "data" / "derived"
    edit(d / "manifests" / "C91_mini.json", lambda m: m["artifact"].__setitem__("bytes", m["artifact"]["bytes"] + 1))
    edit(d / "manifests" / "C92_disc.json", lambda m: m.__setitem__("lane", "live" if m["lane"] == "precompute" else "precompute"))
    (d / "manifests" / "C94_far.json").write_text("{}", encoding="utf-8")
    edit(d / "C93_rearr" / "trace.json", lambda t: t["methods"]["M06"]["final"].__setitem__("rel_std_pct", 1e-4))
    p = run(tree)
    assert p.returncode == 1
    assert "byte drift" in p.stdout and "C91_mini" in p.stdout
    assert "lane/gate mismatch: C92_disc" in p.stdout
    assert "C94_far: refused in the index but a manifest exists" in p.stdout
    assert "units: C93_rearr M06" in p.stdout


def test_adversarial_oversize_trace_and_missing_trace(tree):
    d = tree / "data" / "derived"
    big = d / "C91_mini" / "trace.json"
    big.write_bytes(big.read_bytes() + b" " * (256 * 1024))
    edit(d / "manifests" / "C91_mini.json", lambda m: m["artifact"].__setitem__("bytes", big.stat().st_size))
    (d / "C93_rearr" / "trace.json").unlink()
    p = run(tree)
    assert p.returncode == 1
    assert "over the 262144 byte lane gate" in p.stdout and "missing artifact" in p.stdout


def test_a_declared_absent_trace_is_a_warning_only_when_readiness_says_so(tree):
    d = tree / "data" / "derived"
    (d / "C93_rearr" / "trace.json").unlink()
    rd = json.loads((d / "readiness.json").read_text(encoding="utf-8"))
    for e in rd["contracts"]:
        if e["id"] == "trace":
            e.update(state="partial", missing=["C93_rearr/trace.json"])
    (d / "readiness.json").write_text(json.dumps(rd), encoding="utf-8")
    p = run(tree)
    assert p.returncode == 0 and "declared absent" in p.stdout


def test_no_index_is_a_failure(tmp_path):
    (tmp_path / "data" / "derived").mkdir(parents=True)
    assert run(tmp_path).returncode == 1
