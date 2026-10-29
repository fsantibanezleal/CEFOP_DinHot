"""I2: case C13, the disordered 819-trap array of Kim et al. 2019, on integer FFT bins with a minimum spacing."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from pipeline.cases import library
from pipeline.model.holo.methods.baseline import _gs
from pipeline.stages import infer, preprocess

ROOT = Path(__file__).resolve().parents[2]
CID = "C13_disordered_array"


def _case():
    return next(c for c in library.CASES if c.id == CID)


def test_the_registry_lists_c13_next_to_c03():
    ids = [c.id for c in library.CASES]
    assert CID in ids and len(ids) >= 13 and ids.count(CID) == 1   # I3: a fourteenth case landed (C14)
    c, c03 = _case(), next(c for c in library.CASES if c.id == "C03_large_array")
    assert c.category == library.CAT_ARRAYS
    r, r03 = c.record, c03.record
    assert r["setup"] == r03["setup"] and r["device"] == r03["device"]
    assert r["methods"] == r03["methods"] and r["reference_method"] == "M07"
    assert "10.1364/OL.44.003178" in c.anchor["url"] and "1.2" in c.anchor["source"]["en"]
    assert c.title["en"] and c.title["es"]


def test_contract_1_accepts_c13_and_the_committed_cases_document_holds_it():
    rec = _case().record
    assert library.EXPECT_BASIS[CID] in ("provisional", "anchor")
    report, _ = preprocess.run(ROOT / "data" / "examples" / "cases.json", ROOT)
    assert CID in [r["case_id"] for r in report.accepted]
    assert [r["case_id"] for r in report.rejected] == ["C11_outside_field"]
    committed = next(r for r in json.loads((ROOT / "data" / "examples" / "cases.json").read_text("utf-8"))
                     if r["case_id"] == CID)
    assert committed == rec


def test_c13_is_819_traps_on_bins_at_least_five_bins_apart():
    rec = _case().record
    traps = rec["target"]["traps"]
    assert len(traps) == 819 and len({t["id"] for t in traps}) == 819
    ctx = infer.case_context(rec)
    assert _gs.on_bins(ctx["setup"], ctx["target"].traps)          # so the FFT form applies
    b = library._bin_um(rec["setup"])
    p = np.array([[t["x_um"] / b, t["y_um"] / b] for t in traps])
    d = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1)) + np.eye(len(p)) * 1e9
    assert d.min() >= 5 - 2e-3
    assert np.abs(p).max() <= 100 + 2e-3


def test_c13_keys_every_method_range_to_its_method():
    ex = _case().record["expect"]
    measured = library._measured_ranges()[CID]
    assert ex == measured and len(ex) == 20, "the case's ranges are the measured ones, not the declared bands"
    assert not any(k.startswith("B3.") for k in ex)           # B3 is not registered in this build: nothing was measured
    for k in ex:
        assert "." in k or k.startswith(("feedback_", "fc_")) or k in ("efficiency", "rel_std_pct", "uniformity"), k
