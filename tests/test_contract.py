"""CONTRACT 1 (ingestion) tests: good records validate; bad records are rejected with a reason, never coerced; suspicious ones
are flagged; trap coordinates are rounded once."""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "bake"))

import bakefix  # noqa: E402

from pipeline.io.contract import bin_um, half_field_um, validate_records  # noqa: E402


def one(rec):
    return validate_records([rec])


def rejected_with(rec, code):
    rep = one(rec)
    assert not rep.accepted and rep.rejected, rep.summary()
    assert rep.rejected[0]["code"] == code, rep.rejected[0]
    assert rep.rejected[0]["reason"] and rep.rejected[0]["reason_es"]
    return rep.rejected[0]


def test_good_record_accepted():
    rep = one(bakefix.record())
    assert rep.ok and len(rep.accepted) == 1 and not rep.rejected


def test_adversarial_bad_values_rejected_not_coerced():
    for path, value in ((("setup", "wavelength_nm"), "850"), (("setup", "wavelength_nm"), float("nan")),
                        (("setup", "wavelength_nm"), float("inf")), (("setup", "na"), True), (("seed",), -1),
                        (("setup", "n_pix"), 100), (("budget", "iterations"), 0), (("seed",), 1.5)):
        rec = bakefix.record()
        node = rec
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        rep = one(rec)
        assert not rep.accepted, (path, value)
        assert path[-1] in rep.rejected[0]["reason"], rep.rejected[0]["reason"]


def test_missing_field_and_extra_field_rejected():
    rec = bakefix.record()
    del rec["budget"]
    assert "budget" in rejected_with(rec, "schema")["reason"]
    assert "unexpected" in rejected_with({**bakefix.record(), "colour": "red"}, "schema")["reason"]


def test_out_of_field_names_the_bound():
    rec = bakefix.record(feedback=None, dynamics=None, target={"kind": "traps", "traps": [bakefix.trap(0, 400.0, 0.0)]})
    r = rejected_with(rec, "out_of_field")
    bound = half_field_um(rec["setup"])
    assert f"{bound:.1f}" in r["reason"] and r["bound_um"] == round(bound, 3)
    just_in = bakefix.record(feedback=None, dynamics=None, target={"kind": "traps", "traps": [bakefix.trap(0, bound - 0.01, 0.0)]})
    assert one(just_in).ok
    on_the_edge = bakefix.record(feedback=None, dynamics=None, target={"kind": "traps", "traps": [bakefix.trap(0, bound, 0.0)]})
    rejected_with(on_the_edge, "out_of_field")      # the bin at the bound is outside the centred FFT grid


def test_cross_field_rules():
    t = bakefix.grid(3, 4.0)
    rejected_with(bakefix.record(target={"kind": "traps", "traps": t + [bakefix.trap(0, 9.0, 9.0)]}), "duplicate_trap_id")
    rejected_with(bakefix.record(reference_method="M09"), "reference_method")
    rec = bakefix.record()
    rec["setup"]["na"], rec["setup"]["n_imm"] = 1.4, 1.33
    rejected_with(rec, "na")
    dev = {"bit_depth": 4, "crosstalk": None, "upsample": 1, "fill_factor": 1.0, "flicker_rad": 0.0, "lut_gamma": 1.0}
    off_plane = {"kind": "traps", "traps": [bakefix.trap(0, 0, 0, 5.0)]}
    rejected_with(bakefix.record(device=dev, feedback=None, dynamics=None, target=off_plane), "device_scope")
    rejected_with(bakefix.record(device=dev, feedback=None, dynamics=None, aberration={"noll": {"4": 0.1}}), "device_scope")
    rejected_with({**bakefix.shaped_record(), "feedback": bakefix.record()["feedback"]}, "feedback")
    rec = bakefix.record()
    rec["dynamics"]["trap_id"] = 99
    rejected_with(rec, "dynamics_trap")
    rearr = bakefix.rearr_record()
    rearr["rearrangement"]["target_ids"] = [99]
    rejected_with(rearr, "rearrangement_ids")
    sh = bakefix.shaped_record()
    sh["target"] = {"kind": "shaped", "shape": "ring", "radius_um": 5.0, "signal_margin_bins": 1}
    rejected_with(sh, "shape")
    rejected_with(bakefix.record(expect={"colour": [0, 1]}), "expect")
    rejected_with(bakefix.record(expect={"M09.efficiency": [0, 1]}), "expect")
    rejected_with(bakefix.record(expect={"efficiency": [1.0, 0.0]}), "expect")


def test_duplicate_case_ids_second_rejected():
    rep = validate_records([bakefix.record(), bakefix.record()])
    assert len(rep.accepted) == 1 and rep.rejected[0]["code"] == "duplicate_case"


def test_outlier_flagged_but_accepted():
    rec = bakefix.record()
    rec["setup"]["na"], rec["setup"]["n_imm"] = 1.2, 1.33
    rep = one(rec)
    assert rep.ok and any("scalar model" in f["flag"] for f in rep.flagged)
    close = bakefix.record(feedback=None, dynamics=None, target={"kind": "traps", "traps": [bakefix.trap(0, 0, 0), bakefix.trap(1, 0.5, 0)]})
    assert any("closer than the focal spot" in f["flag"] for f in one(close).flagged)


def test_coordinates_rounded_once_and_input_not_mutated():
    rec = bakefix.record(feedback=None, dynamics=None, target={"kind": "traps", "traps": [bakefix.trap(0, 1.234567891, -0.00004)]})
    before = copy.deepcopy(rec)
    out = one(rec).accepted[0]["target"]["traps"][0]
    assert out["x_um"] == 1.2346 and out["y_um"] == 0.0 and math.copysign(1, out["y_um"]) == 1.0
    assert rec == before
    again = validate_records([one(rec).accepted[0]]).accepted[0]
    assert again["target"] == one(rec).accepted[0]["target"]      # rounding is idempotent: once is enough


def test_bin_and_half_field_units():
    s = bakefix.SETUP
    assert half_field_um(s) == pytest.approx(0.85e-6 * 1.5e-3 / (2 * 20e-6) * 1e6)
    assert bin_um(s) == pytest.approx(half_field_um(s) * 2 / (2 * 64))
