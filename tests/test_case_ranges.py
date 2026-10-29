"""The case cards state the ranges the bake checks (scripts/write_case_ranges.py)."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("write_case_ranges", ROOT / "scripts" / "write_case_ranges.py")
wcr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wcr)


def test_committed_cards_state_the_ranges_the_bake_checks():
    assert wcr.run(ROOT, check=True) == []


def test_the_section_is_replaced_between_its_heading_and_the_next_section():
    text = "# C\n\n## Expected results\n\nprose\n\n" + wcr.HEADING + "\n\nold table\n\n## Validation anchor\n\nanchor\n"
    out = wcr.replace_section(text, wcr.HEADING + "\n\nnew\n\n", "planted")
    assert out == "# C\n\n## Expected results\n\nprose\n\n" + wcr.HEADING + "\n\nnew\n\n## Validation anchor\n\nanchor\n"
    with pytest.raises(ValueError, match="no heading"):
        wcr.replace_section("# C\n", "x", "planted")


def test_adversarial_a_card_with_another_range_is_reported_stale(tmp_path):
    root = tmp_path / "repo"
    for d in ("docs/cases", "data-pipeline", "docs/contracts"):
        shutil.copytree(ROOT / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
    card = next((root / "docs" / "cases").glob("*/C01_square_grid.md"))
    text = card.read_text(encoding="utf-8")
    i = text.index("| `M04.efficiency` |")
    j = text.index("\n", i)
    card.write_text(text[:i] + "| `M04.efficiency` | 0 to 1 | planted | planted |" + text[j:], encoding="utf-8")
    stale = wcr.run(root, check=True)
    assert stale == ["docs/cases/arrays/C01_square_grid.md"]
    assert wcr.run(root, check=False) == ["docs/cases/arrays/C01_square_grid.md"] and wcr.run(root, check=True) == []


def test_every_metric_of_every_range_has_a_meaning():
    with pytest.raises(KeyError, match="no meaning"):
        wcr._meaning("M04.planted_metric")
