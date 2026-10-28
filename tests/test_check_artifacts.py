"""The example's artifact guard (scripts/check_artifacts.py) reads one artifact or many per manifest and the index's
declared files. The guard is the example's, shaped by its manifest contract: a product adapts it to its own manifests and
replaces this test with its own (BD-4: it lived in test_guards.py, which a product takes as it is)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)


def _put(root: Path, rel: str, doc) -> int:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(doc).encode("utf-8"))
    return p.stat().st_size


def test_check_artifacts_reads_one_or_many_artifacts_and_the_index_files(tmp_path):
    d = tmp_path / "data" / "derived"
    n_single = _put(d, "A/trace.json", {"t": [0, 1]})
    n_v1 = _put(d, "B/v1.json", {"x": 1})
    n_v2 = _put(d, "B/v2.json", {"x": 22})
    _put(d, "contract/index.json", {"families": []})
    gate = {"lane": "live"}
    _put(d, "manifests/A.json", {"artifact": {"path": "A/trace.json", "bytes": n_single}, "lane": "live", "gate": gate})
    _put(d, "manifests/B.json", {"artifacts": [{"path": "B/v1.json", "bytes": n_v1, "lane": "live", "gate": gate},
                                               {"path": "B/v2.json", "bytes": n_v2, "lane": "live", "gate": gate}]})
    index = {"files": ["contract/index.json"], "cases": [{"case_id": "A", "manifest_path": "manifests/A.json"},
                                                         {"case_id": "B", "manifest_path": "manifests/B.json"}]}
    _put(d, "manifests/index.json", index)
    ok = _run("check_artifacts.py", str(tmp_path))
    assert ok.returncode == 0 and "2 cases, 3 artifacts" in ok.stdout, ok.stdout
    # drift in the second variant, a lane that disagrees with its gate, a declared file gone
    _put(d, "manifests/B.json", {"artifacts": [{"path": "B/v1.json", "bytes": n_v1, "lane": "live", "gate": gate},
                                               {"path": "B/v2.json", "bytes": n_v2 + 1, "lane": "precompute", "gate": gate}]})
    (d / "contract" / "index.json").unlink()
    bad = _run("check_artifacts.py", str(tmp_path))
    assert bad.returncode == 1
    assert "byte drift" in bad.stdout and "B/v2.json" in bad.stdout
    assert "lane/gate mismatch: B B/v2.json" in bad.stdout
    assert "declared by the index but missing or empty" in bad.stdout
