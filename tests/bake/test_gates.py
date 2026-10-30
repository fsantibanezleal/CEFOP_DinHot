"""The assignment, the trace encoding and decimation, the lane gate and the units gate of the bake."""
from __future__ import annotations

import copy
import itertools
import json
import math

import numpy as np
import pytest

from pipeline.core import gate, trace, units
from pipeline.core.assign import assign


# ---- assignment --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("n,m", [(1, 1), (3, 3), (4, 6), (5, 5), (6, 7)])
def test_assignment_matches_brute_force(n, m):
    rng = np.random.default_rng(n * 10 + m)
    for _ in range(8):
        cost = rng.uniform(0, 10, size=(n, m)).tolist()
        pick = assign(cost)
        assert len(set(pick)) == n
        best = min(sum(cost[i][c] for i, c in enumerate(cols)) for cols in itertools.permutations(range(m), n))
        assert sum(cost[i][c] for i, c in enumerate(pick)) == pytest.approx(best)


def test_assignment_rejects_more_rows_than_columns():
    with pytest.raises(ValueError):
        assign([[1.0], [2.0]])


# ---- trace encoding and decimation -------------------------------------------------------------------------------------
def test_decimation_keeps_first_and_last_and_the_limit():
    for n in (1, 2, 199, 200, 201, 1000, 5001):
        idx = trace.decimate_indices(n, 200)
        assert idx[0] == 0 and idx[-1] == n - 1 and len(idx) <= 200 and idx == sorted(set(idx))
    hist = [{"iteration": i, "efficiency": 0.5, "uniformity": 0.5, "rel_std": 1.0, "time_s": 0.0} for i in range(1000)]
    out = trace.decimate_history(hist, 200)
    assert out[0]["iteration"] == 0 and out[-1]["iteration"] == 999 and len(out) == 200
    assert set(out[0]) == {"iteration", "efficiency", "uniformity", "rel_std_pct"}


def test_rle_roundtrip():
    mask = np.zeros((6, 6), dtype=bool)
    mask[2:4, 1:5] = True
    runs = trace.mask_rle(mask)
    flat, val = [], False
    for r in runs:
        flat += [val] * r
        val = not val
    assert np.array_equal(np.array(flat).reshape(6, 6), mask) and sum(runs) == 36
    assert trace.mask_rle(np.ones((2, 2), dtype=bool))[0] == 0


def test_phase_and_db_encoding_ranges():
    phi = np.array([[0.0, math.pi], [2 * math.pi, -0.1]])
    b = trace.phase_u8(phi)
    assert len(b) == 4 and b[0] == 0 and b[1] == 128 and b[2] == 0
    db = trace.db_u8(np.array([[1.0, 0.1], [1e-9, 5.0]]), 1.0)
    assert db[0] == 255 and db[1] == round(30 / 40 * 255) and db[2] == 0 and db[3] == 255


def test_max_pool_never_loses_a_peak():
    a = np.zeros((8, 8))
    a[3, 5] = 7.0
    assert trace.max_pool(a, 4).max() == 7.0 and trace.max_pool(a, 4).shape == (2, 2)


def test_log_psd_limit():
    f = np.arange(1, 5001) * 0.5
    of, op = trace.log_psd(f, 1.0 / f**2)
    assert len(of) == len(op) <= 200 and of == sorted(of) and of[0] >= f[0] and of[-1] <= f[-1]


def parts(n_traps=4, methods=3, hist=400):
    traps = [{"id": i, "x_um": float(i), "y_um": 0.0, "z_um": 0.0, "weight": 1.0, "charge": 0} for i in range(n_traps)]
    h = [{"iteration": i, "efficiency": 0.5, "uniformity": 0.5, "rel_std": 1.234567, "time_s": 0.0} for i in range(hist)]
    final = {"efficiency": 0.5, "uniformity": 0.5, "rel_std_pct": 1.0, "zero_order": 0.01, "ghost": 0.1}
    ti = [1.0] * n_traps
    return {"case_id": "C99_x", "grid": {"n_pix": 64, "pad": 2, "bin_um": 0.5, "half_field_um": 32.0}, "traps": traps,
            "shape": None, "methods": {f"M0{k}": {"history": h, "final": final, "trap_intensity": ti} for k in range(methods)},
            "reference": {"method": "M00", "phi": np.zeros((64, 64)), "intensity": np.ones((128, 128)), "ref_level": 1.0,
                          "extent_bins": 20.0, "axial": None},
            "feedback": None, "dynamics": None, "rearrangement": None,
            "summary": {"best_method": "M00", "notes": {"en": "x", "es": "x"}}}


def test_a_trace_that_fits_is_not_squeezed_and_one_that_does_not_is_squeezed_or_refused():
    t, n, step = trace.fit(parts())
    assert step == 0 and n <= gate.TRACE_BYTES_GATE and len(t["methods"]["M00"]["history"]) == 200
    big = parts(n_traps=4000, methods=14)
    with pytest.raises(trace.TraceTooLarge, match="C99_x"):
        trace.fit(big)
    mid = parts(n_traps=1350, methods=8)
    t2, n2, step2 = trace.fit(mid)
    assert n2 <= gate.TRACE_BYTES_GATE and step2 >= 1
    assert t2["methods"]["M00"]["history"][-1]["iteration"] == 399        # the last point is never dropped


