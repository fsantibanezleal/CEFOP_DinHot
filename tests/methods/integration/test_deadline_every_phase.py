"""Every phase of every ladder method stops at the deadline of a time row (0.02.004, plan decision 2, unit U8a).

Each method runs on the reduced G6a record (G7 for the shaped-target methods) under a fake clock: ``time.perf_counter``
advances ``COST_S`` per forward or adjoint evaluation, so a 1 s row is 10 evaluations of work whatever the machine does. A method that honours the deadline in every phase does the 10 evaluations and at most the unit in progress; a method that
runs a phase to completion past the deadline does as much work as the same run with no time cap. The work is the engine's
forward plus adjoint evaluation counter (the number a benchmark row records), and the per-trap loop of M03, which the
counter cannot see, is counted at its call site.

Requirements: BM-009 (every phase of every method stops at its deadline), BM-010 (the true work is recorded),
BM-012 (a time row records what the method reaches in the wall clock it was given).
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from pipeline.benchmark import geometries as G
from pipeline.benchmark import protocol
from pipeline.model.holo.core import forward as F
from pipeline.model.holo.core.types import Budget
from pipeline.stages import infer

ROW_S = 1.0             # the time row under test
ITERATIONS = 12         # the reduced protocol's cap: what a time row would run without the deadline
COST_S = 0.1            # seconds one forward or adjoint evaluation takes on the work clock: the row is 10 evaluations of work
ROW_EVALS = round(ROW_S / COST_S)
OVERSHOOT = 8           # evaluations a method may do after the deadline: the unit in progress and the closing evaluation of its result
TICK = 0.4              # seconds the call clock advances per perf_counter call (M03's loop over the traps)
# a method whose forward and adjoint work is one fixed unit (no loop of evaluations to cut): the test then checks only that
# the work is unchanged; M03's loop over the traps is checked by its own test below
ONE_UNIT = {"M01", "M02", "M03"}


class WorkClock:
    """``time.perf_counter`` driven by the work: every forward or adjoint evaluation of the engine counter costs ``COST_S``,
    so a deadline of ``ROW_S`` passes after ``ROW_EVALS`` evaluations on any machine; a phase that does not check the
    deadline does all its evaluations after it."""

    def __init__(self):
        self.t, self.last = 1000.0, F.evaluations()

    def __call__(self):
        n = F.evaluations()
        if n < self.last:                       # the counter was reset by the runner
            self.last = n
        self.t += COST_S * (n - self.last) + 1e-6
        self.last = n
        return self.t


class CallClock:
    """``time.perf_counter`` that advances ``TICK`` seconds per call."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        self.t += TICK
        return self.t


@pytest.fixture(scope="module")
def real_registry():
    """The product's own method registry for this module (see ``tests/bake/test_benchmark_equal_time.py``)."""
    from pipeline.model.holo import methods

    previous = methods._base
    methods.reload(None)
    try:
        yield methods
    finally:
        methods.reload(None if previous == methods.__name__ else previous)


# The geometry each method runs on in the benchmark (its time-row cells in ``data/derived/benchmark/results.json``); M15, M16
# and M17 have no cell in it (the document lists them as skipped on every geometry), so they have no time row to bound.
GEOMETRY = {"M08": "G7", "M18": "G7", "M19": "G5"}
NO_TIME_ROW = ("M15", "M16", "M17")


def _geometry(mid: str) -> str:
    return GEOMETRY.get(mid, "G6a")


# iterations a time row runs for the methods whose unit of work is small at the reduced size
ITERATIONS_OF = {"M09": 60, "M19": 60}


def _run(mid, geometry, device, budget):
    rec = G.record(geometry, device=device, seed=0, reduced=True)
    ctx = infer.case_context(rec)
    return infer.run_method(rec, mid, budget=budget, ctx=ctx)


CASES = [(m, d) for m in protocol.LADDER if m not in NO_TIME_ROW for d in (False, True)]


