"""The over-budget rule of a time row on the shared fixture (0.02.004, plan decision 10, unit U8b); the TypeScript side reads the same
file in ``frontend/src/content/benchmark/data.test.ts``. Requirement BM-017.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "holographic-trap-studio" / "data"))
import extract_methods as X  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "benchmark-over-budget.json").read_text(encoding="utf-8"))
CELLS = FIXTURE["cells"]


def test_the_fixture_states_the_factor():
    assert FIXTURE["over_budget_factor"] == X.OVER_BUDGET_FACTOR == 1.5


@pytest.mark.parametrize("cell", CELLS, ids=[c["name"] for c in CELLS])
def test_cell_result_on_the_over_budget_fixture(cell):
    got = X.cell_result(cell["rows"])
    assert got["result"] == cell["result"], got.get("reason")
    assert (got["published"] or {}).get("method") == cell["best_published"]
    assert (got["proposed"] or {}).get("method") == cell["best_proposed"]
    assert cell["reason_contains"] in got["reason"]


def test_is_over_budget_cases():
    row = lambda **k: {"method": "B1", "budget_kind": "time", "budget": 1.0, "time_s": {"median": 1.0}, **k}  # noqa: E731
    assert not X.is_over_budget(row())
    assert not X.is_over_budget(row(time_s={"median": 1.5}))
    assert X.is_over_budget(row(time_s={"median": 1.51}))
    assert X.is_over_budget({"method": "B1", "budget_kind": "time", "budget": 1.0})          # no time_s: read as over budget
    assert X.is_over_budget(row(time_s=None))
    assert not X.is_over_budget({"method": "B1", "budget_kind": "time"})                      # no budget declared: not judged
    assert not X.is_over_budget(row(budget_kind="iterations", time_s={"median": 99.0}))
    assert not X.is_over_budget(row(budget_kind="converged", budget=300.0, time_s={"median": 900.0}))


def test_must_refute_an_over_budget_row_is_never_a_best_or_part_of_a_win():
    for cell in CELLS:
        got = X.cell_result(cell["rows"])
        for side in ("published", "proposed"):
            if got[side] is not None:
                assert not X.is_over_budget(got[side]), (cell["name"], side)


def test_no_row_over_budget_leaves_the_reading_unchanged_on_the_win_rule_fixture():
    win = json.loads((ROOT / "tests" / "fixtures" / "benchmark-win-rule.json").read_text(encoding="utf-8"))
    for c in win["cells"]:
        assert not any(X.is_over_budget(r) for r in c["rows"]), c["name"]


def test_adversarial_a_rule_that_never_finds_a_row_over_budget_grants_the_over_budget_win(monkeypatch):
    """BM-017 refuted: with the factor raised so that no row is ever over budget, the cell whose best proposed method ran 1.6 times its
    budget is read as a win of that method, which the fixture forbids."""
    cell = next(c for c in CELLS if c["name"].startswith("over-budget best proposed is skipped"))
    monkeypatch.setattr(X, "OVER_BUDGET_FACTOR", 1e9)
    assert X.cell_result(cell["rows"])["proposed"]["method"] == "B1" != cell["best_proposed"]
