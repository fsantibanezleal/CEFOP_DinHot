"""The case registry, cases grouped by CATEGORY. The App shows ONE selected case; Experiments/Benchmark show
cross-case summaries by category."""
from __future__ import annotations

from .cases.example_case import CASES, DEFAULT_CASE, Case

_BY_ID: dict[str, Case] = {c.id: c for c in CASES}


def list_cases() -> list[Case]:
    return list(CASES)


def get_case(case_id: str) -> Case:
    if case_id not in _BY_ID:
        raise KeyError(f"unknown case: {case_id!r}. known: {sorted(_BY_ID)}")
    return _BY_ID[case_id]


def default_case() -> str:
    return DEFAULT_CASE


def list_categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in CASES:
        out.setdefault(c.category["en"], []).append(c.id)
    return out
