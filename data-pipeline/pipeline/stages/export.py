"""Stage 6, export (CONTRACT 2): write the compact trace artifact and the case manifest, and build the summary block.
The manifest records the measured lane and gate verdict, the artifact byte size, the flags of contract 1 and of the bake,
the verdict per method and the model slots behind the metrics."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.manifest import build_case_manifest
from ..core.trace import dumps
from ..io.formats import write_json

EFFICIENCY_FLOOR = 0.5   # a method is eligible for "best" with at least this share of the best efficiency (trace schema)


def best_method(methods: dict[str, dict]) -> str:
    """Lowest ``rel_std_pct`` among the methods whose efficiency is at least half the best efficiency (ties: lowest id)."""
    top = max(m["efficiency"] for m in methods.values())
    eligible = {k: m for k, m in methods.items() if m["efficiency"] >= EFFICIENCY_FLOOR * top}
    return sorted(eligible, key=lambda k: (eligible[k]["rel_std_pct"], k))[0]


def summary(methods: dict[str, dict]) -> dict:
    best = best_method(methods)
    m = methods[best]
    en = (f"{len(methods)} methods ran. Lowest relative standard deviation among those with at least half the best "
          f"efficiency: {best}, {m['rel_std_pct']:.2f} percent with efficiency {m['efficiency']:.3f}.")
    es = (f"Se ejecutaron {len(methods)} métodos. Menor desviación estándar relativa entre los de al menos la mitad de la "
          f"mejor eficiencia: {best}, {m['rel_std_pct']:.2f} por ciento con eficiencia {m['efficiency']:.3f}.")
    return {"best_method": best, "notes": {"en": en, "es": es}}


def run(*, case: Any, record: dict, trace: dict, gate: dict, flags: list[dict], methods: dict[str, dict],
        models: dict[str, str], expect: dict, derived_dir: str, manifests_dir: str) -> dict:
    artifact_rel = f"{case.id}/trace.json"
    trace_bytes = write_json(Path(derived_dir) / artifact_rel, trace)
    assert trace_bytes == len(dumps(trace)) == gate["trace_bytes"], "the gate was judged on a different trace"
    manifest = build_case_manifest(case=case, record=record, artifact_rel=artifact_rel, trace_bytes=trace_bytes, gate=gate,
                                   flags=flags, methods=methods, models=models, expect=expect)
    write_json(Path(manifests_dir) / f"{case.id}.json", manifest)
    return manifest
