"""Stage 4, infer: run every method valid for a case through the registry and score it independently.

A method is a module of ``pipeline.model.holo.methods`` exposing ``SPEC`` and
``run(setup, target, *, device=None, budget, rng, init=None) -> Result`` (``core/types.py``). Every method of a case is
given the same seed (``Rng(seed)``), so all of them start from the same random numbers, and the same budget. The verdict
of the bake is recomputed from the returned phase by ``core/score.py``; the history the method reports is the curve the
replay shows. A method that declares an ``aberration`` parameter is given the case's aberration (Noll coefficients in
waves, index 0 = piston); the others are scored through the aberrated system without knowing it.

Failures are data: a method that is not registered, whose spec does not accept the case's target, or that raises, becomes
a ``MethodFailure`` (never a silent omission); ``pipeline.py`` decides whether the bake continues.
"""
from __future__ import annotations

import inspect
import time

import numpy as np

from ..cases import build
from ..core import score as scoring
from ..core.gate import method_lane
from ..io.schema import MethodFailure, MethodOutcome
from ..model.holo import methods as registry
from ..model.holo.core.rng import Rng
from ..model.holo.core.types import Budget

CONVERGE_WINDOW = 5
CONVERGE_TOL_PCT = 0.1


def registered(ids: list[str]) -> tuple[list[str], list[str]]:
    """``(registered, unregistered)`` among ``ids``, in the given order."""
    known = {s.id for s in registry.all_specs()}
    return [i for i in ids if i in known], [i for i in ids if i not in known]


def spec_problem(spec, rec: dict) -> str | None:
    """Why ``spec`` cannot take the record's target (None when it can)."""
    kind = "traps" if rec["target"]["kind"] == "traps" else "field"
    if kind not in spec.targets:
        return f"method {spec.id} does not accept a {kind} target (spec targets: {list(spec.targets)})"
    if build.is_3d(rec) and 3 not in spec.dims:
        return f"method {spec.id} is 2D only; the case has traps off the focal plane"
    return None


def _converged(history: list[dict], meta: dict) -> bool:
    if isinstance(meta.get("converged"), bool):
        return meta["converged"]
    if len(history) <= CONVERGE_WINDOW:
        return len(history) <= 1
    return abs(history[-1]["rel_std"] - history[-1 - CONVERGE_WINDOW]["rel_std"]) < CONVERGE_TOL_PCT


def _accepted(run, extra: dict) -> dict:
    params = inspect.signature(run).parameters
    return {k: v for k, v in extra.items() if k in params}


def run_method(rec: dict, mid: str, *, budget: Budget | None = None, init: np.ndarray | None = None,
               target=None, extra: dict | None = None, ctx: dict | None = None) -> MethodOutcome:
    """Run one registered method on the record's case and score it. Raises whatever the method raises."""
    method = registry.get(mid)
    ctx = ctx or case_context(rec)
    problem = spec_problem(method.spec, rec)
    if problem:
        raise ValueError(problem)
    b = budget or Budget(rec["budget"]["iterations"], rec["budget"]["time_s"])
    kwargs = {"device": ctx["device"], "budget": b, "rng": Rng(rec["seed"]), "init": init}
    if rec["aberration"] is not None:
        kwargs.update(_accepted(method.run, {"aberration": build.aberration_coeffs(rec)}))
    if extra:
        kwargs.update(extra)
    t0 = time.perf_counter()
    result = method.run(ctx["setup"], target if target is not None else ctx["target"], **kwargs)
    seconds = time.perf_counter() - t0
    if result.phi.shape != (ctx["setup"].n_pix,) * 2:
        raise ValueError(f"method {mid} returned a phase of shape {result.phi.shape}")
    final = scoring.score(rec, result.phi, setup=ctx["setup"], device=ctx["device"],
                          shape_and_region=ctx["shape_region"])
    hist = list(result.history)
    its = result.meta.get("iterations")
    if not isinstance(its, int) or isinstance(its, bool):
        its = int(hist[-1]["iteration"]) if hist else 0
    return MethodOutcome(mid, method.spec.lane, result.phi, hist, final, its, _converged(hist, result.meta), seconds,
                         dict(result.meta))


def case_context(rec: dict) -> dict:
    """The engine objects of a record, built once per case."""
    setup = build.setup_of(rec)
    target = build.target_of(rec)
    shaped = None if rec["target"]["kind"] == "traps" else (build.shape_mask(rec), target.mask)
    return {"setup": setup, "device": build.device_of(rec), "target": target, "shape_region": shaped}


def run_case(rec: dict, ids: list[str], ctx: dict | None = None) -> tuple[dict[str, MethodOutcome], list[MethodFailure]]:
    """Run ``ids`` (all registered) on the case; the outcomes of those that ran and the failures of those that raised."""
    ctx = ctx or case_context(rec)
    outcomes: dict[str, MethodOutcome] = {}
    failures: list[MethodFailure] = []
    for mid in ids:
        try:
            outcomes[mid] = run_method(rec, mid, ctx=ctx)
        except Exception as exc:  # noqa: BLE001 - any method failure is recorded with its type and message
            failures.append(MethodFailure(mid, f"{type(exc).__name__}: {exc}"))
    return outcomes, failures


def lane_of(spec_lane: str, seconds: float) -> str:
    return method_lane(spec_lane, seconds * 1000.0)


def time_again(rec: dict, mid: str, ctx: dict, repeats: int = 1) -> float:
    """Seconds of ``repeats`` further runs of a method (the best of them): the first run of a bake carries import and cache
    effects, the lane gate judges a warm run."""
    best = float("inf")
    for _ in range(repeats):
        best = min(best, run_method(rec, mid, ctx=ctx).seconds)
    return best
