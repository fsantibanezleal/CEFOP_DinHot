"""Helpers of the notebook bar's planted-defect tests: the unit tests' builders (tests/test_check_notebooks.py) and a notebook built from steps.
A module of helpers, not a test module, so both adversarial folders import it."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from planting import ROOT


def unit_module():
    """The unit tests' builders (tests/test_check_notebooks.py), loaded once under a name of their own."""
    if "nb_gate_unit" not in sys.modules:
        spec = importlib.util.spec_from_file_location("nb_gate_unit", ROOT / "tests" / "test_check_notebooks.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["nb_gate_unit"] = module
        spec.loader.exec_module(module)
    return sys.modules["nb_gate_unit"]


def bar_notebook(lang: str, level: int, salt: str, steps: list[tuple[str, str, str]], *, figure: bool = False, answer: str | None = None,
                 prose: int = 900) -> dict:
    """A notebook with the sections of its level and the given Method steps (markdown, code, output text)."""
    u = unit_module()
    h = dict(zip(u.HEADINGS["en"], u.HEADINGS[lang]))
    q, a = ("**Question:**", "**Answer:**") if lang == "en" else ("**Pregunta:**", "**Respuesta:**")
    b = u.Builder(lang, level, salt)
    b.md(f"# T {salt}\n\n{q} {u.words(6, salt + 'q')}?")
    b.md(f"## {h['Objectives']}\n\n{u.words(40, salt + 'o')}.")
    b.md(f"## {h['Setup']}\n\nInstall with `pip install numpy==2.4.6`.")
    b.code(u.SETUP_CODE, "2.4.6\n")
    b.md(f"## {h['Data']}\n\nRead from the repository.")
    b.md(f"## {h['Method']}\n\n{u.words(prose, salt + 'p')}.")
    for text, code, out in steps:
        b.md(text)
        b.code(code, out)
    if figure:
        b.md("Draw.")
        b.code("# draw\nplt.plot([0, 1])\nplt.show()", "", figure=True)
        b.md(u.words(45, salt + "f") + ".")
    b.md(f"## {h['Results']}\n\n{a + ' ' + answer if answer else 'It is what it is.'}\n\n{u.words(30, salt + 'r')}.")
    b.md(f"## {h['Summary']}\n\n- {u.words(8, salt + 's')}.")
    b.md(f"## {h['References']}\n\n- {u.SOURCE}")
    return {"cells": b.cells, "nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"},
        "caos": {"language": lang, "topic": "01-t", "level": level, "title": "t", "packages": ["numpy==2.4.6"], "data": [],
                 "sources": [u.SOURCE], "beyond": []}}}


def floors_of(root: Path, doc: dict, lang: str = "en", others: tuple[dict, ...] = ()) -> list[str]:
    return unit_module().bar_of(root, doc, lang, others)
