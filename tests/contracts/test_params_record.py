"""Contract 1 (catalog row params-record): the records `validate_records` accepts validate against
docs/contracts/schemas/params-record.schema.json, and the records the schema admits are accepted. The source documents are the
repository's own (data/examples/cases.json) and the provider's (the swap). The run-time validator is the standard-library
`jsonschema_lite`; here it is held to `jsonschema`, which reads the same schema file."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import contract_schemas as cs

sys.path.insert(0, str(cs.ROOT / "tests" / "bake"))

import bakefix  # noqa: E402

from pipeline import registry  # noqa: E402
from pipeline.io import jsonschema_lite  # noqa: E402
from pipeline.io.contract import load_schema, read_cases, validate_records  # noqa: E402

REPO_CASES = cs.ROOT / "data" / "examples" / "cases.json"
FIXTURE_CASES = cs.FIXTURE_ROOT / "data" / "examples" / "cases.json"
EXAMPLE = cs.CONTRACTS / "examples" / "params-record.json"


def test_accepted_records_match_the_schema():
    report = validate_records(read_cases(REPO_CASES))
    assert len(report.accepted) == 12, report.summary()
    for rec in report.accepted:
        assert cs.errors("params-record", rec) == [], rec["case_id"]
    assert [r["case_id"] for r in report.rejected] == ["C11_outside_field"]


def test_c11_is_rejected_with_the_field_bounds():
    report = validate_records(read_cases(REPO_CASES))
    c11 = next(r for r in report.rejected if r["case_id"] == "C11_outside_field")
    assert c11["code"] == "out_of_field" and "127.5" in c11["reason"] and c11["bound_um"] == 127.5
    assert "127.5" in c11["reason_es"]
    # the schema alone admits C11: only the cross-field rule refuses it
    raw = next(r for r in read_cases(REPO_CASES) if r["case_id"] == "C11_outside_field")
    assert cs.errors("params-record", raw) == []


def test_source_document_is_the_registry_default():
    assert read_cases(REPO_CASES) == registry.records(), "run: python data-pipeline/run.py cases"


def test_adversarial_schema_valid_records_are_accepted():
    # the committed example and every boundary of the schema's numeric ranges are accepted by contract 1
    example = cs.load_json(EXAMPLE)
    assert cs.errors("params-record", example) == []
    assert validate_records([example]).ok or validate_records([example]).rejected[0]["code"] != "schema"
    base = bakefix.record(feedback=None, dynamics=None)
    for path, value in ((("setup", "wavelength_nm"), 300), (("setup", "wavelength_nm"), 2000), (("setup", "pad"), 1),
                        (("setup", "pad"), 4), (("seed",), 0), (("seed",), 2147483647), (("budget", "iterations"), 1),
                        (("budget", "iterations"), 5000), (("budget", "time_s"), 0.01), (("setup", "pitch_um"), 50)):
        rec = copy.deepcopy(base)
        node = rec
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        assert cs.errors("params-record", rec) == [], (path, value)
        report = validate_records([rec])
        # a schema-valid record is never refused by the schema step (a cross-field rule may still apply, e.g. the field of view)
        assert not report.rejected or report.rejected[0]["code"] != "schema", (path, value, report.rejected)


def test_adversarial_rejections_carry_their_reason():
    base = bakefix.record(feedback=None, dynamics=None)
    mutations = [(("setup", "wavelength_nm"), 299), (("setup", "wavelength_nm"), 2001), (("setup", "pad"), 5),
                 (("setup", "n_pix"), 96), (("budget", "iterations"), 5001), (("seed",), 2147483648),
                 (("setup", "beam", "waist_frac"), 0.05), (("setup", "pitch_um"), 0.5), (("case_id",), "bad id")]
    for path, value in mutations:
        rec = copy.deepcopy(base)
        node = rec
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        assert cs.errors("params-record", rec), (path, value)
        report = validate_records([rec])
        assert not report.accepted and report.rejected[0]["code"] == "schema", (path, value)
        assert path[-1] in report.rejected[0]["reason"], report.rejected[0]["reason"]


def test_lite_validator_agrees_with_jsonschema_on_mutations():
    schema = load_schema()
    base = bakefix.record()
    samples = [base, bakefix.shaped_record(), bakefix.rearr_record(), copy.deepcopy(base)]
    samples[3]["target"]["traps"][0]["charge"] = 99
    for key in list(base):
        broken = {k: v for k, v in base.items() if k != key}
        samples.append(broken)
    samples.append({**base, "setup": {**base["setup"], "beam": {"kind": "flat", "waist_frac": 1.0}}})
    samples.append({**base, "dynamics": {**base["dynamics"], "particle": "atom"}})
    samples.append({**base, "feedback": {"gain": 2.0, "steps": 3, "camera": base["feedback"]["camera"]}})
    samples.append({**base, "methods": ["M02", "M02"]})
    samples.append({**base, "expect": {"efficiency": [0.1]}})
    for s in samples:
        lite = bool(jsonschema_lite.errors(schema, s))
        full = bool(cs.errors("params-record", s))
        assert lite == full, (lite, full, jsonschema_lite.errors(schema, s)[:2], cs.errors("params-record", s)[:2])


def test_lite_validator_refuses_unknown_keywords():
    import pytest

    with pytest.raises(ValueError, match="not supported"):
        jsonschema_lite.errors({"type": "object", "dependentRequired": {"a": ["b"]}}, {})


def test_swap_fixture_and_example_sources():
    for label, path in (("repository", REPO_CASES), ("fixture", FIXTURE_CASES)):
        rows = read_cases(path)
        report = validate_records(rows)
        for rec in report.accepted:
            assert cs.errors("params-record", rec) == [], f"{label} {rec['case_id']}"
        assert len(report.accepted) + len(report.rejected) == len(rows), label
    fixture = validate_records(read_cases(FIXTURE_CASES))
    assert [r["case_id"] for r in fixture.accepted] == ["C01_fixture"]
    assert fixture.rejected[0]["case_id"] == "C11_fixture" and fixture.rejected[0]["code"] == "out_of_field"
    assert Path(REPO_CASES).is_file()