@pytest.mark.parametrize("mid,device", CASES, ids=[f"{m}-{'device' if d else 'ideal'}" for m, d in CASES])
def test_a_time_row_does_a_bounded_amount_of_work(mid, device, real_registry, monkeypatch):
    geometry = _geometry(mid)
    if device and protocol.device_skip_reason(geometry):
        pytest.skip("no device cell for this geometry")
    n_it = ITERATIONS_OF.get(mid, ITERATIONS)
    full = _run(mid, geometry, device, Budget(n_it))
    ref = full.meta["forward_adjoint_evaluations"]
    monkeypatch.setattr(time, "perf_counter", WorkClock())
    capped = _run(mid, geometry, device, Budget(n_it, ROW_S))
    monkeypatch.undo()
    done = capped.meta["forward_adjoint_evaluations"]
    if mid in ONE_UNIT:
        assert done == ref
        return
    assert ref > ROW_EVALS + OVERSHOOT, f"{mid}: the uncapped run ({ref}) is too short to show a deadline"
    assert done <= ROW_EVALS + OVERSHOOT, (f"{mid} did {done} evaluations in a {ROW_EVALS}-evaluation row "
                                           f"(uncapped: {ref}); the deadline did not stop every phase")


def test_m03_stops_its_per_trap_loop_at_the_deadline(real_registry, monkeypatch):
    from pipeline.model.holo.methods.baseline import m03_random_mask as M03

    calls = {"n": 0}
    orig = M03.grating_phase

    def spy(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)

    monkeypatch.setattr(M03, "grating_phase", spy)
    n_traps = len(G.record("G6a", device=False, seed=0, reduced=True)["target"]["traps"])
    _run("M03", "G6a", False, Budget(ITERATIONS))
    assert calls["n"] == n_traps
    calls["n"] = 0
    monkeypatch.setattr(time, "perf_counter", CallClock())
    out = _run("M03", "G6a", False, Budget(ITERATIONS, ROW_S))
    monkeypatch.undo()
    assert 1 <= calls["n"] < n_traps
    assert np.all(np.isfinite(out.phi))


# ---- the line searches of the conjugate-gradient minimizer (M10, M13, B1, B4) ----------------------------------------------

@pytest.mark.parametrize("nonsmooth", [False, True], ids=["strong-wolfe", "staircase-ladder"])
def test_a_line_search_stops_at_the_deadline_inside_an_iteration(nonsmooth, monkeypatch):
    """``f = -sum(x)`` has a constant slope, so every search runs to its trial cap (25 strong-Wolfe trials, 11 doublings and 6
    halvings of the ladder): without a deadline in the search the first iteration alone does the whole cap past the deadline."""
    from pipeline.model.holo.methods.optim import _common as C

    calls = {"n": 0}
    now = {"t": 0.0}

    def fun(x):
        calls["n"] += 1
        now["t"] += COST_S
        return -float(np.sum(x)), -np.ones_like(x), None

    monkeypatch.setattr(time, "perf_counter", lambda: now["t"])
    deadline = C.deadline_of(ROW_S)
    res = C.cg_minimize(fun, np.zeros(4), 50, deadline=deadline, nonsmooth=nonsmooth)
    assert ROW_EVALS <= calls["n"] <= ROW_EVALS + 1          # every trial before the deadline, at most the one in flight after
    assert res.iterations <= 1 and np.all(np.isfinite(res.x))
    assert res.f <= 0.0                                      # the best trial so far, never a worse point


def test_cg_with_a_deadline_already_past_evaluates_nothing(monkeypatch):
    from pipeline.model.holo.methods.optim import _common as C

    calls = {"n": 0}

    def fun(x):
        calls["n"] += 1
        return float(np.sum(x**2)), 2 * x, None

    monkeypatch.setattr(time, "perf_counter", lambda: 5.0)
    res = C.cg_minimize(fun, np.ones(3), 10, deadline=4.0)
    assert calls["n"] == 0 and res.iterations == 0 and np.array_equal(res.x, np.ones(3))
