"""The benchmark protocol on the reduced grid (64 pixels, 2 seeds, a handful of iterations), with the planted methods. The
release run is the same code at 256/512/128 pixels and 20 seeds (not run in tests: ADR-0074)."""
from __future__ import annotations

import json

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))

import contract_schemas as cs  # noqa: E402

from bakefix import Planted  # noqa: F401
from pipeline.benchmark import geometries as G
from pipeline.benchmark import protocol
from pipeline.core import units


@pytest.fixture(scope="module")
def bench(tmp_path_factory):
    root = tmp_path_factory.mktemp("bench")
    with Planted(root / "pl", ("M02", "M04", "M05", "M08"), "benchpkg") as p:
        out = root / "out"
        doc = protocol.run(out, seeds=2, workers=1, reduced=True, geometries=["G1", "G5", "G7"],
                           methods=["M02", "M04", "M05", "M08", "M19"])
        yield out, doc, p


def test_results_validate_and_are_in_units(bench):
    out, doc, _ = bench
    assert cs.errors("benchmark-results", doc) == []
    assert units.check_benchmark(doc) == []
    assert json.loads((out / "benchmark" / "results.json").read_text(encoding="utf-8")) == doc
    assert doc["protocol"]["seeds"] == 2 and doc["protocol"]["budgets"]["iterations"] == [2, 4, 8]


def test_every_budget_kind_is_reported_per_group(bench):
    _, doc, _ = bench
    rows = [r for r in doc["rows"] if (r["method"], r["geometry"], r["device"], r["params"]) == ("M04", "G1", "ideal", "default")]
    kinds = sorted((r["budget_kind"], r["budget"]) for r in rows)
    assert kinds == sorted([("iterations", 2), ("iterations", 4), ("iterations", 8), ("time", 0.05), ("time", 0.2),
                            ("converged", 12.0)])
    assert all(r["n_seeds"] == 2 for r in rows)
    its = {r["budget"]: r["iterations"]["median"] for r in rows if r["budget_kind"] == "iterations"}
    assert its[2] <= its[4] <= its[8]


def test_cells_that_cannot_run_are_listed_with_a_reason_and_absent_from_rows(bench):
    _, doc, _ = bench
    skipped = {(s["method"], s["geometry"]): s["reason"]["en"] for s in doc["skipped"]}
    assert "not registered" in skipped[("M19", "G1")] and "not registered" in skipped[("M19", "G7")]
    assert "does not accept a field target" not in skipped.get(("M08", "G7"), "")
    assert ("M04", "G7") in skipped and ("M02", "G7") in skipped and ("M08", "G1") in skipped
    # a multi-plane geometry has no device rows (the protocol text says why) and is not a skipped cell
    assert ("M04", "G5") not in skipped
    assert not [r for r in doc["rows"] if r["geometry"] == "G5" and r["device"] == "device"]
    rows = {(r["method"], r["geometry"], r["device"]) for r in doc["rows"]}
    assert ("M04", "G5", "device") not in rows and ("M04", "G5", "ideal") in rows
    assert not any(m == "M19" for m, _, _ in rows)
    assert all(s["reason"]["es"] for s in doc["skipped"])


def test_adversarial_tuned_and_default_rows_never_mix_parameters(bench):
    """Must refute: one method's tuned parameters shown as another's defaults, or tuned rows without the field saying so."""
    _, doc, _ = bench
    tuned = {r["method"] for r in doc["rows"] if r["params"] == "tuned"}
    assert tuned == {"M05"}                      # only the method with a tuning grid has tuned rows
    d = next(r for r in doc["rows"] if (r["method"], r["geometry"], r["device"], r["budget_kind"], r["budget"], r["params"]) ==
             ("M05", "G1", "ideal", "converged", 12.0, "default"))
    t = next(r for r in doc["rows"] if (r["method"], r["geometry"], r["device"], r["budget_kind"], r["budget"], r["params"]) ==
             ("M05", "G1", "ideal", "converged", 12.0, "tuned"))
    assert t["rel_std_pct"]["median"] < d["rel_std_pct"]["median"]       # gamma 1.0 beats the default 0.5 in the planted method


def test_tuning_uses_the_same_number_of_runs_for_every_method(bench):
    _, _, _ = bench
    assert protocol.TUNING_CANDIDATES * protocol.TUNING_SEEDS == 12
    assert protocol.tuning_grid("M04") is None and len(protocol.tuning_grid("M05")) == protocol.TUNING_CANDIDATES
    best = protocol.tune("M05", "G1", False, True)
    assert best["gamma"] > 0.5


def test_resume_skips_finished_groups(bench):
    out, doc, p = bench
    before = (out / "benchmark" / "results.json").read_bytes()
    again = protocol.run(out, seeds=2, workers=1, reduced=True, geometries=["G1", "G5", "G7"],
                         methods=["M02", "M04", "M05", "M08", "M19"], resume=True)
    assert len(again["rows"]) == len(doc["rows"])
    assert (out / "benchmark" / "results.json").read_bytes() == before or again["rows"] == doc["rows"]


