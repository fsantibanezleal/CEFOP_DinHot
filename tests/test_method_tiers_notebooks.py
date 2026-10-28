"""The three method tiers in the notebook gate (CAOS_MANAGE ``conventions/method-tiers-and-manuscripts.md``, template 0.13.000): a
notebook of level 3 names the sota methods of the SDD's method ladder that it runs (``caos.methods``) and every sota method has
one, in each language. Each test builds a small repository (``make_repo`` of tests/test_check_notebooks.py), gives its SDD a
ladder and runs the real check. The table itself is held by ``scripts/check_sdd.py`` (tests/test_method_tiers.py)."""
from __future__ import annotations

import json
from pathlib import Path

from test_check_notebooks import CHECK, make_repo

RULE = "method-tiers-and-manuscripts.md"

LADDER_NB = ("| id | tier | method | acceptance criterion | gate |\n|---|---|---|---|---|\n"
             "| M-1 | classical | the textbook model | reproduces the closed form | `x` |\n"
             "| M-2 | sota | the current solver | agrees with the reference | `x` |\n"
             "| M-3 | sota | a second current solver | agrees with the reference | `x` |\n")
LEVEL3 = "02-advanced/03-note.ipynb"


def with_ladder(root: Path, ladder: str = LADDER_NB) -> Path:
    sdd = root / "docs" / "design" / "SDD.md"
    text = sdd.read_text(encoding="utf-8")
    sdd.write_text(text.replace("## Oracles", f"## Method ladder\n\n{ladder}\n## Oracles"), encoding="utf-8")
    return root


def set_methods(root: Path, lang: str, rel: str, methods: list[str] | None) -> None:
    path = root / "notebooks" / lang / rel
    doc = json.loads(path.read_text(encoding="utf-8"))
    if methods is None:
        doc["metadata"]["caos"].pop("methods", None)
    else:
        doc["metadata"]["caos"]["methods"] = methods
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def covered_repo(tmp_path: Path, methods: list[str]) -> Path:
    root = with_ladder(make_repo(tmp_path / "repo"))
    for lang in ("en", "es"):
        set_methods(root, lang, LEVEL3, methods)
    return root


def finds(root: Path, *needles: str) -> bool:
    return any(all(n in f for n in needles) for f in CHECK.form_findings(root))


def test_every_sota_method_named_by_a_level_3_notebook_passes(tmp_path):
    assert CHECK.form_findings(covered_repo(tmp_path, ["M-2", "M-3"])) == []


def test_adversarial_a_sota_method_no_level_3_notebook_names_is_found_in_each_language(tmp_path):
    root = covered_repo(tmp_path, ["M-2"])
    assert finds(root, "notebooks/en", "tiers", "M-3", "no level 3 notebook", RULE)
    assert finds(root, "notebooks/es", "tiers", "M-3", "no level 3 notebook")
    assert not finds(root, "M-2", "no level 3 notebook")


def test_adversarial_a_level_3_notebook_that_names_no_method_is_found(tmp_path):
    root = covered_repo(tmp_path, ["M-2", "M-3"])
    set_methods(root, "en", LEVEL3, [])
    assert finds(root, "notebooks/en/" + LEVEL3, "caos.methods", "level 3")


def test_a_method_that_is_not_a_sota_row_of_the_ladder_is_found(tmp_path):
    root = covered_repo(tmp_path, ["M-2", "M-3", "M-1"])
    assert finds(root, LEVEL3, "M-1", "not a sota method")
    root2 = covered_repo(tmp_path / "x", ["M-2", "M-3", "M-9"])
    assert finds(root2, LEVEL3, "M-9", "not a sota method")


def test_methods_on_a_notebook_that_is_not_level_3_is_found(tmp_path):
    root = covered_repo(tmp_path, ["M-2", "M-3"])
    set_methods(root, "en", "02-advanced/02-note.ipynb", ["M-2"])
    assert finds(root, "02-advanced/02-note.ipynb", "caos.methods", "level 2")


def test_methods_must_be_a_list_of_strings(tmp_path):
    root = covered_repo(tmp_path, ["M-2", "M-3"])
    set_methods(root, "en", LEVEL3, "M-2")
    assert finds(root, LEVEL3, "caos.methods is not a list")


def test_adversarial_the_two_languages_name_the_same_methods(tmp_path):
    root = covered_repo(tmp_path, ["M-2", "M-3"])
    set_methods(root, "es", LEVEL3, ["M-3", "M-2"])
    assert finds(root, "notebooks/es/" + LEVEL3, "mirror", "caos.methods differs")


def test_a_ladder_without_sota_rows_needs_no_level_3_names(tmp_path):
    root = with_ladder(make_repo(tmp_path / "repo"), LADDER_NB.replace("sota", "classical"))
    assert CHECK.form_findings(root) == []


def test_a_repository_without_a_readable_ladder_is_left_to_the_sdd_gate(tmp_path):
    assert CHECK.form_findings(make_repo(tmp_path / "repo")) == []
