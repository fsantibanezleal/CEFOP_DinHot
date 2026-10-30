"""I3: case C14, the three-plane volume at the geometry of the released cgh-net (M17 answers on it in the browser and in the bake)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from pipeline.cases import library
from pipeline.model.holo.core.geometry import focal_bin_m
from pipeline.model.holo.learned import convert
from pipeline.model.holo import methods as registry
from pipeline.model.holo.methods.learned import m17_cgh_net
from pipeline.stages import infer, preprocess

ROOT = Path(__file__).resolve().parents[2]
CID = "C14_volume_learned"
# the real method tree, not the registry in force: a session-scoped planted registry of the bake tests may be redirected at this point
REAL_SPECS = {m.spec.id: m.spec for m in registry.discover()}
CARD = json.loads((ROOT / "models" / "cgh-net.json").read_text("utf-8"))


def _case():
    return next(c for c in library.CASES if c.id == CID)


def test_the_registry_lists_c14_in_the_shaped_and_3d_category():
    ids = [c.id for c in library.CASES]
    assert CID in ids and len(ids) == 14 and ids.count(CID) == 1
    c = _case()
    assert c.category == library.CAT_SHAPED
    assert c.record["reference_method"] == "M17"
    assert {"M17", "M19", "M04"} <= set(c.record["methods"])
    assert c.title["en"] and c.title["es"] and c.expected_band["en"] and c.expected_band["es"]


def test_contract_1_accepts_c14_and_the_committed_cases_document_holds_it():
    rec = _case().record
    assert library.EXPECT_BASIS[CID] in ("provisional", "anchor")
    report, _ = preprocess.run(ROOT / "data" / "examples" / "cases.json", ROOT)
    assert CID in [r["case_id"] for r in report.accepted]
    assert [r["case_id"] for r in report.rejected] == ["C11_outside_field"]
    committed = next(r for r in json.loads((ROOT / "data" / "examples" / "cases.json").read_text("utf-8"))
                     if r["case_id"] == CID)
    assert committed == rec


def test_c14_is_the_geometry_of_the_released_model_card():
    rec = _case().record
    inp, out = CARD["inputs"][0]["shape"], CARD["outputs"][0]["shape"]
    assert inp == [1, 3, CARD["grid"], CARD["grid"]] and out == [1, 1, CARD["grid"], CARD["grid"]]
    s = rec["setup"]
    assert s["n_pix"] == CARD["grid"] == 128 and s["pad"] == 1            # the SLM and the padding the card names
    ctx = infer.case_context(rec)
    setup, traps = ctx["setup"], ctx["target"].traps
    # the planes are at -8, 0, +8 SLM-limited Rayleigh ranges (the card's "planes at -8, 0, +8")
    zr = convert.rayleigh_range_m(setup)
    planes = np.rint(traps.z_m / zr / 8.0).astype(int)
    assert set(planes.tolist()) == {-1, 0, 1}
    assert np.abs(traps.z_m / zr - 8.0 * planes).max() < 0.05
    counts = [int((planes == p).sum()) for p in (-1, 0, 1)]
    assert len(set(counts)) == 1 and counts[0] >= 9                    # equal counts per plane
    # integer lateral bins within 60 bins of the axis, no vortex, equal weights, no repeated site in a plane
    b = focal_bin_m(setup)
    x, y = traps.x_m / b, traps.y_m / b
    assert np.abs(x - np.rint(x)).max() < 1e-3 and np.abs(y - np.rint(y)).max() < 1e-3
    assert np.abs(x).max() <= 60 and np.abs(y).max() <= 60
    assert not traps.charge.any() and len(set(traps.weight.tolist())) == 1
    for p in (-1, 0, 1):
        sites = {(int(round(a)), int(round(c))) for a, c in zip(x[planes == p], y[planes == p])}
        assert len(sites) == counts[0]
    # M17 takes it: the network input is built without a ValueError
    assert m17_cgh_net.planes_from_traps(setup, traps).shape == tuple(inp)


def test_c14_methods_are_registered_and_take_the_target():
    rec = _case().record
    specs = REAL_SPECS
    for m in rec["methods"]:
        assert m in specs, m
        assert infer.spec_problem(specs[m], rec) is None, m


def test_c14_keys_every_method_range_to_its_method():
    ex = _case().record["expect"]
    measured = library._measured_ranges()[CID]
    assert ex == measured and ex, "the case's ranges are the measured ones, not the declared bands"
    for k in ex:
        assert k.split(".")[0] in _case().record["methods"] or k in ("efficiency", "rel_std_pct", "uniformity"), k
    assert any(k.startswith("M17.") for k in ex)


def test_no_case_lists_a_registered_method_that_refuses_its_target():
    """C04 listed M17 for a field after M17 became the three-plane volume method: the bake of C04 failed on it. A registered method of
    a case must take the case's target (a method not registered in this build, B3, is flagged by the bake instead)."""
    specs = REAL_SPECS
    bad = [(c.id, m, infer.spec_problem(specs[m], c.record)) for c in library.CASES for m in c.record["methods"]
           if m in specs and infer.spec_problem(specs[m], c.record)]
    assert bad == []
