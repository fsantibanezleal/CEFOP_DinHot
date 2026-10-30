"""B5 efficiency-uniformity Pareto front by continuation.

Acceptance (SDD): hypervolume at least that of the M04, M05, M09 and M06 points on the 10x10 task, plus (dossier D5.1)
at least one front point dominating each of GS (M04) and GAA (M05) and a front in under 60 s. The baseline points come
from this unit's ``_gs_family`` (GS, GAA with alpha 0.5, GSW; 30 iterations each, the dossier's table) and M09 itself
(one sweep, default parameters), all from the same seed and scored by the same metrics; E2's modules replace them in
the merged re-run. Seeds: 1 (benchmark: 20).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "optim"))
from e3_helpers import bin_grid, make_setup, task_10x10, trap_stats  # noqa: E402

from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.beyond import b5_pareto as B5  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402
from pipeline.model.holo.methods.optim import m09_direct_search as M09  # noqa: E402


def test_spec():
    assert B5.SPEC.id == "B5" and B5.SPEC.targets == ("traps",)


def test_hypervolume_known_values():
    assert B5.hypervolume(np.array([[0.5, 0.5]])) == pytest.approx(0.25)
    assert B5.hypervolume(np.array([[1.0, 0.2], [0.4, 0.9]])) == pytest.approx(0.2 * 0.6 + 0.9 * 0.4)
    assert B5.hypervolume(np.array([[0.5, 0.5], [0.3, 0.3]])) == pytest.approx(0.25)      # dominated point adds nothing
    assert B5.hypervolume(np.zeros((0, 2))) == 0.0
    assert B5.hypervolume(np.array([[0.5, 0.5]]), ref=(0.2, 0.2)) == pytest.approx(0.09)


def test_pareto_indices():
    pts = np.array([[0.9, 0.2], [0.5, 0.5], [0.4, 0.4], [0.2, 0.9], [0.5, 0.5]])
    assert B5.pareto_indices(pts) == [0, 1, 3, 4]       # equal points do not dominate each other; (0.4, 0.4) does


def test_front_gradient_matches_finite_differences():
    s = make_setup(16)
    traps = bin_grid(s, 3, 3, 4)
    cost = B5._FrontCost(s, traps, 0.6)
    phi = Rng(2).phases(256).reshape(16, 16)
    from e3_helpers import check_finite_difference
    for lam in (0.0, 0.4, 1.0):
        cost.lam = lam
        assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(3), n_dirs=5) <= 1e-5


def test_front_is_monotone_in_the_tradeoff_on_a_small_array():
    s = make_setup(64)
    traps = bin_grid(s, 4, 4, 8)
    res = B5.run(s, Target.from_traps(traps), budget=Budget(10), rng=Rng(2), n_lambda=6)
    f = res.meta["front"]
    assert f[-1, 0] >= f[0, 0] - 1e-9 and f[-1, 1] < f[0, 1]       # efficiency rises, uniformity falls
    assert len(res.history) == 6 and res.meta["hypervolume"] > 0
    assert res.phi.shape == (64, 64)


def test_field_target_is_refused():
    s = make_setup(16)
    with pytest.raises(ValueError, match="traps"):
        B5.run(s, Target.from_field(np.ones((32, 32)), np.ones((32, 32), dtype=bool)), budget=Budget(1), rng=Rng(1))


def test_deterministic_for_a_seed():
    s = make_setup(32)
    traps = bin_grid(s, 2, 2, 8)
    a = B5.run(s, Target.from_traps(traps), budget=Budget(4), rng=Rng(5), n_lambda=3)
    b = B5.run(s, Target.from_traps(traps), budget=Budget(4), rng=Rng(5), n_lambda=3)
    assert np.array_equal(a.phi, b.phi) and a.meta["hypervolume"] == b.meta["hypervolume"]


def test_acceptance_hypervolume_and_domination_on_the_10x10_task():
    s = make_setup(256)
    traps = task_10x10(s)
    base = {}
    for name, variant in (("M04", "gs"), ("M05", "gaa"), ("M06", "gsw")):
        phi, _ = G.weighted_gs(s, traps, 30, Rng(1), variant=variant)
        base[name] = trap_stats(phi, s, traps)[:2]
    ds = M09.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(1))
    base["M09"] = trap_stats(ds.phi, s, traps)[:2]
    t0 = time.perf_counter()
    res = B5.run(s, Target.from_traps(traps), budget=Budget(15), rng=Rng(1))
    elapsed = time.perf_counter() - t0
    front = res.meta["front"][:, :2]
    hv_base = B5.hypervolume(np.array(list(base.values())))
    assert res.meta["hypervolume"] >= hv_base, (res.meta["hypervolume"], hv_base, base)
    for name in ("M04", "M05"):
        e, u = base[name]
        assert np.any((front[:, 0] >= e) & (front[:, 1] > u)), (name, base[name], front)
    assert elapsed < 60.0, elapsed
