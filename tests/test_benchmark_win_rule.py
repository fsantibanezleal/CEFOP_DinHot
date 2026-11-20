"""The win rule of a benchmark cell on the shared fixture (0.02.004, plan decision 2); the TypeScript side reads the same file in
``frontend/src/content/benchmark/data.test.ts``. Requirements: BM-015 (the win rule), BM-016 (a 1.x file is refused).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "manuscripts" / "holographic-trap-studio" / "data"))
import extract_methods as X  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "benchmark-win-rule.json").read_text(encoding="utf-8"))


def test_the_fixture_states_the_rule_constants():
    assert FIXTURE["min_seeds"] == X.WIN_MIN_SEEDS == 5 and FIXTURE["min_diff_pct"] == X.WIN_MIN_DIFF_PCT == 0.01


@pytest.mark.parametrize("cell", FIXTURE["cells"], ids=[c["name"] for c in FIXTURE["cells"]])
def test_cell_result_on_the_shared_fixture(cell):
    got = X.cell_result(cell["rows"])
    assert got["result"] == cell["result"], got.get("reason")
    assert (got["published"] or {}).get("method") == cell["best_published"]
    assert (got["proposed"] or {}).get("method") == cell["best_proposed"]


def test_must_refute_no_win_with_four_seeds_overlap_or_a_0009_difference():
    names = {c["name"]: c for c in FIXTURE["cells"]}
    for key in ("tie: 4 seeds on one side", "tie: overlapping IQRs", "tie: medians 0.009 apart with disjoint IQRs"):
        assert X.cell_result(names[key]["rows"])["result"] == "tie"


def _doc(rows, geometries=("G1",)):
    return {"rows": rows, "geometries": [{"id": g} for g in geometries]}


def test_a_1x_file_is_refused_naming_the_contract_version():
    with pytest.raises(SystemExit, match=r"benchmark-results 1\.x.*2\.0\.0"):
        X.require_contract(_doc([{"method": "M04"}]), "test")
    with pytest.raises(SystemExit, match="1.x"):
        X.require_contract(_doc([{"method": "M04", "evaluations": {}}], ("G6",)), "test")
    X.require_contract(_doc([{"method": "M04", "evaluations": {}}], ("G6a", "G6b")), "test")
