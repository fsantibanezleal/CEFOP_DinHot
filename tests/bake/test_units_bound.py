"""The units gate bounds the relative standard deviation by its mathematical maximum for the trap count it was computed
over, 100 sqrt(N - 1) (the population deviation of N non-negative intensities, all the light in one trap); BM-006, BK-009."""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

from pipeline.core import units
from pipeline.model.holo.core import metrics

STAT = {"median": 0.5, "q1": 0.4, "q3": 0.6}
GEOMS = [{"id": "G1", "n_traps": 100}, {"id": "G4", "n_traps": 119}, {"id": "G6b", "n_traps": 819}, {"id": "G7", "n_traps": 0},
         {"id": "G0", "n_traps": 1}]


def _row(geometry: str, rel_std: float, kind: str = "time", budget: float = 0.05, q1: float | None = None) -> dict:
    rs = {"median": rel_std, "q1": rel_std if q1 is None else q1, "q3": rel_std}
    return {"method": "M03", "geometry": geometry, "device": "device", "budget_kind": kind, "budget": budget,
            "params": "default", "n_seeds": 5, "efficiency": STAT, "uniformity": STAT, "rel_std_pct": rs,
            "time_s": STAT, "iterations": STAT}


def _doc(*rows: dict, geoms=GEOMS) -> dict:
    return {"geometries": geoms, "rows": list(rows), "pareto": []}


def test_the_bound_is_the_population_maximum_of_the_relative_standard_deviation():
    assert units.rel_std_bound(1) == 0.0
    for n in (2, 36, 100, 119, 819, 1024):
        # all the light in one trap: the most spread N non-negative intensities can have, computed by the product's own metric
        one = np.zeros(n)
        one[0] = 1.0
        assert units.rel_std_bound(n) == pytest.approx(metrics.rel_std(one), rel=1e-12)
        assert units.rel_std_bound(n) == pytest.approx(100.0 * math.sqrt(n - 1), rel=1e-12)
    assert units.rel_std_bound(100) == pytest.approx(994.987, abs=1e-3)
    assert units.rel_std_bound(119) == pytest.approx(1086.28, abs=1e-2)
    assert units.rel_std_bound(819) == pytest.approx(2860.07, abs=1e-2)


def test_a_shaped_target_keeps_the_finite_cap_of_its_clipped_signal_error():
    # score.py clips the shaped target's rel_std_pct (the signal RMS error) at REL_STD_CAP = 1000, so no trap count applies
    assert units.rel_std_bound(0) == 1000.0
    assert units.rel_std_bound(-3) == 1000.0


def test_the_failed_stage_rows_pass():
    doc = _doc(_row("G6b", 2446.825072), _row("G4", 1081.19212), _row("G4", 934.5, kind="iterations", budget=10))
    assert units.check_benchmark(doc) == []


def test_the_maximum_passes_and_a_value_above_it_fails_per_geometry():
    assert units.check_benchmark(_doc(_row("G6b", 100 * math.sqrt(818)))) == []
    assert units.check_benchmark(_doc(_row("G1", 100 * math.sqrt(99)))) == []
    assert units.check_benchmark(_doc(_row("G6b", 2900.0)))
    assert units.check_benchmark(_doc(_row("G1", 1100.0)))
    assert units.check_benchmark(_doc(_row("G4", 1090.0)))


def test_a_row_is_checked_against_its_own_geometry_not_another():
    # 1500 is fine on 819 traps and a violation on 100 and on 119
    assert units.check_benchmark(_doc(_row("G6b", 1500.0))) == []
    assert units.check_benchmark(_doc(_row("G1", 1500.0)))
    assert units.check_benchmark(_doc(_row("G4", 1500.0)))
    # the order of the geometry list does not matter
    assert units.check_benchmark(_doc(_row("G6b", 1500.0), geoms=list(reversed(GEOMS)))) == []


def test_one_trap_allows_only_zero():
    assert units.check_benchmark(_doc(_row("G0", 0.0))) == []
    assert units.check_benchmark(_doc(_row("G0", 0.5)))


