"""The design records state the measured values of the canonical bake (scripts/write_record_tables.py)."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("write_record_tables", ROOT / "scripts" / "write_record_tables.py")
wrt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wrt)


def test_committed_records_state_the_measured_values():
    assert wrt.run(ROOT, check=True) == []


def test_a_cell_is_the_mean_and_the_range_of_the_seeds():
    assert wrt.cell([0.5, 0.6, 0.7]) == "0.6 (0.5 to 0.7)"
    assert wrt.method_of(Path("M07-phase-fixed-wgs.md")) == "M07"
    assert wrt.method_of(Path("B1-device-aware-wgs.md")) == "B1"
    assert wrt.method_of(Path("README.md")) is None


def test_a_row_the_values_cannot_rebuild_is_kept_and_the_rest_is_sorted():
    rows = wrt.merge(["| C03 | 30 | a | b | c |", "| C01 | 30 | a | b | c |"], ["| C10 | 10 | x | not recorded | not recorded |"])
    assert rows == ["| C01 | 30 | a | b | c |", "| C03 | 30 | a | b | c |", "| C10 | 10 | x | not recorded | not recorded |"]


def test_adversarial_a_record_with_another_value_is_reported_stale(tmp_path):
    root = tmp_path / "repo"
    for d in ("docs/design/methods", "data/examples", "data-pipeline/pipeline/cases"):
        (root / d).mkdir(parents=True)
    for f in ("data/examples/cases.json", "data-pipeline/pipeline/cases/measured_ranges.json"):
        shutil.copy(ROOT / f, root / f)
    for f in (ROOT / "docs" / "design" / "methods").glob("*.md"):
        shutil.copy(f, root / "docs" / "design" / "methods" / f.name)
    record = root / "docs" / "design" / "methods" / "M07-phase-fixed-wgs.md"
    text = record.read_bytes().decode("utf-8")
    i = text.index("| C03 | ")
    j = text.index("\n", i)
    j = j - 1 if text[j - 1] == "\r" else j
    record.write_bytes((text[:i] + "| C03 | 30 | 9 (9 to 9) | 9 (9 to 9) | 9 (9 to 9) |" + text[j:]).encode("utf-8"))
    assert wrt.run(root, check=True) == ["docs/design/methods/M07-phase-fixed-wgs.md"]
    assert wrt.run(root, check=False) == ["docs/design/methods/M07-phase-fixed-wgs.md"]
    assert wrt.run(root, check=True) == []
