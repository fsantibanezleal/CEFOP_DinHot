"""The case registry, cases grouped by CATEGORY (the four of the SDD). The App shows ONE selected case; the Benchmark views
show cross-case summaries by category.

The registry owns the reader-facing metadata of the fourteen cases (titles, categories, bands, anchors) and their default
records (``cases/library.py``). The records the bake runs are read from ``data/examples/cases.json`` through contract 1
(``stages/preprocess.py``); a record whose id the registry does not know gets generic metadata, so a reader's own case
bakes like the twelve.
"""
from __future__ import annotations

import copy

from .cases.library import CASES, DEFAULT_CASE, Case

_BY_ID: dict[str, Case] = {c.id: c for c in CASES}

CUSTOM_CATEGORY = {"en": "Custom", "es": "Propios"}


def list_cases() -> list[Case]:
    return list(CASES)


def get_case(case_id: str) -> Case:
    if case_id not in _BY_ID:
        raise KeyError(f"unknown case: {case_id!r}. known: {sorted(_BY_ID)}")
    return _BY_ID[case_id]


def default_case() -> str:
    return DEFAULT_CASE


def records() -> list[dict]:
    """The default params records of the fourteen cases, as ``data/examples/cases.json`` holds them."""
    return [copy.deepcopy(c.record) for c in CASES]


def case_for(record: dict) -> Case:
    """The metadata of a record: the registry's when its id is known, else generic (title = the id)."""
    cid = record["case_id"]
    if cid in _BY_ID:
        known = _BY_ID[cid]
        return Case(known.id, known.title, known.category, record, known.expected_band, known.real_or_synthetic,
                    known.anchor, known.expect_basis)
    text = {"en": cid, "es": cid}
    band = {"en": "A case supplied by the reader; the ranges of its expect field are what the bake checks.",
            "es": "Un caso aportado por el lector; los rangos de su campo expect son lo que revisa la generación."}
    return Case(cid, text, CUSTOM_CATEGORY, record, band, "synthetic",
                {"source": {"en": "none (a case supplied by the reader)", "es": "ninguna (un caso aportado por el lector)"},
                 "url": None}, "provisional")


def list_categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in CASES:
        out.setdefault(c.category["en"], []).append(c.id)
    return out
