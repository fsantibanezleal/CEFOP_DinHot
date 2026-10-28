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


# ===== M1 block begin: the model slots (catalog rows cgh-net, warmstart-model), producer side =====
import hashlib  # noqa: E402

from pipeline.io import model_card  # noqa: E402

MODELS = cs.ROOT / "models"
SLOT_STEMS = {"cgh-net": "cgh-net", "warmstart-model": "warmstart"}


def _examples():
    return {slot: cs.load_json(cs.CONTRACTS / "examples" / f"{slot}.json") for slot in SLOT_STEMS}


def _released_cards():
    return {slot: cs.load_json(MODELS / f"{stem}.json") for slot, stem in SLOT_STEMS.items() if (MODELS / f"{stem}.json").is_file()}


def _fake_slot(tmp_path, slot, payload=b"onnx-bytes"):
    """A models directory whose card for ``slot`` is valid for ``payload`` standing in for the graph (the validity rule reads
    the card, the size and the SHA-256 only)."""
    models = tmp_path / "models"
    models.mkdir(parents=True, exist_ok=True)
    card = copy.deepcopy(_examples()[slot])
    card["onnx"] = f"models/{SLOT_STEMS[slot]}.onnx"
    card["sha256"], card["bytes"] = hashlib.sha256(payload).hexdigest(), len(payload)
    (models / f"{SLOT_STEMS[slot]}.onnx").write_bytes(payload)
    (models / f"{SLOT_STEMS[slot]}.json").write_text(json.dumps(card), encoding="utf-8")
    return models, card


def test_model_cards_validate():
    cards = {**{f"example/{k}": v for k, v in _examples().items()}, **{f"released/{k}": v for k, v in _released_cards().items()}}
    assert len(cards) >= 2
    for label, card in cards.items():
        assert cs.errors("model-card", card) == [], label
        assert card["slot"] == label.split("/")[1], label
        assert ("grid" in card) == (card["slot"] == "cgh-net"), label
        assert card["metrics_path"] == "data/derived/models/metrics.json", label
    for slot, card in _released_cards().items():
        data = (MODELS.parent / card["onnx"]).read_bytes()
        assert len(data) == card["bytes"] and hashlib.sha256(data).hexdigest() == card["sha256"], slot
        assert model_card.is_valid_slot(MODELS, slot), slot
        assert card["bytes"] <= (5 if slot == "cgh-net" else 1) * 1024 * 1024, slot
    bad = copy.deepcopy(_examples()["warmstart-model"])
    bad["grid"] = 128
    assert cs.errors("model-card", bad)                               # a warm start has no grid
    bad = copy.deepcopy(_examples()["cgh-net"])
    del bad["grid"]
    assert cs.errors("model-card", bad)                               # a cgh-net has one
    bad = copy.deepcopy(_examples()["cgh-net"])
    bad["onnx"] = "../elsewhere/cgh-net.onnx"
    assert cs.errors("model-card", bad)


def test_onnx_graphs_match_their_cards():
    onnx = pytest.importorskip("onnx")
    from pipeline.model.holo.learned.webops import WEB_SAFE_OPS
    cards = _released_cards()
    if not cards:
        pytest.skip("no released model graph: the baselines answer (readiness says training)")
    for slot, card in cards.items():
        g = onnx.load(str(MODELS.parent / card["onnx"])).graph

        def spec(vs):
            return [{"name": v.name, "shape": [d.dim_value for d in v.type.tensor_type.shape.dim], "dtype": "float32"} for v in vs]

        assert spec(g.input) == card["inputs"] and spec(g.output) == card["outputs"], slot
        assert {n.op_type for n in g.node} <= WEB_SAFE_OPS, slot
        opset = [o.version for o in onnx.load(str(MODELS.parent / card["onnx"])).opset_import if o.domain in ("", "ai.onnx")]
        assert opset == [card["opset"]], slot


