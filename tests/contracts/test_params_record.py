"""Contract 1 (catalog row params-record): the records `validate_rows` accepts validate against
docs/contracts/schemas/params-record.schema.json, and the records the schema admits are accepted. The source tables
are the repository's own and the provider's (the swap)."""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
from typing import Any

import contract_schemas as cs
from pipeline.io.contract import DEFAULT_DAYS, RANGES, validate_rows

REPO_CSV = cs.ROOT / "data" / "examples" / "params.csv"
FIXTURE_CSV = cs.FIXTURE_ROOT / "data" / "examples" / "params.csv"
EXAMPLE = cs.CONTRACTS / "examples" / "params-record.json"
FIELDS = ("beta", "gamma", "N", "I0")


def rows_of(path: Path) -> list[dict[str, Any]]:
    assert path.is_file(), f"missing source table {path}"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_text(record: dict[str, Any]) -> dict[str, str]:
    """A record as a CSV cell dictionary: every value is text."""
    return {k: repr(v) if isinstance(v, float) else str(v) for k, v in record.items()}


def good_row(**over: Any) -> dict[str, str]:
    base = {"case_id": "probe", "beta": "0.5", "gamma": "0.25", "N": "1000", "I0": "10", "days": "10"}
    return {**base, **{k: str(v) for k, v in over.items()}}


def accepted(row: dict[str, str]) -> bool:
    return len(validate_rows([row]).accepted) == 1


def schema_admits(row: dict[str, str]) -> bool:
    """The schema's verdict on the typed record of a text row (the cross-field rule I0 <= N is stated in prose)."""
    rec = {"case_id": row["case_id"], **{k: float(row[k]) for k in FIELDS}, "days": int(row["days"])}
    return cs.errors("params-record", rec) == [] and rec["I0"] <= rec["N"]


def test_accepted_records_match_the_schema() -> None:
    report = validate_rows(rows_of(REPO_CSV))
    assert report.accepted, "the repository's example table has no accepted row"
    for p in report.accepted:
        assert cs.errors("params-record", asdict(p)) == [], p.case_id


def test_adversarial_schema_valid_records_are_accepted() -> None:
    schema = cs.load_json(cs.SCHEMAS / "params-record.schema.json")
    # the schema's bounds are the contract's RANGES
    for name in FIELDS:
        prop = schema["properties"][name]
        assert (prop["minimum"], prop["maximum"]) == RANGES[name][:2], name
    # the committed example, given as text as a CSV would, is accepted with equal values
    example = cs.load_json(EXAMPLE)
    assert cs.errors("params-record", example) == []
    report = validate_rows([as_text(example)])
    assert len(report.accepted) == 1 and asdict(report.accepted[0]) == example
    # each bound, one step inside and one step outside: the schema and validate_rows agree
    for name in FIELDS:
        lo, hi = RANGES[name][:2]
        for value, inside in ((lo, True), (hi, True), (lo / 2 if lo > 0 else -1.0, False), (hi * 2, False)):
            over: dict[str, Any] = {name: repr(float(value))}
            if name == "I0":
                over["N"] = "1e9" if value <= 1e9 else "1e12"  # keep I0 <= N so only the range decides
            row = good_row(**over)
            if name == "N":
                row["I0"] = "1" if value >= 1.0 else "0"
            assert accepted(row) == inside, f"{name}={value}: validate_rows"
            assert schema_admits(row) == inside, f"{name}={value}: schema"
    # an empty days becomes the default
    row = good_row(days="")
    report = validate_rows([row])
    assert report.accepted[0].days == DEFAULT_DAYS == 160
    assert cs.errors("params-record", asdict(report.accepted[0])) == []
    # I0 above N is rejected by the contract (the rule the schema states in prose)
    assert not accepted(good_row(N="100", I0="500"))


def test_swap_fixture_and_example_sources() -> None:
    for label, path in (("repository", REPO_CSV), ("fixture", FIXTURE_CSV)):
        rows = rows_of(path)
        report = validate_rows(rows)
        for p in report.accepted:
            assert cs.errors("params-record", asdict(p)) == [], f"{label} {p.case_id}"
    fixture = validate_rows(rows_of(FIXTURE_CSV))
    assert len(fixture.accepted) == len(rows_of(FIXTURE_CSV)) and not fixture.rejected
