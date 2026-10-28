"""The measured lane gate (ADR-0054). A case may be re-run LIVE in the browser iff its engine is light (pure Python
with wheels in a small allowed set, a proxy for an engine small enough to port or to run client side) AND one run is
fast AND its trace is small; otherwise it is PRECOMPUTE and the web replays the committed artifact. The verdict and
the measured numbers go into the manifest, and scripts/check_artifacts.py fails on a mislabelled lane."""
from __future__ import annotations

LIVE_WHEELS: set[str] = {"numpy"}   # the wheels a light, live-eligible engine may depend on
RUN_MS_GATE = 1500.0                 # a live run must complete well within an interaction budget
TRACE_BYTES_GATE = 256 * 1024        # a live/replay artifact must stay small


def classify_lane(*, pure_python: bool, wheels: set[str], run_ms: float, trace_bytes: int) -> dict:
    reasons: list[str] = []
    live = True
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
