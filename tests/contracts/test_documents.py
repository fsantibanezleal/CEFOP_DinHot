"""Producer-side tests of the document contracts (catalog rows case-index, case-manifest, trace, benchmark-results,
model-metrics): every document of a fresh sandbox bake, of the committed bake (when it exists) and of the provider tree
validates against its schema file (docs/contracts/schemas/) and obeys the rules a schema cannot state. The consumer and
swap side is frontend/src/lib/contract.test.ts, which runs the same assertions on the same roots. The model-slot and
engine-reference tests (model cards, ONNX graphs, engine reference) belong to the units that produce those documents.

The sandbox bake runs the small cases of tests/bake/bakefix.py with the planted methods; the canonical bake is the same
code on the twelve cases."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path

import contract_schemas as cs
import pytest

FIXTURE = cs.DERIVED_ROOTS["fixture"]
COMMITTED = cs.DERIVED_ROOTS["bake"]
TRACE_BYTES_GATE = 256 * 1024


def roots(sandbox_bake) -> dict[str, Path]:
    out = {"fixture": FIXTURE, "sandbox": sandbox_bake[0]}
    if (COMMITTED / "manifests" / "index.json").is_file():
        out["committed"] = COMMITTED
    return out


def index_of(root: Path) -> dict:
    return cs.load_json(root / "manifests" / "index.json")


def baked(root: Path):
    """(entry, manifest, trace) of every baked case under ``root``."""
    for e in index_of(root)["cases"]:
        if e["status"] == "baked":
            m = cs.load_json(root / e["path"])
            yield e, m, cs.load_json(root / m["artifact"]["path"])


def test_index_validates(sandbox_bake):
    for label, root in roots(sandbox_bake).items():
        index = index_of(root)
        assert cs.errors("case-index", index) == [], label
        ids = [e["case_id"] for e in index["cases"]]
        assert ids == sorted(ids), f"{label}: entries not sorted by case_id"
        by_id = {e["case_id"]: e for e in index["cases"]}
        assert by_id[index["default_case"]]["status"] == "baked", f"{label}: the default case must be baked"


def test_refused_case_has_no_manifest(sandbox_bake):
    for label, root in roots(sandbox_bake).items():
        refused = [e for e in index_of(root)["cases"] if e["status"] == "refused"]
        assert refused, f"{label}: the root exercises no refused case"
        for e in refused:
            assert e["path"] is None and e["reason"]["en"] and e["reason"]["es"], (label, e["case_id"])
            assert not (root / "manifests" / f"{e['case_id']}.json").exists(), (label, e["case_id"])
            assert not (root / e["case_id"]).exists(), (label, e["case_id"])
    far = next(e for e in index_of(sandbox_bake[0])["cases"] if e["case_id"] == "C94_far")
    assert "below 127" in far["reason"]["en"] or "below" in far["reason"]["en"]   # the field bound is in the reason


def test_adversarial_baked_entry_with_a_reason_or_refused_with_a_path_fails_the_schema(sandbox_bake):
    index = index_of(sandbox_bake[0])
    bad = copy.deepcopy(index)
    next(e for e in bad["cases"] if e["status"] == "baked")["reason"] = {"en": "x", "es": "x"}
    assert cs.errors("case-index", bad)
    bad = copy.deepcopy(index)
    next(e for e in bad["cases"] if e["status"] == "refused")["path"] = "manifests/C94_far.json"
    assert cs.errors("case-index", bad)


def test_manifests_validate(sandbox_bake):
    for label, root in roots(sandbox_bake).items():
        for e, m, _t in baked(root):
            assert cs.errors("case-manifest", m) == [], (label, e["case_id"])
            assert m["case_id"] == e["case_id"]
            assert m["lane"] == m["gate"]["lane"], (label, e["case_id"], "lane differs from gate.lane")
            assert sorted(m["methods"]) == sorted(m["params"]["methods"]), (label, e["case_id"])
            assert m["params"]["reference_method"] in m["methods"], (label, e["case_id"])
            assert m["params"]["expect"] == m["expect"], (label, e["case_id"])
            size = (root / m["artifact"]["path"]).stat().st_size
            assert size == m["artifact"]["bytes"] == m["gate"]["trace_bytes"], (label, e["case_id"])
            assert size <= m["gate"]["trace_bytes_budget"] == TRACE_BYTES_GATE


def test_adversarial_a_manifest_with_wall_clock_time_or_an_unknown_field_fails(sandbox_bake):
    _e, m, _t = next(baked(sandbox_bake[0]))
    for plant in ({"baked_at": "2026-10-28T00:00:00Z"}, {"run_ms": 12.5}):
        assert cs.errors("case-manifest", {**m, **plant}), plant
    keys = {k for k in json.dumps(m).replace('"', " ").replace(":", " ").replace(",", " ").split()}
    assert not keys & {"run_ms", "baked_at", "timestamp", "seconds"}


def test_traces_validate(sandbox_bake):
    for label, root in roots(sandbox_bake).items():
        for e, m, t in baked(root):
            assert cs.errors("trace", t) == [], (label, e["case_id"])
            assert t["case_id"] == e["case_id"]
            assert t["reference"]["method"] in t["methods"], (label, e["case_id"])
            assert sorted(t["methods"]) == sorted(m["methods"]), (label, e["case_id"])
            assert t["summary"]["best_method"] in t["methods"]
            for mid, row in t["methods"].items():
                assert len(row["history"]) <= 200
                its = [h["iteration"] for h in row["history"]]
                assert its == sorted(its), (label, e["case_id"], mid)
                if t["traps"]:
                    assert len(row["trap_intensity"]) == len(t["traps"]), (label, e["case_id"], mid)


def test_trace_base64_fields_have_their_sizes(sandbox_bake):
    for label, root in roots(sandbox_bake).items():
        for e, _m, t in baked(root):
            ref = t["reference"]
            assert len(base64.b64decode(ref["phase_u8"], validate=True)) == t["grid"]["n_pix"] ** 2, (label, e["case_id"])
            f = ref["focal"]
            assert len(base64.b64decode(f["intensity_db_u8"], validate=True)) == f["size"] ** 2, (label, e["case_id"])
            if ref["axial"] is not None:
                a = ref["axial"]
                assert len(base64.b64decode(a["xz_u8"], validate=True)) == a["nz"] * a["nx"], (label, e["case_id"])
            assert (root / e["path"]).exists()


def test_trace_dynamics_and_rearrangement_limits(sandbox_bake):
    seen = set()
    for _label, root in roots(sandbox_bake).items():
        for _e, _m, t in baked(root):
            if t["dynamics"]:
                seen.add("dynamics")
                d = t["dynamics"]
                assert len(d["x_um"]) == len(d["y_um"]) <= 4000 and len(d["psd"]["f_hz"]) == len(d["psd"]["p"]) <= 200
            if t["rearrangement"]:
                seen.add("rearrangement")
                assert len(t["rearrangement"]["frames"]) <= 120
            if t["feedback"]:
                seen.add("feedback")
    assert seen == {"dynamics", "rearrangement", "feedback"}


def test_benchmark_validates():
    for label, root in {"fixture": FIXTURE, "committed": COMMITTED}.items():
        path = root / "benchmark" / "results.json"
        if not path.is_file():
            assert label == "committed"
            continue
        doc = cs.load_json(path)
        assert cs.errors("benchmark-results", doc) == [], label
        for r in doc["rows"]:
            assert r["params"] in ("default", "tuned") and r["n_seeds"] >= 1


def test_skipped_cells_are_absent_from_rows():
    for label, root in {"fixture": FIXTURE, "committed": COMMITTED}.items():
        path = root / "benchmark" / "results.json"
        if not path.is_file():
            continue
        doc = cs.load_json(path)
        rows = {(r["method"], r["geometry"], r["device"]) for r in doc["rows"]}
        for s in doc.get("skipped", []):
            assert s["reason"]["en"] and s["reason"]["es"], label
            if "Device cell" in s["reason"]["en"]:
                assert (s["method"], s["geometry"], "device") not in rows, (label, s)
            else:
                assert (s["method"], s["geometry"], "ideal") not in rows, (label, s)


def test_model_metrics_validate():
    for label, root in {"fixture": FIXTURE, "committed": COMMITTED}.items():
        path = root / "models" / "metrics.json"
        if not path.is_file():
            assert label == "committed"
            continue
        doc = cs.load_json(path)
        assert cs.errors("model-metrics", doc) == [], label


def test_fixture_tree_validates(sandbox_bake):
    """The swap test: the same assertions pass on the provider tree and on a bake (documents and cross-field rules)."""
    for label, root in roots(sandbox_bake).items():
        index = index_of(root)
        assert cs.errors("case-index", index) == [], label
        for e, m, t in baked(root):
            assert cs.errors("case-manifest", m) == [] and cs.errors("trace", t) == [], (label, e["case_id"])
            assert (root / m["artifact"]["path"]).stat().st_size == m["artifact"]["bytes"], (label, e["case_id"])
    # the provider tree is also the swap target of the sandbox: a fixture case carries the refused-case path
    assert any(e["status"] == "refused" for e in index_of(FIXTURE)["cases"])


@pytest.mark.parametrize("which", ["manifest", "trace"])
def test_adversarial_a_corrupted_document_is_seen(sandbox_bake, which):
    _e, m, t = next(baked(sandbox_bake[0]))
    doc = copy.deepcopy(m if which == "manifest" else t)
    if which == "manifest":
        doc["lane"] = "somewhere"
    else:
        doc["reference"]["method"] = "not-a-method-id"
    assert cs.errors("case-manifest" if which == "manifest" else "trace", doc)
