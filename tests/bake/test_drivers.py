"""The drivers of a case: camera feedback, the particle simulation and the rearrangement plan."""
from __future__ import annotations

import json
import math

import bakefix
import numpy as np
import pytest

from pipeline.stages import rearrangement


def trace_of(sandbox_bake, case):
    root = sandbox_bake[0]
    m = json.loads((root / "manifests" / f"{case}.json").read_text(encoding="utf-8"))
    return m, json.loads((root / m["artifact"]["path"]).read_text(encoding="utf-8"))


def test_feedback_reduces_the_measured_spread(sandbox_bake):
    _m, t = trace_of(sandbox_bake, "C91_mini")
    steps = t["feedback"]["steps"]
    assert [s["step"] for s in steps] == [0, 1, 2, 3]
    assert steps[-1]["rel_std_pct"] < 0.5 * steps[0]["rel_std_pct"], steps
    assert 5 < steps[0]["rel_std_pct"] < 40        # the camera gain error of 15 percent rms shows before the loop


def test_bead_spectrum_recovers_the_corner_frequency(sandbox_bake):
    m, t = trace_of(sandbox_bake, "C91_mini")
    d = t["dynamics"]
    gamma = 6 * math.pi * 0.00089 * 0.5e-6
    expected = d["kappa_pn_per_um"] * 1e-6 / (2 * math.pi * gamma)          # pN/um to N/m is 1e-6 * 1e... (1 pN/um = 1e-6 N/m)
    assert d["fc_hz"] == pytest.approx(expected, rel=0.3)
    assert d["depth"]["unit"] == "kBT" and d["depth"]["value"] > 10
    assert len(d["x_um"]) <= 4000 and d["t_decimation"] >= 1


def test_rearrangement_plan_moves_surplus_atoms_into_the_target_without_losing_any():
    rec = bakefix.rearr_record()
    loaded, moves, still_empty = rearrangement.plan(rec)
    targets = set(rec["rearrangement"]["target_ids"])
    assert set(loaded) >= {a for a, _ in moves} and all(b in targets and b not in loaded for _, b in moves)
    assert len({a for a, _ in moves}) == len(moves) == len({b for _, b in moves})
    assert all(a not in targets for a, _ in moves)
    assert len(moves) + len(still_empty) == len(targets - set(loaded))


def test_rearrangement_frames_and_filling(sandbox_bake):
    m, t = trace_of(sandbox_bake, "C93_rearr")
    r = t["rearrangement"]
    steps = 4
    assert len(r["frames"]) == steps + 1 == len(r["filling"])
    assert r["frames"][0]["t_s"] == 0 and r["frames"][-1]["moving"] == []
    assert r["filling"] == sorted(r["filling"]) and 0 <= r["filling"][-1] <= 1
    ts = [f["t_s"] for f in r["frames"]]
    assert ts == sorted(ts)
    assert r["min_transient"] >= 0


def test_shaped_case_scores_inside_the_shape(sandbox_bake):
    m, t = trace_of(sandbox_bake, "C92_disc")
    assert t["traps"] == [] and t["shape"]["kind"] == "disc" and sum(t["shape"]["mask_rle"]) == t["reference"]["focal"]["size"] ** 2
    assert 0 < m["methods"]["M08"]["efficiency"] <= 1 and t["methods"]["M08"]["trap_intensity"] == []
    assert np.isfinite(m["methods"]["M08"]["rel_std_pct"])
