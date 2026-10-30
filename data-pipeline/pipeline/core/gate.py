"""The measured lane gate (ADR-0054). A case may be re-run LIVE in the browser iff its engine is light (pure Python
with wheels in a small allowed set, a proxy for an engine small enough to port or to run client side) AND one run of its
live-lane method is fast AND its trace is small; otherwise it is PRECOMPUTE and the web replays the committed artifact.
The verdict and the deterministic budgets go into the manifest, and scripts/check_artifacts.py fails on a mislabelled
lane.

DinHot's reading of the gate:

- the unit of judgement is the case's *reference method* (the one whose maps the replay shows): the case is live iff the
  reference method's spec lane is ``live`` or ``both``, one run of it at the case's own grid and budget takes at most
  ``RUN_MS_GATE`` (the Python numpy engine is the measured proxy for the TypeScript port; the browser's own timing is
  measured by the web gate), and the trace is within ``TRACE_BYTES_GATE``;
- every method of the case also gets a lane of its own, ``live`` iff its spec lane is live or both and its measured run
  fits the budget, else ``baked`` (``method_lane``): a method labelled live that does not fit is baked, never silently live.
"""
from __future__ import annotations

import time
from collections.abc import Callable

LIVE_WHEELS: set[str] = {"numpy"}   # the wheels a light, live-eligible engine may depend on
RUN_MS_GATE = 1500.0                 # a live run must complete well within an interaction budget
TRACE_BYTES_GATE = 256 * 1024        # a live/replay artifact must stay small


def classify_lane(*, pure_python: bool, wheels: set[str], run_ms: float, trace_bytes: int,
                  extra_reasons: tuple[str, ...] = ()) -> dict:
    reasons: list[str] = list(extra_reasons)
    live = not extra_reasons
    if not pure_python:
        live = False
        reasons.append("not pure-python")
    extra = set(wheels) - LIVE_WHEELS
    if extra:
        live = False
        reasons.append(f"wheels outside the live set: {sorted(extra)}")
    if run_ms > RUN_MS_GATE:
        live = False
        reasons.append(f"runtime exceeds the {RUN_MS_GATE:.0f}ms budget")
    if trace_bytes > TRACE_BYTES_GATE:
        live = False
        reasons.append(f"trace_bytes {trace_bytes} > {TRACE_BYTES_GATE}")
    # NOTE: the raw measured run_ms is used for the DECISION but deliberately NOT stored, the committed manifest
    # must be a pure function of (params, seed); wall-clock would dirty git on every re-run. We record the verdict
    # + the (deterministic) budgets instead. The live runtime is measured separately, live, in the browser.
    return {
        "lane": "live" if live else "precompute",
        "pure_python": pure_python,
        "wheels": sorted(wheels),
        "trace_bytes": trace_bytes,
        "run_ms_budget": RUN_MS_GATE,
        "trace_bytes_budget": TRACE_BYTES_GATE,
        "reasons": reasons,
    }


def method_lane(spec_lane: str, run_ms: float) -> str:
    """``live`` iff the spec says the method can run live (``live`` or ``both``) and one run fits the budget."""
    return "live" if spec_lane in ("live", "both") and run_ms <= RUN_MS_GATE else "baked"


def measure_ms(run: Callable[[], object], repeats: int = 3) -> float:
    """The cost the lane gate judges: one run after a warm-up, as the median of ``repeats`` (timing the whole case,
    validation and the cold start of the first case in a bake, made the verdict depend on bake order: the first case
    baked was once labelled precompute while it runs in microseconds, found 2026-10-04)."""
    run()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        run()
        times.append((time.perf_counter() - t0) * 1000.0)
    return sorted(times)[repeats // 2]
