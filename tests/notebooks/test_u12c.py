"""Row tests of the unit U12c notebooks (topic 08-learned-holography, both languages).

The notebooks are executed by ``scripts/run_notebooks.py`` and held to the bar by ``scripts/check_notebooks.py``; these tests hold what
those gates leave to the writer: the mirror of the two trees, the metadata the method tiers need, the claim of each Answer against the
outputs and against the committed record it reads, and a planted defect for the Answer check. They read the committed notebooks and
need no kernel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOPIC = "08-learned-holography"
NOTEBOOKS = ("03-a-network-start-for-volume-holograms", "04-is-a-learned-warm-start-worth-it")
ANSWER = {"en": "**Answer:**", "es": "**Respuesta:**"}
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def load(lang: str, name: str) -> dict:
    path = ROOT / "notebooks" / lang / TOPIC / f"{name}.ipynb"
    return json.loads(path.read_text(encoding="utf-8"))


def source(cell: dict) -> str:
    return "".join(cell["source"])


def output_text(nb: dict) -> str:
    parts: list[str] = []
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream":
                parts.append("".join(out["text"]))
    return "\n".join(parts)


def figures(nb: dict) -> int:
    return sum(1 for c in nb["cells"] for o in c.get("outputs", []) if "image/png" in o.get("data", {}))


def answer_numbers(nb: dict, lang: str) -> list[str]:
    for cell in nb["cells"]:
        text = source(cell)
        if cell["cell_type"] == "markdown" and ANSWER[lang] in text:
            paragraph = re.split(r"\n\s*\n", text[text.index(ANSWER[lang]):], maxsplit=1)[0]
            return [n.replace(",", ".") for n in NUMBER.findall(paragraph)]
    raise AssertionError("no Answer in the notebook")


def answer_is_backed(nb: dict, lang: str, numbers: list[str] | None = None) -> bool:
    """True when at least one number of the Answer, written as the Answer writes it, appears in a printed output."""
    printed = {n.replace(",", ".") for n in NUMBER.findall(output_text(nb))}
    return any(n in printed for n in (numbers if numbers is not None else answer_numbers(nb, lang)) if "." in n)


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_the_two_trees_mirror_each_other(name):
    en, es = load("en", name), load("es", name)
    assert [c["cell_type"] for c in en["cells"]] == [c["cell_type"] for c in es["cells"]]
    assert figures(en) == figures(es) >= 2
    assert {k: v for k, v in en["metadata"]["caos"].items() if k not in ("language", "title")} == \
        {k: v for k, v in es["metadata"]["caos"].items() if k not in ("language", "title")}
    # the same computation: the code cells differ only in comments and printed words, so their call names agree
    calls = lambda nb: [re.findall(r"\b[a-z_0-9]+\.[a-z_0-9]+\(", source(c)) for c in nb["cells"] if c["cell_type"] == "code"]  # noqa: E731
    assert calls(en) == calls(es)


def test_the_tier_metadata_names_the_methods_and_the_claim():
    for lang in ("en", "es"):
        first, second = load(lang, NOTEBOOKS[0])["metadata"]["caos"], load(lang, NOTEBOOKS[1])["metadata"]["caos"]
        assert (first["level"], first["methods"], first["beyond"]) == (3, ["M17"], [])
        assert (second["level"], second["beyond"]) == (4, ["BS-3"]) and "methods" not in second
        assert first["topic"] == second["topic"] == TOPIC and first["language"] == second["language"] == lang


@pytest.mark.parametrize("lang", ("en", "es"))
@pytest.mark.parametrize("name", NOTEBOOKS)
def test_the_notebook_is_clean_and_deterministic(lang, name):
    nb = load(lang, name)
    counts = [c["execution_count"] for c in nb["cells"] if c["cell_type"] == "code"]
    assert counts == list(range(1, len(counts) + 1))
    text = output_text(nb) + "".join(source(c) for c in nb["cells"])
    assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]|/Users/|/home/", text), "a machine path"
    assert not any(o.get("output_type") in ("error",) or o.get("name") == "stderr" for c in nb["cells"] for o in c.get("outputs", []))
    # a wall-clock figure in an output would make the committed bytes differ from a fresh run
    assert not re.search(r"\b\d+(\.\d+)?\s?(ms|s|seconds|segundos)\b", output_text(nb))


@pytest.mark.parametrize("lang", ("en", "es"))
@pytest.mark.parametrize("name", NOTEBOOKS)
def test_the_answer_quotes_a_number_the_notebook_printed(lang, name):
    assert answer_is_backed(load(lang, name), lang)


def test_a_planted_answer_with_numbers_nobody_printed_is_refused():
    nb = load("en", NOTEBOOKS[0])
    assert answer_is_backed(nb, "en", ["0.7452"])
    assert not answer_is_backed(nb, "en", ["0.1234", "9.876"])


def test_the_learned_start_notebook_quotes_the_committed_record():
    record = json.loads((ROOT / "data" / "derived" / "models" / "warmstart-model-rejected.json").read_text(encoding="utf-8"))
    iterations = record["metrics"]["iterations_to_1pct"]
    assert (iterations["model"]["median"], iterations["random"]["median"]) == (8.0, 14.0)
    assert record["ratio_random_over_model_median_iterations"] == 1.75
    nb = load("en", NOTEBOOKS[1])
    printed = output_text(nb)
    assert "median 8.0 iterations" in printed and "median 14.0 iterations" in printed and "1.75" in printed
    control = record["control_without_the_network"]["median_and_q3_iterations"]
    assert control["model_nfix3"][0] > control["random_nfix3"][0]   # the network did no better than the control it was credited over
    assert "random_nfix3" in printed and "model_nfix3" in printed
