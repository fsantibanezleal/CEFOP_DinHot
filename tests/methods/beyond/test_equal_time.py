"""Equal work (0.02.004, plan decision 2): every phase of the weighted-GS warm start, B1, B2 and B5 stops at its deadline,
and a run records the work it did (inner iterations and forward plus adjoint evaluations), counted here independently of the
engine's counter by spying on the transforms at their call sites.

Requirements: BM-008 (deadline in weighted_gs), BM-009 (deadline in every phase of B1, B2, B5),
BM-010 (true iteration and evaluation counts).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "optim"))
from e3_helpers import bin_grid, make_setup  # noqa: E402

from pipeline.model.holo.core import forward as F  # noqa: E402
from pipeline.model.holo.core.device import Device  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.beyond import b1_device_wgs as B1  # noqa: E402
from pipeline.model.holo.methods.beyond import b2_flicker_bounded as B2  # noqa: E402
from pipeline.model.holo.methods.beyond import b5_pareto as B5  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402

RAW = ("point_trap_projection", "point_trap_backproject", "fft_focal_field", "fft_inverse")
DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)


class Spy:
    """Counts the calls of the four transforms of ``core/forward.py`` and of the crosstalk model at every module that imported
    them (an independent count: it does not read the engine's counter)."""

    def __init__(self, monkeypatch):
        self.calls = 0
        spy = self

        def wrap(fn):
            def inner(*a, **k):
                spy.calls += 1
                return fn(*a, **k)
            return inner

        for name in RAW:
            orig = getattr(F, name)
            wrapped = wrap(orig)
            for mod in list(sys.modules.values()):
                if mod is not None and getattr(mod, "__name__", "").startswith("pipeline") and getattr(mod, name, None) is orig:
                    monkeypatch.setattr(mod, name, wrapped)
        # the crosstalk model does not go through the transforms of core/forward.py: its two directions are one call each
        fwd_o, adj_o = C.FocalForward.forward, C.FocalForward.adjoint

        def fwd(self, phi):
            if self.device is not None and self.device.crosstalk is not None:
                spy.calls += 1
            return fwd_o(self, phi)

        def adj(self, g, cache):
            if self.device is not None and self.device.crosstalk is not None:
                spy.calls += 1
            return adj_o(self, g, cache)

        monkeypatch.setattr(C.FocalForward, "forward", fwd)
        monkeypatch.setattr(C.FocalForward, "adjoint", adj)


def counted(fn):
    F.reset_evaluations()
    out = fn()
    return out, F.evaluations()


# ---------------------------------------------------------------------------------------------------- the counter

def test_counter_counts_each_transform_once_and_resets():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    F.reset_evaluations()
    assert F.evaluations() == 0
    phi, _ = G.weighted_gs(s, traps, 2, Rng(1), variant="gsw")
    assert F.evaluations() > 0
    F.reset_evaluations()
    assert F.evaluations() == 0
    F.point_trap_fields(phi, s, traps)
    F.fft_inverse(F.fft_focal_field(phi, s), s)
    assert F.evaluations() == 3


def test_weighted_gs_evaluations_equal_the_independent_count(monkeypatch):
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    spy = Spy(monkeypatch)
    (phi, hist), n = counted(lambda: G.weighted_gs(s, traps, 5, Rng(1), variant="pfwgs"))
    assert len(hist) == 5
    assert n == spy.calls and n >= 2 * 5          # one adjoint and one forward per iteration, plus the start


# ---------------------------------------------------------------------------------------------------- weighted_gs deadline

def test_weighted_gs_stops_at_its_deadline_with_its_true_iteration_count():
    s = make_setup(64)
    traps = bin_grid(s, 6, 6, 6)
    t0 = time.perf_counter()
    full = G.weighted_gs(s, traps, 3, Rng(1), variant="gsw")
    per_it = (time.perf_counter() - t0) / 3
    budget_s = max(0.05, 20 * per_it)
    start = time.perf_counter()
    phi, hist = G.weighted_gs(s, traps, 100000, Rng(1), variant="gsw", deadline=C.deadline_of(budget_s))
    took = time.perf_counter() - start
    assert 1 <= len(hist) < 100000
    assert hist[-1]["iteration"] == len(hist)
    assert took <= budget_s + 5 * per_it + 0.05          # never more than about one iteration past the deadline
    assert phi.shape == full[0].shape


def test_weighted_gs_with_an_expired_deadline_returns_one_iteration_and_never_raises():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    phi, hist = G.weighted_gs(s, traps, 50, Rng(1), variant="pfwgs", deadline=time.perf_counter() - 1.0)
    assert len(hist) == 1


def test_weighted_gs_without_a_deadline_is_unchanged():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    a, ha = G.weighted_gs(s, traps, 6, Rng(3), variant="gsw")
    b, hb = G.weighted_gs(s, traps, 6, Rng(3), variant="gsw", deadline=None)
    assert (a == b).all() and len(ha) == len(hb) == 6


# ---------------------------------------------------------------------------------------------------- B2

def test_b2_records_its_true_iterations_and_evaluations(monkeypatch):
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    spy = Spy(monkeypatch)
    res, n = counted(lambda: B2.run(s, Target.from_traps(traps), budget=Budget(5), rng=Rng(1), frames=4, frame_iterations=3))
    # frame 0 runs 5 iterations, three more frames run 3 iterations each
    assert res.meta["iterations"] == 5 + 3 * 3
    assert res.meta["n_frames"] == 4
    assert n == spy.calls


def test_b2_stops_every_phase_at_its_deadline():
    s = make_setup(64)
    traps = bin_grid(s, 6, 6, 6)
    t0 = time.perf_counter()
    B2.run(s, Target.from_traps(traps), budget=Budget(4), rng=Rng(1), frames=3, frame_iterations=2)
    per_it = (time.perf_counter() - t0) / (4 + 2 * 2)
    budget_s = max(0.05, 10 * per_it)
    t_run = time.perf_counter()
    res = B2.run(s, Target.from_traps(traps), budget=Budget(100000, budget_s), rng=Rng(1))
    took = time.perf_counter() - t_run
    assert res.meta["iterations"] < 100000
    assert res.meta["iterations"] >= 1
    # the iterations stop at the deadline; what follows is the transient model of the frames, a small fixed cost
    t_model = time.perf_counter()
    B2.transient_min_ratio(s, [res.phi] * 2, lambda x: traps)
    assert took <= budget_s + 5 * per_it + 3 * (time.perf_counter() - t_model) + 0.1


# ---------------------------------------------------------------------------------------------------- B1

def test_b1_records_warm_plus_cg_iterations_and_independent_evaluations(monkeypatch):
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    spy = Spy(monkeypatch)
    res, n = counted(lambda: B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(2), rng=Rng(1), warm=3, steps=2))
    assert 3 + 1 <= res.meta["iterations"] <= 3 + 2 * 2
    assert n == spy.calls


