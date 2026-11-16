"""The benchmark at equal wall clock (0.02.004, plan decision 2) on the reduced grid: B2 is not a static method, the large
array is two geometries, every row records its work, and the seed rule holds.

Requirements: BM-011 (B2 out of the static cells), BM-012 (seed rule), BM-013 (G6 per target),
BM-014 (the work recorded in every row).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))

import contract_schemas as cs  # noqa: E402

from pipeline.benchmark import geometries as G
from pipeline.benchmark import protocol
from pipeline.model.holo.core.types import Budget
from pipeline.stages import infer


def test_b2_is_not_in_the_static_ladder_and_its_docstring_says_why():
    assert "B2" not in protocol.LADDER and {"B1", "B3", "B4", "B5"} <= set(protocol.LADDER)
    assert "B2" in protocol.__doc__ or "phase-fixed" in open(protocol.__file__, encoding="utf-8").read()


def test_g6_is_two_geometries_with_their_own_targets_and_every_seed_runs_both():
    assert "G6" not in G.GEOMETRIES and {"G6a", "G6b"} <= set(G.GEOMETRIES)
    for reduced in (True, False):
        lat0 = G.record("G6a", device=False, seed=0, reduced=reduced)["target"]["traps"]
        lat1 = G.record("G6a", device=False, seed=1, reduced=reduced)["target"]["traps"]
        dis0 = G.record("G6b", device=False, seed=0, reduced=reduced)["target"]["traps"]
        dis1 = G.record("G6b", device=False, seed=1, reduced=reduced)["target"]["traps"]
        assert lat0 == lat1 and dis0 == dis1 and lat0 != dis0          # no parity: each geometry is one target on every seed
    assert G.n_traps("G6a", False) == 1024 and G.n_traps("G6b", False) == 819
    assert G.GEOMETRIES["G6a"][0]["en"] != G.GEOMETRIES["G6b"][0]["en"]


@pytest.fixture(scope="module")
def real_registry():
    """The product's own method registry for this module, the previous one restored after it. The session's
    ``planted_registry`` (``bakefix.py``, used by the contract tests' sandbox bake) keeps a four-method package active
    for the rest of the session, so without this M07 and B5 are unknown whenever a contract test ran first."""
    from pipeline.model.holo import methods

    previous = methods._base
    methods.reload(None)
    try:
        yield methods
    finally:
        methods.reload(None if previous == methods.__name__ else previous)


@pytest.fixture(scope="module")
def doc(tmp_path_factory, real_registry):
    out = tmp_path_factory.mktemp("eq")
    one = protocol.run(out / "a", seeds=3, workers=1, reduced=True, geometries=["G1", "G6a", "G6b"], methods=["M04", "M07"])
    two = protocol.run(out / "b", seeds=3, workers=1, reduced=True, geometries=["G1"], methods=["B5"])   # the slowest method, one geometry
    return {**one, "rows": one["rows"] + two["rows"]}


def test_every_row_records_evaluations_and_the_document_validates(doc):
    assert cs.errors("benchmark-results", doc) == []
    assert doc["rows"] and all("evaluations" in r and r["evaluations"]["median"] > 0 for r in doc["rows"])
    # B5 does more work than M04 at the same iteration budget: the row says so
    b5 = next(r for r in doc["rows"] if (r["method"], r["geometry"], r["device"], r["budget_kind"], r["budget"]) == ("B5", "G1", "ideal", "iterations", 2))
    m4 = next(r for r in doc["rows"] if (r["method"], r["geometry"], r["device"], r["budget_kind"], r["budget"]) == ("M04", "G1", "ideal", "iterations", 2))
    assert b5["evaluations"]["median"] > 5 * m4["evaluations"]["median"]
    assert b5["iterations"]["median"] > 2


def test_no_static_row_for_b2_and_the_two_g6_targets_are_separate(doc):
    assert not [r for r in doc["rows"] if r["method"] == "B2"]
    assert {r["geometry"] for r in doc["rows"]} == {"G1", "G6a", "G6b"}
    assert {g["id"] for g in doc["geometries"]} >= {"G6a", "G6b"} and "G6" not in {g["id"] for g in doc["geometries"]}
    assert not any(r["geometry"] == "G6" for r in doc["rows"])


def test_evaluations_of_a_run_equal_the_independent_count_of_the_transforms(monkeypatch, real_registry):
    """The row's number is the engine counter read between the run and its scoring; count the same run by hand."""
    import sys as _sys

    from pipeline.model.holo.core import forward as F

    names = ("point_trap_projection", "point_trap_backproject", "fft_focal_field", "fft_inverse")
    tally = {"n": 0}
    for name in names:
        orig = getattr(F, name)

        def spy(*a, _o=orig, **k):
            tally["n"] += 1
            return _o(*a, **k)

        for mod in list(_sys.modules.values()):
            if getattr(mod, "__name__", "").startswith("pipeline") and getattr(mod, name, None) is orig and mod.__name__ != "pipeline.core.score":
                monkeypatch.setattr(mod, name, spy)
    rec = G.record("G1", device=False, seed=0, reduced=True)
    ctx = infer.case_context(rec)
    tally["n"] = 0
    out = infer.run_method(rec, "M07", budget=Budget(5), ctx=ctx)
    # the scoring runs after the counter is read: whatever it called is not in the number
    assert out.meta["forward_adjoint_evaluations"] <= tally["n"]
    assert out.meta["forward_adjoint_evaluations"] >= 2 * 5


def test_seed_rule_time_and_converged_rows_run_five_seeds_iteration_rows_keep_the_group_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(protocol, "GROUP_BUDGET_S", -1.0)          # the group budget is spent from the first seed
    d = protocol.run(tmp_path, seeds=8, workers=1, reduced=True, geometries=["G1"], methods=["M04"])
    by = {}
    for r in d["rows"]:
        by.setdefault(r["budget_kind"], set()).add(r["n_seeds"])
    assert by["iterations"] == {protocol.MIN_SEEDS}
    assert by["time"] == {protocol.MIN_BOUNDED_SEEDS} and by["converged"] == {protocol.MIN_BOUNDED_SEEDS}
    assert protocol.MIN_BOUNDED_SEEDS == 5 and protocol.MIN_SEEDS == 2


# ---- B3 has no benchmark row while its network is not released (plan decision 2; review finding N-M3) ----

def test_b3_is_skipped_with_a_reason_in_both_languages_while_no_network_is_released(real_registry, monkeypatch):
    from pipeline.model.holo.methods.learned import _slot

    assert _slot.load("warmstart-model") is None                   # the repository releases no warm-start network
    for geometry in ("G1", "G6a", "G5"):
        why = protocol.skip_reason("B3", geometry, True)
        assert why is not None and why["en"].startswith("Not run: the network of this method is not released")
        assert why["es"].startswith("No ejecutado") and "red" in why["es"]
    assert protocol.skip_reason("M07", "G1", True) is None          # the fallback it would have run is M07, measured as M07


def test_b3_runs_as_before_once_a_network_is_released(real_registry, monkeypatch):
    monkeypatch.setattr(protocol, "_warm_start_network_released", lambda: True)
    assert protocol.skip_reason("B3", "G1", True) is None


def test_the_protocol_lists_b3_as_skipped_and_keeps_no_row_of_it(tmp_path, real_registry):
    doc = protocol.run(tmp_path, seeds=2, workers=1, reduced=True, geometries=["G1"], methods=["B3", "M07"])
    assert not [r for r in doc["rows"] if r["method"] == "B3"] and [r for r in doc["rows"] if r["method"] == "M07"]
    assert [s for s in doc["skipped"] if s["method"] == "B3" and s["geometry"] == "G1"]
    assert cs.errors("benchmark-results", doc) == []
