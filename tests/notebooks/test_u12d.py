"""Row tests of the notebooks of unit U12d (topics 04 and 08: the level 1 and level 2 notebooks, English and Spanish) and planted defects.

The rows pin what the unit promised: four new notebooks per language (04-01 and 04-02, 08-01 and 08-02), the four earlier notebooks of
those topics renumbered to 03 and 04 with their content and their methods, the same paths in both trees, the question and the answer, levels
that never decrease inside a topic, and the product calls each lesson has to make. The plants copy a committed notebook in memory, break one
rule of the bar (a long line, an answer that quotes no printed number, a copied template sentence, a method handed over as a callback, a
figure with no prose after it) and expect the gate of ``scripts/check_notebooks.py`` to say so; the unbroken notebook is the control.
Nothing here executes a notebook: the runner does that (``scripts/run_notebooks.py``).
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
NEW_ROWS = {
    "04-shaped-potentials/01-what-a-shaped-potential-asks": (1, [], []),
    "04-shaped-potentials/02-the-signal-and-the-noise-region": (2, [], []),
    "08-learned-holography/01-what-a-network-sees-of-a-hologram": (1, [], []),
    "08-learned-holography/02-training-without-labels": (2, [], []),
}
# the four notebooks that existed before this unit, now numbered after the new ones
RENUMBERED = {
    "04-shaped-potentials/03-mraf-and-the-signal-region": (3, [], ["M08"]),
    "04-shaped-potentials/04-optimal-transport-start": (3, [], ["M18"]),
    "08-learned-holography/03-a-network-start-for-volume-holograms": (3, [], ["M17"]),
    "08-learned-holography/04-is-a-learned-warm-start-worth-it": (4, ["BS-3"], []),
}
OLD_PATHS = (
    "04-shaped-potentials/01-mraf-and-the-signal-region",
    "04-shaped-potentials/02-optimal-transport-start",
    "08-learned-holography/01-a-network-start-for-volume-holograms",
    "08-learned-holography/02-is-a-learned-warm-start-worth-it",
)
ROWS = {**NEW_ROWS, **RENUMBERED}
# the product calls each new notebook must make, by the text of its code cells
CALLS = {
    "04-shaped-potentials/01-what-a-shaped-potential-asks": ("m04_gs.run(", "fft_focal_field(", "square_grid("),
    "04-shaped-potentials/02-the-signal-and-the-noise-region": ("m04_gs.run(", "m08_mraf.run(", "from_field("),
    "08-learned-holography/01-what-a-network-sees-of-a-hologram": ("m17_cgh_net.predict(", "InferenceSession(", "lens_phase("),
    "08-learned-holography/02-training-without-labels": ("fft_focal_field(", "m04_gs.run(", "point_trap_fields(", "sha256("),
}
MARKERS = {"en": ("**Question:**", "**Answer:**"), "es": ("**Pregunta:**", "**Respuesta:**")}
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


def code_of(nb: dict) -> str:
    return "\n".join(text(c) for c in nb["cells"] if c["cell_type"] == "code")


def findings_of(nb: dict, lang: str, row: str) -> list[str]:
    reading = GATE.Reading(nb, lang, ROOT, BAR)
    return GATE.reading_findings(f"notebooks/{lang}/{row}.ipynb", reading, BAR)


CASES = [(lang, row) for lang in LANGS for row in ROWS]
NEW_CASES = [(lang, row) for lang in LANGS for row in NEW_ROWS]


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


def test_the_two_trees_hold_the_same_paths_and_the_old_paths_are_gone():
    for row in ROWS:
        assert path_of("en", row).is_file(), row
        assert path_of("es", row).is_file(), row
    for row in OLD_PATHS:
        assert not path_of("en", row).exists(), row
        assert not path_of("es", row).exists(), row


def test_the_two_topics_are_numbered_without_a_gap_and_the_levels_never_decrease():
    for topic, levels in (("04-shaped-potentials", [1, 2, 3, 3]), ("08-learned-holography", [1, 2, 3, 4])):
        for lang in LANGS:
            files = sorted((ROOT / "notebooks" / lang / topic).glob("*.ipynb"))
            assert [f.name[:2] for f in files] == ["01", "02", "03", "04"]
            found = [json.loads(f.read_text(encoding="utf-8"))["metadata"]["caos"]["level"] for f in files]
            assert found == levels


@pytest.mark.parametrize("row", RENUMBERED)
def test_a_renumbered_notebook_keeps_its_method_and_its_content(row):
    en = read("en", row)
    body = code_of(en)
    marker = {"M08": "m08_mraf.run(", "M18": "m18_ot_mraf.run(", "M17": "m17_cgh_net.run(", "BS-3": "slmsuite"}
    key = (ROWS[row][2] or ROWS[row][1])[0]
    assert marker[key] in body, key


@pytest.mark.parametrize("lang", LANGS)
def test_the_prerequisites_of_the_renumbered_notebooks_name_the_new_numbers(lang):
    first = text(read(lang, "04-shaped-potentials/04-optimal-transport-start")["cells"][0])
    assert "03" in first
    first = text(read(lang, "08-learned-holography/04-is-a-learned-warm-start-worth-it")["cells"][0])
    assert "01" in first and "03" in first


@pytest.mark.parametrize("row", NEW_ROWS)
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


@pytest.mark.parametrize("lang,row", NEW_CASES)
def test_every_code_cell_ran_clean(lang, row):
    nb = read(lang, row)
    count = 0
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        count += 1
        assert cell["execution_count"] == count
        assert all(o["output_type"] != "error" and o.get("name") != "stderr" for o in cell.get("outputs", []))


@pytest.mark.parametrize("lang,row", NEW_CASES)
def test_no_code_line_is_too_long_and_no_statements_are_doubled(lang, row):
    nb = read(lang, row)
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert max(len(line) for line in text(cell).splitlines()) <= BAR["floors"]["line_chars_max"]
            assert not re.search(r";\s*\w", re.sub(r"(['\"]).*?\1", "", re.sub(r"#.*", "", text(cell))))


@pytest.mark.parametrize("lang,row", CASES)
def test_the_gate_has_no_finding_for_the_notebook(lang, row):
    assert findings_of(read(lang, row), lang, row) == []


@pytest.mark.parametrize("lang,row", NEW_CASES)
def test_the_notebook_runs_the_product_and_does_not_compute_from_baked_results(lang, row):
    body = code_of(read(lang, row))
    for call in CALLS[row]:
        assert call in body, call
    if row.startswith("04-"):
        assert '"derived"' not in body and "data/derived" not in body
        assert '"artifacts"' not in body and "data/artifacts" not in body
        assert '"examples"' in body and '"cases.json"' in body      # the one input: the cases, through the contract reader
    else:
        # topic 08 reads the released graph and the committed evidence of its training; the lesson is computed from the graph
        assert "cgh-net.onnx" in body


@pytest.mark.parametrize("lang", LANGS)
def test_the_evidence_notebook_reads_the_record_and_counts_one_reproduction_check(lang):
    body = code_of(read(lang, "08-learned-holography/02-training-without-labels"))
    assert "evaluation-detail.json" in body and "cgh-net-training.json" in body
    assert body.count("sha256(") == 1                      # the one reproduction check of the notebook
    assert body.count("hexdigest()") == 1


@pytest.mark.parametrize("lang,row", NEW_CASES)
def test_a_notebook_of_levels_1_and_2_has_the_figures_and_a_reading_after_each(lang, row):
    nb = read(lang, row)
    need = BAR["floors"]["figures_min"] if "figures_min" in BAR["floors"] else 1
    assert need >= 1
    figures = 0
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code" and any("image/png" in o.get("data", {}) for o in cell.get("outputs", [])):
            figures += 1
            assert nb["cells"][i + 1]["cell_type"] == "markdown"
            assert len(text(nb["cells"][i + 1]).split()) >= 40
    assert figures >= (2 if NEW_ROWS[row][0] == 2 else 1)


# ---- planted defects: each one breaks a rule of the bar in a copy, the gate must say so ----

LONG_LINE = "# " + "x" * 125


def plant_long_line(nb: dict) -> None:
    code = next(c for c in nb["cells"] if c["cell_type"] == "code")
    code["source"] = text(code) + "\n" + LONG_LINE


def plant_unprinted_answer(nb: dict) -> None:
    results = next(c for c in nb["cells"] if c["cell_type"] == "markdown" and text(c).lstrip().startswith("## Results"))
    head, _, tail = text(results).partition("**Answer:**")
    paragraph, sep, rest = tail.partition("\n\n")
    paragraph = re.sub(r"\d+(?:[.,]\d+)?(?:e-\d+)?", "98765.4321", paragraph)    # every number, whole ones too: the answer quotes none
    results["source"] = head + "**Answer:**" + paragraph + sep + rest


def plant_copied_template_sentence(nb: dict) -> None:
    nb["cells"][1]["source"] = text(nb["cells"][1]) + "\n\nInterpret the method with its units.\n"


def plant_method_handed_over_as_a_callback(nb: dict) -> None:
    """Every call of a product method goes through a name the gate cannot follow: no method cell is left."""
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            body = re.sub(r"\b(m\d\d_\w+|b\d_\w+)\.\w+\(", "(lambda f: f)(print).__call__(", text(cell))
            body = re.sub(r"\b(forward|modes|traps|metrics|evaluation)\.\w+\(", "(lambda f: f)(print).__call__(", body)
            cell["source"] = body


def plant_figure_without_a_reading(nb: dict) -> None:
    """The prose after the first figure is cut to a few words."""
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] == "code" and any("image/png" in o.get("data", {}) for o in cell.get("outputs", [])):
            nb["cells"][i + 1]["source"] = "A figure."
            return


PLANTS = [
    (plant_long_line, "characters", "04-shaped-potentials/01-what-a-shaped-potential-asks"),
    (plant_unprinted_answer, "answer quotes no number", "04-shaped-potentials/02-the-signal-and-the-noise-region"),
    (plant_copied_template_sentence, "generic filler sentence", "08-learned-holography/01-what-a-network-sees-of-a-hologram"),
    (plant_method_handed_over_as_a_callback, "method cells", "08-learned-holography/02-training-without-labels"),
    (plant_figure_without_a_reading, "figure", "04-shaped-potentials/01-what-a-shaped-potential-asks"),
]


@pytest.mark.parametrize("plant,expect,row", PLANTS, ids=[p[0].__name__ for p in PLANTS])
def test_the_gate_catches_each_planted_defect(plant, expect, row):
    nb = copy.deepcopy(read("en", row))
    assert findings_of(nb, "en", row) == []          # the control: the unbroken copy is clean
    plant(nb)
    found = findings_of(nb, "en", row)
    assert any(expect in f for f in found), found
