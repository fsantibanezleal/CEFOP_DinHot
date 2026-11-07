"""Plants of the internal-names refinement of template 0.15.002 (the follow-up of #101): a string that is a key of one of the
product's committed documents, in the position of a key access, is an identifier of the data contract and passes; every string
a reader sees that names a method by its ladder id still fails, even when the same word is a data key somewhere.

Product-agnostic: each test plants a throwaway tree with its own SDD ladder and its own committed document and runs the real guard."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from planting import guard, make_tree

NAMES_INPUTS = ("scripts/check_internal_names.py", "scripts/check_notebook_depth.py", "scripts/check_notebooks.py")
SDD = ("# SDD\n\n## Method ladder\n\n| id | tier | method | acceptance criterion | gate |\n|---|---|---|---|---|\n"
       "| M-1 | classical | A method | It converges | `tests/test_a.py` |\n"
       "| B-lin | sota | Another method | It agrees | `tests/test_b.py` |\n"
       "| M0 | beyond | A third method | It holds | `tests/test_c.py` |\n")
NB = "notebooks/en/01-topic/01-lesson.ipynb"
PAGE = "frontend/src/pages/Page.tsx"
FIG = "manuscripts/report/figures/fig1.py"


def cell(kind: str, text: str, output: str = "") -> dict:
    c = {"cell_type": kind, "metadata": {}, "source": text}
    if kind == "code":
        c["outputs"] = [{"output_type": "stream", "name": "stdout", "text": output}] if output else []
        c["execution_count"] = None
    return c


def write_nb(repo: Path, cells: list[dict]) -> None:
    nb = {"cells": cells, "metadata": {"caos": {"title": "How the solver compares", "methods": []}}, "nbformat": 4, "nbformat_minor": 5}
    (repo / NB).write_text(json.dumps(nb), encoding="utf-8")


def put(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    repo = make_tree(tmp_path / "repo", *NAMES_INPUTS)
    put(repo, "docs/design/SDD.md", SDD)
    put(repo, "data/derived/hp500/loo.json",
        json.dumps({"schema": "x/v1", "kW": {"M0": 1.0, "B-lin": 2.0, "M-1": 3.0}, "M0_backbone": {"a": 1}}))
    (repo / NB).parent.mkdir(parents=True)
    write_nb(repo, [cell("markdown", "# How the solver compares\n\nThe Morrell power model."), cell("code", "x = 1")])
    put(repo, "README.md", "# Product\n\nThe Morrell model.\n")
    return repo


def run(repo: Path) -> subprocess.CompletedProcess:
    return guard(repo, "check_internal_names.py")


# ------------------------------------------------------------------------- key accesses to a committed document pass

def test_a_key_access_in_a_notebook_code_cell_passes(tree: Path) -> None:
    src = ("import json\nd = json.load(open('loo.json'))\nv = d['kW']['M0']\nw = d.get('kW', {})[\"B-lin\"]\n"
           "u = d.get(\"M0_backbone\")\nz = d['kW'].pop('M-1')\n")
    write_nb(tree, [cell("code", src)])
    r = run(tree)
    assert r.returncode == 0, r.stdout


def test_a_key_access_in_a_manuscript_figure_script_passes(tree: Path) -> None:
    put(tree, FIG, "import json\nd = json.load(open('loo.json'))\nv = d['kW']['M0']\n")
    r = run(tree)
    assert r.returncode == 0, r.stdout


def test_a_key_access_in_an_app_source_passes(tree: Path) -> None:
    put(tree, PAGE, "const v = doc['kW']['M0'];\nconst w = doc.kW?.[\"B-lin\"];\nconst u = map.get('M-1');\n")
    r = run(tree)
    assert r.returncode == 0, r.stdout


def test_a_key_of_a_schema_property_passes(tree: Path) -> None:
    (tree / "data/derived/hp500/loo.json").unlink()
    put(tree, "docs/contracts/schemas/loo.schema.json",
        json.dumps({"type": "object", "properties": {"M0": {"type": "number"}, "B-lin": {"type": "number"}}}))
    write_nb(tree, [cell("code", "v = d['M0'] + d['B-lin']\n")])
    r = run(tree)
    assert r.returncode == 0, r.stdout


# ------------------------------------------------------- every reader-facing string still fails, key or not

@pytest.mark.parametrize("surface", ["chart label", "markdown", "output", "axis label", "app label", "app jsx",
                                     "manuscript script label", "list of labels"])
def test_adversarial_a_label_that_equals_a_key_still_fails(tree: Path, surface: str) -> None:
    expect, word = NB, "M0"
    if surface == "chart label":
        write_nb(tree, [cell("code", "ax.plot(x, y, label='M0')")])
    elif surface == "markdown":
        write_nb(tree, [cell("markdown", "# How the solver compares\n\nM0 is the physics.")])
    elif surface == "output":
        write_nb(tree, [cell("code", "print(d['kW']['M0'])", "M0: 1.0\n")])
    elif surface == "axis label":
        write_nb(tree, [cell("code", "ax.set_xlabel('M0')\nax.legend(['B-lin'])")])
    elif surface == "app label":
        put(tree, PAGE, "export const label = 'M0';\nconst v = doc['kW']['M0'];\n")
        expect = PAGE
    elif surface == "app jsx":
        put(tree, PAGE, "export const A = () => <h2>M0</h2>;\n")
        expect = PAGE
    elif surface == "manuscript script label":
        put(tree, FIG, "plt.plot(x, y, label='B-lin')\nv = d['kW']['M0']\n")
        expect, word = FIG, "B-lin"
    else:
        write_nb(tree, [cell("code", "labels = ['M0', 'M-1']\nax.bar(range(2), vals, tick_label=labels)")])
    r = run(tree)
    assert r.returncode == 1 and expect in r.stdout and word in r.stdout, (surface, r.stdout)


def test_a_key_access_with_a_longer_string_is_not_a_data_key(tree: Path) -> None:
    write_nb(tree, [cell("code", "v = d['M0 is the physics']\nw = d['kW']['B-lin setting']")])
    r = run(tree)
    assert r.returncode == 1 and "M0" in r.stdout and "B-lin" in r.stdout, r.stdout


def test_a_string_that_is_no_key_of_any_document_is_not_exempt(tree: Path) -> None:
    write_nb(tree, [cell("code", "v = d['kW']['M-1']")])
    assert run(tree).returncode == 0
    put(tree, "data/derived/hp500/loo.json", json.dumps({"kW": {"B-lin": 1}}))
    r = run(tree)
    assert r.returncode == 1 and "M-1" in r.stdout, r.stdout


def test_a_product_without_committed_documents_behaves_as_before(tree: Path) -> None:
    (tree / "data/derived/hp500/loo.json").unlink()
    write_nb(tree, [cell("code", "v = d['kW']['M0']")])
    r = run(tree)
    assert r.returncode == 1 and "M0" in r.stdout, r.stdout


def test_a_malformed_committed_document_does_not_stop_the_guard(tree: Path) -> None:
    put(tree, "data/derived/hp500/broken.json", "{not json")
    write_nb(tree, [cell("code", "v = d['kW']['M0']")])
    assert run(tree).returncode == 0


def test_a_dict_or_object_literal_key_passes_and_its_value_is_still_read(tree: Path) -> None:
    write_nb(tree, [cell("code", "style = {'M0': ('red', 'o'), \"B-lin\": 1}\nv = {'M-1': d['kW']}\n")])
    put(tree, PAGE, "const names = { 'M0': 1, 'B-lin': 2 };\n")
    assert run(tree).returncode == 0
    write_nb(tree, [cell("code", "style = {'M0': 'M0 backbone'}\n")])
    r = run(tree)
    assert r.returncode == 1 and "M0" in r.stdout and NB in r.stdout and PAGE not in r.stdout, r.stdout
    write_nb(tree, [cell("code", "x = 1")])
    put(tree, PAGE, "const names = { en: 'M0', es: 'M0' };\nconst t = ok ? 'M0' : 'x';\n")
    r = run(tree)
    assert r.returncode == 1 and PAGE in r.stdout, r.stdout