def test_pool_workers_give_the_same_rows(bench, tmp_path):
    _, doc, p = bench
    out = tmp_path / "pool"
    pooled = protocol.run(out, seeds=2, workers=2, reduced=True, geometries=["G1"], methods=["M02", "M04"],
                          base_package=p.base, sys_path=[p.path])
    keep = [r for r in doc["rows"] if r["geometry"] == "G1" and r["method"] in ("M02", "M04")]

    def strip(rows):
        # a wall-clock-capped row performs as many iterations as the machine's load allows, so only the deterministic rows
        # (fixed iteration counts and the converged cap) are compared
        return [{k: v for k, v in r.items() if k != "time_s"} for r in rows if r["budget_kind"] != "time"]

    assert strip(pooled["rows"]) == strip(keep)


def test_geometries_are_valid_records_and_in_units():
    from pipeline.io.contract import validate_records

    for g in G.GEOMETRIES:
        for reduced in (True, False):
            rec = G.record(g, device=False, seed=0, reduced=reduced)
            rep = validate_records([{**rec, "case_id": "C99_bm"}])
            assert rep.ok, (g, reduced, rep.rejected)
    assert G.n_traps("G1", False) == 100 and G.n_traps("G6", False) == 1024 and G.n_traps("G4", False) == 119
    assert G.n_traps("G5", False) == 75 and G.n_traps("G2", False) == 36 and G.n_traps("G3", False) == 100
    assert {G.record("G7", device=False, seed=s)["target"]["shape"] for s in range(4)} == {"ring", "disc", "line", "lg_ring"}
    assert G.unit_um(256) == pytest.approx(G.unit_um(512)) and G.unit_um(256) == pytest.approx(0.996, abs=1e-3)



def test_a_method_that_refuses_a_geometry_is_skipped_with_its_reason(tmp_path, monkeypatch):
    """A ValueError of the method is a refusal: the cell is listed in skipped with the method's message, no row of it is kept,
    and the other methods' cells still run (the run does not stop)."""
    orig = protocol.infer.run_method

    def refusing(rec, mid, *a, **k):
        if mid == "M04":
            raise ValueError("planted: the fft form needs traps on FFT bins")
        return orig(rec, mid, *a, **k)

    with Planted(tmp_path / "pl", ("M02", "M04"), "refusepkg"):
        monkeypatch.setattr(protocol.infer, "run_method", refusing)
        doc = protocol.run(tmp_path / "out", seeds=2, workers=1, reduced=True, geometries=["G1"], methods=["M02", "M04"])
    assert cs.errors("benchmark-results", doc) == []
    skipped = {(s["method"], s["geometry"]): s["reason"] for s in doc.get("skipped", [])}
    assert "planted: the fft form needs traps on FFT bins" in skipped[("M04", "G1")]["en"]
    assert skipped[("M04", "G1")]["es"].startswith("El método rechaza esta geometría")
    assert not [r for r in doc["rows"] if r["method"] == "M04"]
    assert [r for r in doc["rows"] if r["method"] == "M02" and r["geometry"] == "G1"]


def test_an_error_that_is_not_a_refusal_stops_the_run(tmp_path, monkeypatch):
    def broken(rec, mid, *a, **k):
        raise RuntimeError("planted bug")

    with Planted(tmp_path / "pl", ("M02",), "brokenpkg"):
        monkeypatch.setattr(protocol.infer, "run_method", broken)
        with pytest.raises(RuntimeError, match="planted bug"):
            protocol.run(tmp_path / "out", seeds=2, workers=1, reduced=True, geometries=["G1"], methods=["M02"])


def test_b5_front_is_stored_as_its_non_dominated_points():
    """B5 returns its front as rows of (e, u, sigma) with the indices of the non-dominated ones: the cell keeps those points."""
    import numpy as np

    meta = {"lambdas": [0.0, 0.5, 1.0], "front": np.array([[0.79, 1.0, 0.1], [0.80, 0.5, 9.0], [0.83, 0.09, 40.0]]),
            "pareto": np.array([2, 0])}
    assert protocol.pareto_points(meta) == [{"lambda": 0.0, "efficiency": 0.79, "uniformity": 1.0},
                                            {"lambda": 1.0, "efficiency": 0.83, "uniformity": 0.09}]
    assert protocol.pareto_points({"pareto": []}) is None and protocol.pareto_points({}) is None


def test_the_real_b5_runs_through_the_protocol_and_its_front_validates(tmp_path):
    """Must refute: a B5 group that stops the run (the release run of 2026-10-29 stopped on it after four hours). The module's
    fixture keeps a planted registry active, so the product's own registry is loaded for this test and the previous one restored."""
    from pipeline.model.holo import methods

    previous = methods._base
    methods.reload(None)
    try:
        doc = protocol.run(tmp_path / "out", seeds=2, workers=1, reduced=True, geometries=["G1"], methods=["B5"])
    finally:
        methods.reload(None if previous == methods.__name__ else previous)
    assert cs.errors("benchmark-results", doc) == []
    assert [r for r in doc["rows"] if r["method"] == "B5" and r["geometry"] == "G1"]
    front = doc["pareto"]
    assert front, doc["pareto"]
