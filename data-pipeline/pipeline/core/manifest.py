"""CONTRACT 2, artifact (pipeline -> web). The manifest is the authoritative, versioned record of a baked case:
its params, seed, engine+version, the compact artifact pointer + byte size, the lane/gate verdict, flags from
CONTRACT 1, and the evaluation metrics. The web loads ONLY manifests + artifacts; frontend/src/lib/contract.types.ts
mirrors this schema so a drift fails the build. A flat index.json inventories every case (ADR-0057 default)."""
from __future__ import annotations

from typing import Any

from .. import __version__
from .trace import TRACE_SCHEMA

MANIFEST_SCHEMA = "example.manifest/v4"
INDEX_SCHEMA = "example.index/v2"


def build_case_manifest(
    *,
    case: Any,
    params: Any,
    seed: int,
    artifact_rel: str,
    trace_bytes: int,
    gate: dict,
    flags: list[dict],
    metrics: dict,
    models: dict[str, str],
    expect: dict,
) -> dict:
    # Deterministic: a pure function of (params, seed). No wall-clock here (would dirty git on re-run), the
    # lane/gate verdict + budgets carry the lane decision; live timing is measured in the browser, not committed.
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case.id,
        "title": case.title,
        "category": case.category,
        "real_or_synthetic": case.real_or_synthetic,
        "expected_band": case.expected_band,
        "engine": {"package": "pipeline", "version": __version__, "model": "SIR, forward Euler"},
        "params": {"beta": params.beta, "gamma": params.gamma, "N": params.N, "I0": params.I0, "days": params.days},
        "seed": seed,
        "artifact": {"path": artifact_rel, "format": "json", "trace_schema": TRACE_SCHEMA, "bytes": trace_bytes},
        "lane": gate["lane"],
        "gate": gate,
        "flags": flags,
        "metrics": metrics,
        "models": models,  # per model slot: "real" (the released bundle) or "baseline" produced the metrics
        "expect": expect,
    }


def build_index(entries: list[dict], default_case: str) -> dict:
    """entries: [{case_id, title, category, manifest_path}] -> the flat authoritative inventory, with the case the
    App opens on."""
    if default_case not in {e["case_id"] for e in entries}:
        raise ValueError(f"default case {default_case!r} is not among the baked cases")
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "n_cases": len(entries),
        "default_case": default_case,
        "cases": sorted(entries, key=lambda e: e["case_id"]),
    }