def test_b1_stops_warm_start_and_cg_at_its_deadline_and_keeps_the_best_iterate():
    s = make_setup(64)
    traps = bin_grid(s, 6, 6, 6)
    t0 = time.perf_counter()
    B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(1), rng=Rng(1), warm=2, steps=1)
    t_small = time.perf_counter() - t0
    budget_s = t_small / 3
    start = time.perf_counter()
    res = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(100000, budget_s), rng=Rng(1), warm=12, steps=3)
    took = time.perf_counter() - start
    assert took <= budget_s + t_small           # the longest unit between two checks is one evaluation of the device model
    assert res.meta["iterations"] >= 1
    assert res.meta["best_iteration"] >= 0 and res.phi.shape == (64, 64)


def test_b1_deadline_inside_the_warm_start_returns_the_warm_iterate():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    res = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(10, 1e-9), rng=Rng(1), warm=40, steps=3)
    assert res.meta["iterations"] <= 3
    assert res.meta["best_iteration"] == 0


def test_b1_without_a_time_budget_keeps_its_results():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    a = B1.run(s, Target.from_traps(traps), device=None, budget=Budget(2), rng=Rng(5), warm=3, steps=2)
    b = B1.run(s, Target.from_traps(traps), device=None, budget=Budget(2), rng=Rng(5), warm=3, steps=2)
    assert (a.phi == b.phi).all() and len(a.history) == 2


# ---------------------------------------------------------------------------------------------------- B5

def test_b5_records_warm_plus_cg_iterations_and_independent_evaluations(monkeypatch):
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    spy = Spy(monkeypatch)
    res, n = counted(lambda: B5.run(s, Target.from_traps(traps), budget=Budget(3), rng=Rng(1), n_lambda=3, warm=4))
    assert 4 + 3 <= res.meta["iterations"] <= 4 + 3 * 3
    assert n == spy.calls


def test_b5_stops_warm_start_and_every_lambda_at_its_deadline():
    s = make_setup(64)
    traps = bin_grid(s, 6, 6, 6)
    t0 = time.perf_counter()
    B5.run(s, Target.from_traps(traps), budget=Budget(1), rng=Rng(1), n_lambda=2, warm=2)
    t_small = time.perf_counter() - t0
    budget_s = t_small
    start = time.perf_counter()
    res = B5.run(s, Target.from_traps(traps), budget=Budget(100000, budget_s), rng=Rng(1))
    took = time.perf_counter() - start
    assert took <= budget_s + t_small
    assert len(res.meta["lambdas"]) >= 1 and res.meta["iterations"] >= 1


def test_b5_deadline_inside_the_warm_start_still_returns_a_point():
    s = make_setup(32)
    traps = bin_grid(s, 3, 3, 6)
    res = B5.run(s, Target.from_traps(traps), budget=Budget(10, 1e-9), rng=Rng(1), n_lambda=5, warm=30)
    assert len(res.meta["lambdas"]) == 1 and res.meta["iterations"] <= 3
