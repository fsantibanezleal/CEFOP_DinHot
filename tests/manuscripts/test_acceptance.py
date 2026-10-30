"""The acceptance table of the studio manuscript is measured, not quoted (``manuscripts/holographic-trap-studio/data``).

``acceptance.py`` measures the acceptance quantity of every ladder method as its gate test computes it and writes
``acceptance.json``; ``extract.py`` builds the table from that file. These tests pin the file's shape, that every number of a
row's text comes from the row's measured numbers (or is a setup constant named below), and that ``extract.py`` types no
acceptance string (a planted one fails).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "manuscripts" / "holographic-trap-studio" / "data"
IDS = ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14", "M15", "M16", "M17",
       "M18", "M19", "BS-4", "BS-5"]       # the rows of the table before it was measured (M01 to M19, BS-4, BS-5)
# Decimal constants that describe a row's setup (a bar, a gain, a start), not a measured value; they appear in the text by design.
SETUP_CONSTANTS = {"M06": {"0.9", "0.98"}, "M07": {"0.5"}, "BS-4": {"0.5"}}
DECIMAL = re.compile(r"(?<![\w.])-?\d+\.\d+(?:e-?\d+)?")


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem + "_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def doc():
    return json.loads((DATA / "acceptance.json").read_text(encoding="utf-8"))


def flatten(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from flatten(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from flatten(v)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield float(x)


def candidates(x) -> list[float]:
    """Every value of a row's numbers, plus the median, minimum and maximum of each list (the row's text quotes those)."""
    out = list(flatten(x))
    stack = [x]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            stack += list(n.values())
        elif isinstance(n, list):
            vals = [float(v) for v in n if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if vals:
                vals.sort()
                out += [vals[0], vals[-1], (vals[(len(vals) - 1) // 2] + vals[len(vals) // 2]) / 2]
            stack += [v for v in n if isinstance(v, (list, dict))]
    return out


def typed_acceptance_strings(source: str) -> list[str]:
    """String constants with a digit inside the right-hand side of ``UNIT_ACCEPTANCE = ...`` (empty when the table is built)."""
    out = []
    for node in ast.walk(ast.parse(source)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(t, ast.Name) and t.id == "UNIT_ACCEPTANCE" for t in targets) and node.value is not None:
            out += [c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)
                    and re.search(r"\d", c.value)]
    return out


def test_acceptance_json_has_a_measured_row_for_every_id(doc):
    rows = {r["id"]: r for r in doc["rows"]}
    assert [r["id"] for r in doc["rows"]] == IDS
    for mid in IDS:
        r = rows[mid]
        assert r["text"] and r["seeds"] and r["source"], mid
        nums = list(flatten(r["numbers"]))
        assert nums and all(math.isfinite(v) for v in nums), (mid, r["numbers"])
        assert (ROOT / r["source"].split(" ")[0].split(";")[0]).is_file(), (mid, r["source"])   # the gate test it mirrors exists
    assert not any("report" in r["source"].lower() for r in doc["rows"])                        # no unit report as a source


def test_every_decimal_of_a_text_comes_from_its_measured_numbers(doc):
    for r in doc["rows"]:
        nums = candidates(r["numbers"])
        for tok in DECIMAL.findall(r["text"]):
            if tok in SETUP_CONSTANTS.get(r["id"], ()):
                continue
            val = float(tok)
            digits = len(tok.split("e")[0].split(".")[1])
            tol = 0.5 * 10 ** (-digits) if "e" not in tok else abs(val) * 0.06
            assert any(abs(v - val) <= tol * 1.0001 for v in nums), (r["id"], tok, r["text"])


def test_extract_builds_the_acceptance_table_from_the_file(doc):
    ex = load_module(DATA / "extract.py")
    assert [row[0] for row in ex.UNIT_ACCEPTANCE] == IDS
    for (mid, text, seeds, src), r in zip(ex.UNIT_ACCEPTANCE, doc["rows"]):
        assert (mid, text, seeds, src) == (r["id"], r["text"], r["seeds"], r["source"])
    tex = ex.table_acceptance()
    assert tex.count("\\\n") >= len(IDS) and "acceptance.py" in (DATA / "extract.py").read_text(encoding="utf-8")


def test_extract_types_no_acceptance_number():
    assert typed_acceptance_strings((DATA / "extract.py").read_text(encoding="utf-8")) == []


def test_a_planted_typed_string_is_detected():
    src = (DATA / "extract.py").read_text(encoding="utf-8")
    planted = src.replace("UNIT_ACCEPTANCE = ", 'UNIT_ACCEPTANCE = [("M01", "efficiency 0.281", "1", "E2 D5")] + ', 1)
    assert planted != src and "efficiency 0.281" in typed_acceptance_strings(planted)
    assert typed_acceptance_strings('UNIT_ACCEPTANCE = [("M01", "efficiency 0.281", "1", "E2 D5")]') != []