def test_negative_and_non_finite_values_still_fail():
    assert units.check_benchmark(_doc(_row("G6b", -1.0)))
    assert units.check_benchmark(_doc(_row("G6b", float("nan"))))
    assert units.check_benchmark(_doc(_row("G6b", float("inf"))))


def test_q1_above_median_is_still_reported_and_each_quartile_is_bounded():
    bad = _row("G1", 500.0, q1=1100.0)
    assert any("rel_std_pct.q1" in p for p in units.check_benchmark(_doc(bad)))


def test_a_shaped_geometry_row_is_bounded_by_the_clipped_cap():
    assert units.check_benchmark(_doc(_row("G7", 1000.0))) == []
    assert units.check_benchmark(_doc(_row("G7", 1200.0)))


def test_an_unknown_geometry_is_a_units_problem_not_a_silent_pass():
    problems = units.check_benchmark(_doc(_row("G9", 10.0)))
    assert problems and any("unknown geometry" in p and "G9" in p for p in problems)
    problems = units.check_benchmark({"rows": [_row("G1", 10.0)], "pareto": []})   # no geometries listed at all
    assert any("unknown geometry" in p for p in problems)


def test_the_other_observables_are_unchanged():
    row = _row("G1", 10.0)
    row["efficiency"] = {"median": 1.5, "q1": 0.4, "q3": 0.6}
    assert any("efficiency" in p for p in units.check_benchmark(_doc(row)))


def test_method_row_takes_the_trap_count():
    base = {"efficiency": 0.5, "uniformity": 0.5, "rel_std_pct": 2446.8, "iterations": 3}
    assert units.check_method_row(base, "x", n_traps=819) == []
    assert units.check_method_row({**base, "rel_std_pct": 2900.0}, "x", n_traps=819)
    assert units.check_method_row({**base, "rel_std_pct": 1100.0}, "x", n_traps=100)
    assert units.check_method_row({**base, "rel_std_pct": 0.1}, "x", n_traps=1)
    assert units.check_method_row({**base, "rel_std_pct": 0.0}, "x", n_traps=1) == []
    assert units.check_method_row({**base, "rel_std_pct": 1000.0}, "x", n_traps=0) == []
    assert units.check_method_row({**base, "rel_std_pct": 1001.0}, "x", n_traps=0)


def _case(n: int, rel_std: float):
    """A minimal case manifest and trace of ``n`` traps (n = 0: a shaped target) carrying ``rel_std`` everywhere."""
    half = 10.0
    traps = [{"id": i, "x_um": 1.0 + i * 0.01, "y_um": 1.0, "weight": 1.0} for i in range(n)]
    final = {"efficiency": 0.5, "uniformity": 0.5, "rel_std_pct": rel_std, "iterations": 1}
    hist = [{"iteration": 1, "efficiency": 0.5, "uniformity": 0.5, "rel_std_pct": rel_std}]
    ti = [1.0] * n
    trace = {"grid": {"half_field_um": half, "bin_um": 1.0, "n_pix": 10, "pad": 2}, "traps": traps,
             "methods": {"M04": {"final": final, "history": hist, "trap_intensity": ti}},
             "reference": {"phase_u8": "AAAA", "focal": {"size": 1, "intensity_db_u8": "AA=="}, "axial": None},
             "feedback": {"steps": [{"step": 0, "rel_std_pct": rel_std, "efficiency": 0.5}]},
             "dynamics": None, "rearrangement": None}
    manifest = {"case_id": "C0", "methods": {"M04": dict(final)}}
    return manifest, trace


def _case_problems(n: int, rel_std: float) -> list[str]:
    m, t = _case(n, rel_std)
    # only the bound is under test: drop the grid, payload and consistency problems this minimal fixture has by design
    return [p for p in units.check_case(m, t) if "rel_std_pct" in p and "domain" in p]


def test_a_case_row_is_bounded_by_the_case_trap_count_in_every_place():
    assert _case_problems(819, 2446.8) == []
    assert _case_problems(100, 1100.0)
    p = _case_problems(100, 1100.0)
    # manifest row, final, history and feedback step
    assert len(p) == 4
    assert _case_problems(1, 0.1)
    assert _case_problems(0, 1000.0) == []
    assert _case_problems(0, 1100.0)