def test_adversarial_swap_gs_baseline_and_cgh_net(tmp_path):
    """The baseline (GS, 30 iterations) and the network answer the same contract: a unit-energy 128 x 128 amplitude in, a finite
    128 x 128 phase out; an unreleased or altered slot is never used."""
    import numpy as np
    from pipeline.model.holo.core.geometry import Setup
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.types import Budget, Target
    from pipeline.model.holo.learned import generators
    from pipeline.model.holo.methods.baseline import m04_gs
    from pipeline.model.holo.methods.learned import m17_cgh_net
    setup = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
    a = generators.sample_target(np.random.default_rng(1), "ring").astype(np.float64)
    target = Target.from_field(a, a > 1e-2 * a.max())
    empty = tmp_path / "none"
    base = m17_cgh_net.run(setup, target, budget=Budget(1), rng=Rng(1), models_dir=empty)
    ref = m04_gs.run(setup, target, budget=Budget(30), rng=Rng(1))
    assert base.meta["provenance"] == "baseline" and base.phi.shape == (128, 128)
    np.testing.assert_array_equal(base.phi, ref.phi)                   # the baseline IS GS at 30 iterations
    models, _card = _fake_slot(tmp_path, "cgh-net")
    assert model_card.is_valid_slot(models, "cgh-net")
    (models / "cgh-net.onnx").write_bytes(b"onnx-bytez")             # same size, other bytes: the sha256 refuses it
    assert not model_card.is_valid_slot(models, "cgh-net")
    assert m17_cgh_net.run(setup, target, budget=Budget(1), rng=Rng(1), models_dir=models).meta["provenance"] == "baseline"
    if "cgh-net" in _released_cards():
        pytest.importorskip("onnxruntime")
        real = m17_cgh_net.run(setup, target, budget=Budget(1), rng=Rng(1))
        assert real.meta["provenance"] == "real" and real.phi.shape == base.phi.shape and np.isfinite(real.phi).all()
        assert not np.array_equal(real.phi, base.phi)
        assert set(real.history[0]) >= {"iteration", "efficiency", "uniformity", "rel_std", "time_s"}


def test_adversarial_swap_random_start_and_warmstart_model(tmp_path):
    """The random start (M07's own) and the learned start answer the same contract: a trap list in, a finite SLM phase and a
    history out; the baseline result is exactly M07 from its random start."""
    import numpy as np
    from pipeline.model.holo.core.geometry import Setup, focal_bin_m
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.traps import square_grid
    from pipeline.model.holo.core.types import Budget, Target
    from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs as m07
    from pipeline.model.holo.methods.learned import b3_warm_start
    setup = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)
    target = Target.from_traps(square_grid(4, 4, 8 * focal_bin_m(setup) * 1e6))
    empty = tmp_path / "none"
    base = b3_warm_start.run(setup, target, budget=Budget(6), rng=Rng(3), n_fix=12, models_dir=empty)
    ref = m07.run(setup, target, budget=Budget(6), rng=Rng(3), form="point")
    assert base.meta["provenance"] == "baseline"
    np.testing.assert_array_equal(base.phi, ref.phi)
    models, _card = _fake_slot(tmp_path, "warmstart-model")
    (models / "warmstart.onnx").write_bytes(b"onnx-bytez")
    assert not model_card.is_valid_slot(models, "warmstart-model")
    assert b3_warm_start.run(setup, target, budget=Budget(6), rng=Rng(3), n_fix=12, models_dir=models).meta["provenance"] == "baseline"
    if "warmstart-model" in _released_cards():
        pytest.importorskip("onnxruntime")
        real = b3_warm_start.run(setup, target, budget=Budget(6), rng=Rng(3))
        assert real.meta["provenance"] == "real" and real.phi.shape == base.phi.shape and np.isfinite(real.phi).all()
        assert len(real.history) == 6 and not np.array_equal(real.phi, base.phi)
# ===== M1 block end =====
