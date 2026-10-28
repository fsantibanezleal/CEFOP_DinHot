"""CONTRACT 2, artifact (pipeline -> web). The manifest is the authoritative, versioned record of a baked case (catalog row
case-manifest, schema ``dinhot.manifest/v1``): its params as the producer used them, seed, engine and version, the compact
artifact pointer and byte size, the lane and gate verdict, the flags from contract 1 and from the bake, the verdict per
method, the model slots behind it and the published anchor. The web loads ONLY manifests and artifacts. A flat
``index.json`` inventories every case, baked or refused (catalog row case-index).

A manifest is a pure function of (params, seed): no wall-clock time (ADR-0054). The only measured quantity behind it is the
lane decision, stored as a verdict and the deterministic budgets, never as milliseconds.
"""
from __future__ import annotations

from typing import Any

from .. import __version__
from .trace import TRACE_SCHEMA

MANIFEST_SCHEMA = "dinhot.manifest/v1"
INDEX_SCHEMA = "dinhot.index/v1"
ENGINE_PACKAGE = "dinhot-holo"
ENGINE_MODEL = "scalar-fourier"


def build_case_manifest(
    *,
    case: Any,
    record: dict,
    artifact_rel: str,
    trace_bytes: int,
    gate: dict,
    flags: list[dict],
    methods: dict[str, dict],
    models: dict[str, str],
    expect: dict,
) -> dict:
    params = {k: v for k, v in record.items() if k != "case_id"}
    params["expect"] = expect
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case.id,
        "title": case.title,
        "category": case.category,
        "real_or_synthetic": case.real_or_synthetic,
        "expected_band": case.expected_band,
        "engine": {"package": ENGINE_PACKAGE, "version": __version__, "model": ENGINE_MODEL},
        "params": params,
        "seed": record["seed"],
        "artifact": {"path": artifact_rel, "format": "json", "trace_schema": TRACE_SCHEMA, "bytes": trace_bytes},
        "lane": gate["lane"],
        "gate": gate,
        "flags": flags,
        "methods": methods,
        "models": models,
        "expect": expect,
        "anchor": case.anchor,
    }


def index_entry_baked(case: Any) -> dict:
    return {"case_id": case.id, "title": case.title, "category": case.category, "path": f"manifests/{case.id}.json",
            "status": "baked", "reason": None}


def index_entry_refused(case: Any, reason: dict) -> dict:
    return {"case_id": case.id, "title": case.title, "category": case.category, "path": None, "status": "refused",
            "reason": reason}


def build_index(entries: list[dict], default_case: str) -> dict:
    """entries -> the flat authoritative inventory, sorted by case id, with the case the App opens on (a baked one)."""
    baked = {e["case_id"] for e in entries if e["status"] == "baked"}
    if default_case not in baked:
        raise ValueError(f"default case {default_case!r} is not among the baked cases")
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "default_case": default_case,
        "cases": sorted(entries, key=lambda e: e["case_id"]),
    }
