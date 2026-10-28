"""Producer-side tests of the document contracts (catalog rows case-index, case-manifest, trace, benchmark-results,
model-metrics): every document of a fresh sandbox bake, of the committed bake (when it exists) and of the provider tree
validates against its schema file (docs/contracts/schemas/) and obeys the rules a schema cannot state. The consumer and
swap side is frontend/src/lib/contract.test.ts, which runs the same assertions on the same roots. The model-slot and
engine-reference tests (model cards, ONNX graphs, engine reference) belong to the units that produce those documents.

The sandbox bake runs the small cases of tests/bake/bakefix.py with the planted methods; the canonical bake is the same
code on the twelve cases."""
from __future__ import annotations

import base64
import contextlib
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


# ---- engine-reference (catalog row engine-reference 1.0.0, unit T1) ------------------------------------------------------
# The reference values the TypeScript parity tests read (frontend/src/engine/holo/*.parity.test.ts): written by
# data-pipeline/pipeline/stages/engine_reference.py from the Python engine. The consumer side is those vitest files.

ENGINE_DIR = cs.ROOT / "tests" / "fixtures" / "engine"
ENGINE_EXAMPLE = cs.CONTRACTS / "examples" / "engine-reference.json"


def _engine_files() -> list[Path]:
    return sorted(ENGINE_DIR.glob("*.json"))


def _number_arrays(node):
    """Every encoded array ({shape, complex, data | b64}) inside a reference document."""
    if isinstance(node, dict):
        if "shape" in node and "complex" in node and ("data" in node or "b64" in node):
            yield node
        else:
            for v in node.values():
                yield from _number_arrays(v)
    elif isinstance(node, list):
        for v in node:
            yield from _number_arrays(v)


def test_engine_reference_validates():
    files = _engine_files()
    assert files, "tests/fixtures/engine holds no reference file (run python -m pipeline.stages.engine_reference)"
    version = (cs.ROOT / "VERSION").read_text(encoding="utf-8").strip()
    for f in files:
        doc = cs.load_json(f)
        assert cs.errors("engine-reference", doc) == [], f.name
        assert f.name == f"{doc['function']}.json", f.name
        assert tuple(map(int, doc["engine_version"].split("."))) <= tuple(map(int, version.split("."))), f.name


def test_engine_reference_example_validates():
    assert cs.errors("engine-reference", cs.load_json(ENGINE_EXAMPLE)) == []


def test_engine_reference_arrays_have_their_sizes():
    for f in _engine_files():
        for a in _number_arrays(cs.load_json(f)):
            n = 1
            for d in a["shape"]:
                n *= d
            n *= 2 if a["complex"] else 1
            size = len(a["data"]) if "data" in a else len(base64.b64decode(a["b64"])) // 8
            assert size == n, (f.name, a["shape"], a["complex"])


@contextlib.contextmanager
def _default_registry():
    """The real method registry, whatever a planted registry of another test left behind (restored afterwards)."""
    from pipeline.model.holo import methods as registry

    previous = registry._base
    registry.reload()
    try:
        yield registry
    finally:
        registry.reload(None if previous == registry.__name__ else previous)


def test_engine_reference_covers_every_live_method_and_the_core():
    have = {cs.load_json(f)["function"] for f in _engine_files()}
    with _default_registry() as registry:
        # The learned methods run in the browser through onnxruntime-web, not the TypeScript engine: their live parity is
        # the ONNX-against-torch check of the model slot (tests/learned/), so they need no engine-reference fixture.
        live = {s.id for s in registry.all_specs() if s.lane in ("live", "both") and s.family != "learned"}
    assert {f"methods.{m}" for m in live} <= have, sorted({f"methods.{m}" for m in live} - have)
    core = {"rng.stream", "geometry.setup_functions", "traps.generators", "forward.point_trap_fields", "forward.fft_focal_field",
            "forward.fft_inverse", "forward.angular_spectrum", "forward.axial_cut", "metrics.trap_metrics", "metrics.power_budget",
            "device.device_focal_field", "device.crosstalk", "zernike.wavefront", "camera.measure", "trapphys.formulas",
            "dynamics.trajectories", "dynamics.psd_fit", "live.M07"}
    assert core <= have, sorted(core - have)


def test_engine_reference_is_reproducible(tmp_path):
    """The documents are a pure function of the engine code: regenerating writes the committed bytes (engine_version aside)."""
    from pipeline.stages import engine_reference as er

    with _default_registry():
        written = er.write(tmp_path / "again", live=True)
    assert {p.name for p in written} == {f.name for f in _engine_files()}, "the committed set differs from the generated set"
    for p in written:
        fresh, old = cs.load_json(p), cs.load_json(ENGINE_DIR / p.name)
        fresh["engine_version"] = old["engine_version"]
        assert er.dump(fresh) == er.dump(old), f"{p.name} differs from a fresh run of the Python engine"


def test_adversarial_an_engine_reference_with_a_foreign_field_or_no_cases_fails():
    doc = cs.load_json(next(iter(_engine_files())))
    bad = copy.deepcopy(doc)
    bad["tolerance"]["relative"] = 1e-9
    assert cs.errors("engine-reference", bad)
    bad = copy.deepcopy(doc)
    bad["cases"] = []
    assert cs.errors("engine-reference", bad)
    bad = copy.deepcopy(doc)
    bad["schema"] = "dinhot.engine-ref/v0"
    assert cs.errors("engine-reference", bad)


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
    """The baseline (M19, volumetric 3D GS, 30 iterations) and the network answer the same contract: three plane amplitudes in, a
    finite 128 x 128 phase out; an unreleased or altered slot is never used."""
    import numpy as np
    from pipeline.model.holo.core.geometry import Setup, focal_bin_m
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.traps import Trap, TrapSet
    from pipeline.model.holo.core.types import Budget, Target
    from pipeline.model.holo.learned import convert, generators
    from pipeline.model.holo.methods.baseline import m19_multiplane
    from pipeline.model.holo.methods.learned import m17_cgh_net
    setup = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
    b, zr = focal_bin_m(setup), convert.rayleigh_range_m(setup)
    rows = generators.sample_volume(np.random.default_rng(1), "lattice")[1]
    target = Target.from_traps(TrapSet(Trap(i, r[0] * b, r[1] * b, r[2] * 8.0 * zr) for i, r in enumerate(rows)))
    empty = tmp_path / "none"
    base = m17_cgh_net.run(setup, target, budget=Budget(1), rng=Rng(1), models_dir=empty)
    ref = m19_multiplane.run(setup, target, budget=Budget(30), rng=Rng(1), dz_m=m17_cgh_net.plane_dz_m(setup))
    assert base.meta["provenance"] == "baseline" and base.phi.shape == (128, 128)
    np.testing.assert_array_equal(base.phi, ref.phi)                   # the baseline IS M19 at 30 iterations
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
