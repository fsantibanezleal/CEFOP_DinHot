"""Stage 6, export (CONTRACT 2): write the compact trace artifact + the case manifest. The manifest records the
measured lane/gate verdict, the artifact byte size, the CONTRACT-1 flags, and the evaluation metrics."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.gate import classify_lane
from ..core.manifest import build_case_manifest
from ..core.trace import build_trace
from ..io.formats import write_json
from ..io.schema import SIRParams, SIRResult


def run(
    *,
    case: Any,
    params: SIRParams,
    result: SIRResult,
    seed: int,
    run_ms: float,
    flags: list[dict],
    metrics: dict,
    models: dict[str, str],
    expect: dict,
    derived_dir: str,
    manifests_dir: str,
) -> dict:
    trace = build_trace(result)
    artifact_rel = f"{case.id}/trace.json"
    trace_bytes = write_json(Path(derived_dir) / artifact_rel, trace)
    gate = classify_lane(pure_python=True, wheels={"numpy"}, run_ms=run_ms, trace_bytes=trace_bytes)
    manifest = build_case_manifest(
        case=case, params=params, seed=seed,
        artifact_rel=artifact_rel, trace_bytes=trace_bytes, gate=gate, flags=flags, metrics=metrics, models=models,
        expect=expect,
    )
    write_json(Path(manifests_dir) / f"{case.id}.json", manifest)
    return manifest
