"""Row tests of the notebooks of unit U12b (topics 05 to 07, English and Spanish) and planted defects.

The rows pin what the unit promised: fourteen notebooks per language at their levels (levels 3 name their sota method), the same paths in both trees, the question and
the answer, a level 4 notebook that names its claim and measures it against a baseline of the product, levels that never
decrease inside a topic and that cover levels 1 and 2 in every topic. The plants copy a committed notebook in memory, break one
rule of the bar (a long line, an answer that quotes no printed number, a missing table or figure under Beyond, a copied
template sentence, a method that is only handed over as a callback) and expect the gate of ``scripts/check_notebooks.py`` to say
so; the unbroken notebook is the control. Nothing here executes a notebook: the runner does that
(``scripts/run_notebooks.py --check``).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LANGS = ("en", "es")

# path below notebooks/<language>/ -> (level, claims the notebook demonstrates, sota methods it runs)
ROWS = {
    "05-optimization/01-the-cost-and-its-gradient": (1, [], []),
    "05-optimization/02-the-wirtinger-gradient-and-adams-step": (2, [], []),
    "05-optimization/03-conjugate-gradient-against-weighted-gs": (3, [], ["M10"]),
    "05-optimization/04-wirtinger-adam-against-gerchberg-saxton": (3, [], ["M11"]),
    "05-optimization/05-the-efficiency-uniformity-front": (4, ["BS-5"], []),
    "06-device-and-aberrations/01-what-the-device-costs": (1, [], []),
    "06-device-and-aberrations/02-zernike-correction": (2, [], []),
    "06-device-and-aberrations/03-crosstalk-aware-cg-against-cg": (3, [], ["M13"]),
    "06-device-and-aberrations/04-robust-holograms": (4, ["BS-4"], []),
    "07-feedback-and-dynamics/01-a-bead-in-the-computed-trap": (1, [], []),
    "07-feedback-and-dynamics/02-assigning-atoms-to-sites": (2, [], []),
    "07-feedback-and-dynamics/03-closed-loop-feedback": (3, [], ["M12"]),
    "07-feedback-and-dynamics/04-moving-atoms-by-linear-phase-interpolation": (3, [], ["M16"]),
    "07-feedback-and-dynamics/05-flicker-bounded-moves": (4, ["BS-2"], []),
}
# the product module a level 3 notebook must call under State of the art, per sota method
LEVEL3 = {"M10": "m10_cg", "M11": "m11_wirtinger_adam", "M12": "m12_closed_loop", "M13": "m13_crosstalk_cg", "M16": "m16_rearrangement"}
# the product methods a level 4 notebook must run, as the baseline and as the claimed method
LEVEL4 = {
    "05-optimization/05-the-efficiency-uniformity-front": ("m06_gsw", "b5_pareto", "m09_direct_search"),
    "06-device-and-aberrations/04-robust-holograms": ("m07_phase_fixed_wgs", "b4_robust", "ensemble_stats"),
    "07-feedback-and-dynamics/05-flicker-bounded-moves": ("m16_rearrangement", "b2_flicker_bounded", "transient_min_ratio"),
}
MARKERS = {"en": ("**Question:**", "**Answer:**"), "es": ("**Pregunta:**", "**Respuesta:**")}
BEYOND = {"en": "Beyond the state of the art", "es": "Más allá del estado del arte"}
RESULTS = {"en": "## Results", "es": "## Resultados"}


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
    level, beyond, methods = ROWS[row]
    assert caos["language"] == lang
    assert caos["topic"] == row.split("/")[0]
    assert caos["level"] == level
    assert caos["beyond"] == beyond
    assert caos.get("methods", []) == methods


def test_the_two_trees_hold_the_same_paths():
    for row in ROWS:
        assert path_of("en", row).is_file(), row
        assert path_of("es", row).is_file(), row


def test_levels_never_decrease_and_every_topic_has_levels_1_and_2():
    by_topic: dict[str, list[int]] = {}
    for row, (level, _, _) in sorted(ROWS.items()):
        by_topic.setdefault(row.split("/")[0], []).append(level)
    for topic, levels in by_topic.items():
        assert levels == sorted(levels), topic
        assert {1, 2} <= set(levels), topic


def test_the_sota_methods_of_the_unit_are_m10_to_m13_and_m16():
    named = sorted(m for _, _, methods in ROWS.values() for m in methods)
    assert named == ["M10", "M11", "M12", "M13", "M16"]


def test_the_claims_of_the_unit_are_bs_2_bs_4_and_bs_5():
    claims = sorted(c for _, beyond, _ in ROWS.values() for c in beyond)
    assert claims == ["BS-2", "BS-4", "BS-5"]


@pytest.mark.parametrize("row", ROWS)
def test_the_spanish_notebook_mirrors_the_english_one(row):
    en, es = read("en", row), read("es", row)
    kinds = lambda nb: [c["cell_type"] for c in nb["cells"]]  # noqa: E731
    assert kinds(en) == kinds(es)
    figures = lambda nb: sum(  # noqa: E731
        1 for c in nb["cells"] if c["cell_type"] == "code" for o in c.get("outputs", []) if "image/png" in o.get("data", {}))
    assert figures(en) == figures(es) > 0
    code = lambda nb: [  # noqa: E731
        re.sub(r"\s+", " ", re.sub(r"#.*|\"[^\"]*\"|'[^']*'", "", text(c))) for c in nb["cells"] if c["cell_type"] == "code"]
    assert code(en) == code(es)       # the same computation: only comments and printed words differ


@pytest.mark.parametrize("lang,row", CASES)
def test_question_first_and_answer_in_results(lang, row):
    nb = read(lang, row)
    question, answer = MARKERS[lang]
    assert question in text(nb["cells"][0])
    results = [text(c) for c in nb["cells"] if c["cell_type"] == "markdown" and text(c).lstrip().startswith(RESULTS[lang])]
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
            assert not re.search(r";\s*\w", re.sub(r"(['\"]).*?\1", "", re.sub(r"#.*", "", text(cell))))


@pytest.mark.parametrize("lang,row", CASES)
def test_the_gate_has_no_finding_for_the_notebook(lang, row):
    assert findings_of(read(lang, row), lang, row) == []


@pytest.mark.parametrize("lang,row", CASES)
def test_no_notebook_computes_from_baked_results(lang, row):
    body = "\n".join(text(c) for c in read(lang, row)["cells"] if c["cell_type"] == "code")
    assert "data/derived" not in body
    assert "data/artifacts" not in body
    assert "data/examples/cases.json" in body        # the one input: the cases, read through the contract reader


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("row", LEVEL4)
def test_a_level_4_notebook_runs_the_baseline_and_the_claimed_method(lang, row):
    nb = read(lang, row)
    body = "\n".join(text(c) for c in nb["cells"] if c["cell_type"] == "code")
    for name in LEVEL4[row]:
        assert name in body, name
    claim = ROWS[row][1][0]
    assert nb["metadata"]["caos"]["beyond"] == [claim]
    section, shown = None, 0
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == BEYOND[lang]:
            shown += sum(1 for o in cell.get("outputs", []) if "image/png" in o.get("data", {}))
    assert shown >= 1


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("row", [r for r, v in ROWS.items() if v[0] == 3])
def test_a_level_3_notebook_runs_its_method_and_shows_a_figure_under_state_of_the_art(lang, row):
    nb = read(lang, row)
    name = LEVEL3[ROWS[row][2][0]]
    sota = {"en": "State of the art", "es": "Estado del arte"}[lang]
    section, calls, figures = None, 0, 0
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == sota:
            calls += text(cell).count(name + ".run(")
            figures += sum(1 for o in cell.get("outputs", []) if "image/png" in o.get("data", {}))
    assert calls >= 1 and figures >= 1


# ---- planted defects: each one breaks a rule of the bar in a copy, the gate must say so ----

LONG_LINE = "# " + "x" * 125


def plant_long_line(nb: dict) -> None:
    code = next(c for c in nb["cells"] if c["cell_type"] == "code")
    code["source"] = text(code) + "\n" + LONG_LINE


def plant_unprinted_answer(nb: dict) -> None:
    results = next(c for c in nb["cells"] if c["cell_type"] == "markdown" and text(c).lstrip().startswith("## Results"))
    head, _, tail = text(results).partition("**Answer:**")
    paragraph, sep, rest = tail.partition("\n\n")
    paragraph = re.sub(r"\d+[.,]\d+", "98765.4321", paragraph)
    results["source"] = head + "**Answer:**" + paragraph + sep + rest


def plant_no_figure_under_beyond(nb: dict) -> None:
    section = None
    for cell in nb["cells"]:
        if cell["cell_type"] == "markdown":
            for line in text(cell).splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
        elif section == BEYOND["en"]:
            cell["outputs"] = [o for o in cell.get("outputs", []) if o["output_type"] == "stream"]


def plant_copied_template_sentence(nb: dict) -> None:
    nb["cells"][1]["source"] = text(nb["cells"][1]) + "\n\nInterpret the method with its units.\n"


def plant_method_handed_over_as_a_callback(nb: dict) -> None:
    """Every call of a product method goes through a name the gate cannot follow: no method cell is left."""
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            cell["source"] = re.sub(r"\b(m\d\d_\w+|b\d_\w+)\.run\(", "(lambda f: f)(print).__call__(", text(cell))


PLANTS = [
    (plant_long_line, "characters", "05-optimization/01-the-cost-and-its-gradient"),
    (plant_unprinted_answer, "answer quotes no number", "05-optimization/02-the-wirtinger-gradient-and-adams-step"),
    (plant_no_figure_under_beyond, "Beyond the state of the art", "05-optimization/05-the-efficiency-uniformity-front"),
    (plant_copied_template_sentence, "generic filler sentence", "06-device-and-aberrations/01-what-the-device-costs"),
    (plant_method_handed_over_as_a_callback, "method cells", "07-feedback-and-dynamics/02-assigning-atoms-to-sites"),
]


@pytest.mark.parametrize("plant,expect,row", PLANTS, ids=[p[0].__name__ for p in PLANTS])
def test_the_gate_catches_each_planted_defect(plant, expect, row):
    nb = copy.deepcopy(read("en", row))
    assert findings_of(nb, "en", row) == []          # the control: the unbroken copy is clean
    plant(nb)
    found = findings_of(nb, "en", row)
    assert any(expect in f for f in found), found
