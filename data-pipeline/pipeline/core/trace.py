"""The compact TRACE = the web-replay artifact (decimated trajectory + summary). Part of CONTRACT 2: its shape is
mirrored by frontend/src/lib/contract.types.ts, so a drift fails the web build. Schema id is versioned."""
from __future__ import annotations

from ..io.schema import SIRResult

TRACE_SCHEMA = "example.trace/v1"
MAX_POINTS = 200  # decimate longer trajectories so the committed artifact stays small (replay, not raw data)


def build_trace(result: SIRResult) -> dict:
    n = len(result.t)
    if n > MAX_POINTS:
        idx = [round(i * (n - 1) / (MAX_POINTS - 1)) for i in range(MAX_POINTS)]
    else:
        idx = list(range(n))
    return {
        "schema": TRACE_SCHEMA,
        "case_id": result.case_id,
        "t": [round(result.t[i], 3) for i in idx],
        "S": [round(result.S[i], 2) for i in idx],
        "I": [round(result.I[i], 2) for i in idx],
        "R": [round(result.R[i], 2) for i in idx],
        "summary": {
            "peak_I": round(result.peak_I, 2),
            "t_peak": round(result.t_peak, 2),
            "attack_rate": round(result.attack_rate, 4),
        },
    }
