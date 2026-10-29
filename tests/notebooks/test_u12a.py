"""Row tests of the notebooks of unit U12a (topics 01 to 04, English and Spanish) and planted defects.

The rows pin what the unit promised: ten notebooks per language at their levels, the same paths in both trees, the question and
the answer, a level 3 notebook that runs slmsuite under State of the art, a level 4 notebook that names its claim. The plants
copy a committed notebook in memory, break one rule of the bar (a long line, an answer that quotes no printed number, a missing
state-of-the-art cell, a missing table under Beyond) and expect the gate of ``scripts/check_notebooks.py`` to say so; the
unbroken notebook is the control. Nothing here executes a notebook: the runner does that (``scripts/run_notebooks.py --check``).
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LANGS = ("en", "es")

# path below notebooks/<language>/ -> (level, claims the notebook demonstrates)
ROWS = {
    "01-fourier-optics/01-where-the-light-goes": (1, []),
    "01-fourier-optics/02-reading-a-trap-array": (2, []),
    "02-analytic-holograms/01-superposition-and-random-mask": (1, []),
    "02-analytic-holograms/02-the-ten-by-ten-benchmark": (2, []),
    "03-gerchberg-saxton/01-the-gs-loop": (1, []),
    "03-gerchberg-saxton/02-weights-for-uniformity": (2, []),
    "03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite": (3, []),
    "03-gerchberg-saxton/04-device-aware-wgs": (4, ["BS-1"]),
    "04-shaped-potentials/03-mraf-and-the-signal-region": (3, []),
    "04-shaped-potentials/04-optimal-transport-start": (3, []),
}
METHODS = {"03-gerchberg-saxton/03-phase-fixed-wgs-against-slmsuite": ["M07"],
           "04-shaped-potentials/03-mraf-and-the-signal-region": ["M08"],
           "04-shaped-potentials/04-optimal-transport-start": ["M18"]}
LEVEL3 = [k for k, (level, _) in ROWS.items() if level == 3]
LEVEL4 = [k for k, (level, _) in ROWS.items() if level == 4]
MARKERS = {"en": ("**Question:**", "**Answer:**"), "es": ("**Pregunta:**", "**Respuesta:**")}
SOTA = {"en": "State of the art", "es": "Estado del arte"}
BEYOND = {"en": "Beyond the state of the art", "es": "Más allá del estado del arte"}


def load_gate():
    spec = importlib.util.spec_from_file_location("check_notebooks", ROOT / "scripts" / "check_notebooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = load_gate()
BAR = GATE.load_bar()


def path_of(lang: str, row: str) -> Path:
    return ROOT / "notebooks" / lang / f"{row}.ipynb"


def read(lang: str, row: str) -> dict:
    return json.loads(path_of(lang, row).read_text(encoding="utf-8"))


def text(cell: dict) -> str:
    src = cell["source"]
    return src if isinstance(src, str) else "".join(src)


def findings_of(nb: dict, lang: str, row: str) -> list[str]:
    reading = GATE.Reading(nb, lang, ROOT, BAR)
    return GATE.reading_findings(f"notebooks/{lang}/{row}.ipynb", reading, BAR)


CASES = [(lang, row) for lang in LANGS for row in ROWS]


@pytest.mark.parametrize("lang,row", CASES)
def test_notebook_exists_with_its_level_and_topic(lang, row):
    nb = read(lang, row)
    caos = nb["metadata"]["caos"]
    level, beyond = ROWS[row]
    assert caos["language"] == lang
    assert caos["topic"] == row.split("/")[0]
    assert caos["level"] == level
    assert caos["beyond"] == beyond
    assert caos.get("methods", []) == METHODS.get(row, [])


def test_the_two_trees_hold_the_same_paths():
    for row in ROWS:
        assert path_of("en", row).is_file(), row
        assert path_of("es", row).is_file(), row


def test_levels_never_decrease_within_a_topic():
    by_topic: dict[str, list[int]] = {}
    for row, (level, _) in sorted(ROWS.items()):
        by_topic.setdefault(row.split("/")[0], []).append(level)
    for topic, levels in by_topic.items():
        assert levels == sorted(levels), topic


@pytest.mark.parametrize("row", ROWS)
def test_the_spanish_notebook_mirrors_the_english_one(row):
    en, es = read("en", row), read("es", row)
    kinds = lambda nb: [c["cell_type"] for c in nb["cells"]]  # noqa: E731
    assert kinds(en) == kinds(es)
    figures = lambda nb: sum(  # noqa: E731
        1 for c in nb["cells"] if c["cell_type"] == "code" for o in c.get("outputs", []) if "image/png" in o.get("data", {}))
    assert figures(en) == figures(es) > 0


@pytest.mark.parametrize("lang,row", CASES)
def test_question_first_and_answer_in_results(lang, row):
    nb = read(lang, row)
    question, answer = MARKERS[lang]
    assert question in text(nb["cells"][0])
    results = [text(c) for c in nb["cells"] if c["cell_type"] == "markdown" and text(c).lstrip().startswith(
        "## Results" if lang == "en" else "## Resultados")]
    assert results and answer in results[0]


@pytest.mark.parametrize("lang,row", CASES)
def test_every_code_cell_ran_clean(lang, row):
    nb = read(lang, row)
    count = 0
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        count += 1
        assert cell["execution_count"] == count
        assert all(o["output_type"] != "error" and o.get("name") != "stderr" for o in cell.get("outputs", []))


@pytest.mark.parametrize("lang,row", CASES)
def test_no_code_line_is_too_long_and_no_statements_are_doubled(lang, row):
    nb = read(lang, row)
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert max(len(line) for line in text(cell).splitlines()) <= BAR["floors"]["line_chars_max"]


@pytest.mark.parametrize("lang,row", CASES)
def test_the_gate_has_no_finding_for_the_notebook(lang, row):
    assert findings_of(read(lang, row), lang, row) == []


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("row", LEVEL3)
def test_a_level_3_notebook_runs_slmsuite_under_state_of_the_art(lang, row):
    nb = read(lang, row)
    section, cells = None, []
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == SOTA[lang]:
            cells.append(cell)
    assert any("SpotHologram" in text(c) or "Hologram(" in text(c) for c in cells)
    assert any("image/png" in o.get("data", {}) for c in cells for o in c.get("outputs", []))
    assert "slmsuite==0.5.0" in nb["metadata"]["caos"]["packages"]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("row", LEVEL4)
def test_a_level_4_notebook_measures_its_claim_against_the_strongest_baseline(lang, row):
    nb = read(lang, row)
    body = "\n".join(text(c) for c in nb["cells"])
    assert "BS-1" in nb["metadata"]["caos"]["beyond"]
    assert "m07_phase_fixed_wgs" in body and "b1_device_wgs" in body
    assert "m13_crosstalk_cg" in body


# ---- planted defects: each one breaks a rule of the bar in a copy, the gate must say so ----

LONG_LINE = "# " + "x" * 125


def plant_long_line(nb: dict) -> None:
    code = next(c for c in nb["cells"] if c["cell_type"] == "code")
    code["source"] = text(code) + "\n" + LONG_LINE


def plant_unprinted_answer(nb: dict) -> None:
    results = next(c for c in nb["cells"] if c["cell_type"] == "markdown" and text(c).lstrip().startswith("## Results"))
    head, _, tail = text(results).partition("**Answer:**")
    paragraph, sep, rest = tail.partition("\n\n")
    paragraph = re.sub(r"\d+(?:[.,]\d+)?", "98765.4321", paragraph)
    results["source"] = head + "**Answer:**" + paragraph + sep + rest


def plant_no_state_of_the_art_cell(nb: dict) -> None:
    section = None
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == SOTA["en"]:
            cell["source"] = "# a comment and nothing else\nprint('no method here')"
            cell["outputs"] = []


def plant_no_table_under_beyond(nb: dict) -> None:
    section = None
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == BEYOND["en"]:
            cell["outputs"] = [o for o in cell.get("outputs", []) if o["output_type"] == "stream"]
            cell["source"] = re.sub(r"plt\.\w+\(.*\)", "pass", text(cell))


def plant_copied_template_sentence(nb: dict) -> None:
    nb["cells"][1]["source"] = text(nb["cells"][1]) + "\n\nInterpret the method with its units.\n"


PLANTS = [
    (plant_long_line, "characters", "01-fourier-optics/01-where-the-light-goes"),
    (plant_unprinted_answer, "answer quotes no number", "03-gerchberg-saxton/02-weights-for-uniformity"),
    (plant_no_state_of_the_art_cell, "no method cell under State of the art", LEVEL3[0]),
    (plant_no_table_under_beyond, "Beyond the state of the art", LEVEL4[0]),
    (plant_copied_template_sentence, "generic filler sentence", "02-analytic-holograms/01-superposition-and-random-mask"),
]


@pytest.mark.parametrize("plant,expect,row", PLANTS, ids=[p[0].__name__ for p in PLANTS])
def test_the_gate_catches_each_planted_defect(plant, expect, row):
    nb = copy.deepcopy(read("en", row))
    assert findings_of(nb, "en", row) == []          # the control: the unbroken copy is clean
    plant(nb)
    found = findings_of(nb, "en", row)
    assert any(expect in f for f in found), found