def test_dynamics_trajectory_is_thinned_by_the_squeeze():
    p = parts(n_traps=900, methods=8)
    n = 4000
    p["dynamics"] = {"particle": "bead", "dt_s": 1e-5, "t_decimation": 2, "x_um": [0.0] * n, "y_um": [0.0] * n,
                     "psd": {"f_hz": [1.0], "p": [1.0]}, "fc_hz": 100.0, "kappa_pn_per_um": 1.0,
                     "depth": {"value": 10.0, "unit": "kBT"}}
    t, nbytes, step = trace.fit(p)
    d = t["dynamics"]
    assert nbytes <= gate.TRACE_BYTES_GATE and len(d["x_um"]) == len(d["y_um"]) <= 4000
    assert d["t_decimation"] * len(d["x_um"]) >= 2 * n - d["t_decimation"]


# ---- lane gate ---------------------------------------------------------------------------------------------------------
def test_lane_gate_decisions_and_budgets():
    ok = gate.classify_lane(pure_python=True, wheels={"numpy"}, run_ms=100.0, trace_bytes=1000)
    assert ok["lane"] == "live" and ok["reasons"] == [] and "run_ms" not in ok
    slow = gate.classify_lane(pure_python=True, wheels={"numpy"}, run_ms=gate.RUN_MS_GATE + 1, trace_bytes=1000)
    assert slow["lane"] == "precompute" and "exceeds" in slow["reasons"][0]
    big = gate.classify_lane(pure_python=True, wheels={"numpy"}, run_ms=1.0, trace_bytes=gate.TRACE_BYTES_GATE + 1)
    assert big["lane"] == "precompute"
    assert gate.classify_lane(pure_python=True, wheels={"numpy", "torch"}, run_ms=1.0, trace_bytes=1)["lane"] == "precompute"
    baked = gate.classify_lane(pure_python=True, wheels={"numpy"}, run_ms=1.0, trace_bytes=1, extra_reasons=("reference is baked",))
    assert baked["lane"] == "precompute" and baked["reasons"] == ["reference is baked"]


def test_method_lane_needs_the_spec_and_the_time():
    assert gate.method_lane("live", 10.0) == "live" and gate.method_lane("both", 10.0) == "live"
    assert gate.method_lane("baked", 1.0) == "baked" and gate.method_lane("live", 1501.0) == "baked"


def test_measure_ms_warms_up_and_takes_the_median():
    calls = []
    assert gate.measure_ms(lambda: calls.append(1), repeats=3) >= 0.0 and len(calls) == 4


# ---- units gate --------------------------------------------------------------------------------------------------------
def baked_pair(sandbox_bake):
    root = sandbox_bake[0]
    m = json.loads((root / "manifests" / "C91_mini.json").read_text(encoding="utf-8"))
    return m, json.loads((root / m["artifact"]["path"]).read_text(encoding="utf-8"))


def test_units_hold_on_a_bake_and_over_the_tree(sandbox_bake):
    m, t = baked_pair(sandbox_bake)
    assert units.check_case(m, t) == []
    assert units.check_tree(sandbox_bake[0]) == []


def test_adversarial_a_percent_written_as_a_fraction_is_caught(sandbox_bake):
    """The Fragua lesson: the same field with the wrong quantity or unit must fail."""
    m, t = baked_pair(sandbox_bake)
    bad = copy.deepcopy(t)
    bad["methods"]["M06"]["final"]["rel_std_pct"] /= 100.0
    assert any("fraction written as a percent" in p for p in units.check_case(m, bad))
    bad = copy.deepcopy(t)
    bad["methods"]["M06"]["final"]["uniformity"] = 0.5 * bad["methods"]["M06"]["final"]["uniformity"]
    assert any("uniformity" in p for p in units.check_case(m, bad))
    bad = copy.deepcopy(t)
    bad["methods"]["M06"]["trap_intensity"] = [v * 100 for v in bad["methods"]["M06"]["trap_intensity"]]
    assert any("relative to the mean" in p for p in units.check_case(m, bad))


def test_adversarial_domain_and_unit_violations(sandbox_bake):
    m, t = baked_pair(sandbox_bake)
    cases = {
        "efficiency above 1": lambda x: x["methods"]["M04"]["final"].__setitem__("efficiency", 1.2),
        "negative zero order": lambda x: x["methods"]["M04"]["final"].__setitem__("zero_order", -0.1),
        "position in metres": lambda x: x["traps"][0].__setitem__("x_um", 4e-6),
        "trap outside the field": lambda x: x["traps"][0].__setitem__("x_um", 1e3),
        "dt in ms written as s": lambda x: x["dynamics"].__setitem__("dt_s", 5.0),
        "negative fc": lambda x: x["dynamics"].__setitem__("fc_hz", -1.0),
        "stiffness in N/m": lambda x: x["dynamics"].__setitem__("kappa_pn_per_um", 4e-6 * 1e13),
        "phase size": lambda x: x["reference"].__setitem__("phase_u8", "AAAA"),
        "grid micrometres": lambda x: x["grid"].__setitem__("bin_um", 0.5e-6),
    }
    for name, plant in cases.items():
        bad = copy.deepcopy(t)
        plant(bad)
        assert units.check_case(m, bad), name
    with pytest.raises(units.UnitsError, match="units gate failed"):
        units.require(["x"])


def test_benchmark_units():
    stat = {"median": 0.5, "q1": 0.4, "q3": 0.6}
    row = {"method": "M04", "geometry": "G1", "device": "ideal", "budget_kind": "iterations", "budget": 10, "params": "default",
           "n_seeds": 2, "efficiency": stat, "uniformity": stat, "rel_std_pct": stat, "time_s": stat, "iterations": stat}
    assert units.check_benchmark({"rows": [row], "pareto": []}) == []
    bad = {**row, "efficiency": {"median": 1.5, "q1": 0.4, "q3": 0.6}}
    assert units.check_benchmark({"rows": [bad], "pareto": []})
