"""CONTRACT 1, ingestion (raw -> pipeline). The bring-your-own-case gate.

A source document (``data/examples/cases.json``) is an array of params records; the record shape is
``docs/contracts/schemas/params-record.schema.json`` (catalog row params-record), read here through ``jsonschema_lite``
so the schema file stays the single source and this module runs on the standard library (readiness runs in CI with nothing
installed). A record is ACCEPTED iff it passes the schema and the rules a schema cannot state; a bad record is REJECTED
with a reason (never silently coerced: a string is not a number, a NaN is not a value); a plausible but suspicious record
is FLAGGED (accepted, and the manifest records the flag).

Rules beyond the schema (each a rejection naming the record and the offending value):

- trap ids are unique within a target;
- ``reference_method`` is one of ``methods``;
- a trap lies strictly inside the unaliased field of view: ``abs(x_um)`` and ``abs(y_um)`` below ``lambda f / (2 p)``
  (the engine's rule, ``core.traps.check_in_field``: the bin at the bound is outside the centred FFT grid), the bound is
  in the reason (case C11 exists to prove it);
- the numerical aperture does not exceed the immersion index;
- a device model is read at the focal plane only, so it excludes traps off the focal plane or with a vortex charge, and
  it excludes an aberration (not modelled together);
- ``feedback``, ``dynamics`` and ``rearrangement`` need a trap target; ``dynamics.trap_id`` and ``rearrangement.target_ids``
  name traps of the target;
- a shaped target has the dimensions its shape needs, and fits the field of view;
- every ``expect`` key is a known metric (``core/expect.py``) and a method prefix is one of ``methods``.

The accepted record keeps the exact values the producer uses: trap coordinates are rounded to 0.1 nm once, here, before
any run (the manifest stores them as accepted, never rounded again).
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.expect import ExpectationError, parse_key
from . import jsonschema_lite

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_REL = "docs/contracts/schemas/params-record.schema.json"
COORD_DECIMALS = 4            # trap coordinates in micrometres: 0.1 nm
NA_SCALAR_LIMIT = 0.7         # beyond this the scalar model carries a validity flag (SDD non-goals)
SHAPE_NEEDS = {"ring": ("radius_um", "width_um"), "disc": ("radius_um",), "line": ("length_um", "width_um"),
               "top_hat": ("radius_um",), "lg_ring": ("radius_um", "width_um")}

_schema_cache: dict[str, dict] = {}


def load_schema(repo_root: Path | None = None) -> dict:
    """The params-record schema of ``repo_root`` (a copy of the repository may lack it: then this repository's own)."""
    root = repo_root if repo_root and (repo_root / SCHEMA_REL).is_file() else REPO_ROOT
    key = str(root)
    if key not in _schema_cache:
        _schema_cache[key] = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8"))
    return _schema_cache[key]


@dataclass
class ContractReport:
    accepted: list[dict]
    rejected: list[dict[str, Any]] = field(default_factory=list)
    flagged: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.accepted) > 0

    def summary(self) -> str:
        return f"{len(self.accepted)} accepted, {len(self.rejected)} rejected, {len(self.flagged)} flagged"


def half_field_um(setup: dict) -> float:
    """The unaliased half-window ``lambda f / (2 p)`` of a record's setup, in micrometres."""
    return setup["wavelength_nm"] * 1e-9 * setup["focal_mm"] * 1e-3 / (2.0 * setup["pitch_um"] * 1e-6) * 1e6


def bin_um(setup: dict) -> float:
    """One focal FFT bin ``lambda f / (pad N p)`` of a record's setup, in micrometres."""
    return half_field_um(setup) * 2.0 / (setup["pad"] * setup["n_pix"])


def _reject(i: int, cid: str, code: str, en: str, es: str, **extra: Any) -> dict[str, Any]:
    return {"row": i, "case_id": cid, "code": code, "reason": en, "reason_es": es, **extra}


def _cross_field(rec: dict, i: int, cid: str) -> dict[str, Any] | None:
    """The first rule a schema cannot state that ``rec`` breaks, as a rejection; None when it keeps them all."""
    setup, target, methods = rec["setup"], rec["target"], rec["methods"]
    if rec["reference_method"] not in methods:
        m = rec["reference_method"]
        return _reject(i, cid, "reference_method", f"reference_method {m} is not one of methods {methods}",
                       f"reference_method {m} no está entre los métodos {methods}")
    if setup["na"] > setup["n_imm"]:
        return _reject(i, cid, "na", f"na={setup['na']:g} exceeds the immersion index n_imm={setup['n_imm']:g}",
                       f"na={setup['na']:g} supera el índice de inmersión n_imm={setup['n_imm']:g}")
    bound = half_field_um(setup)
    traps = target["traps"] if target["kind"] == "traps" else []
    ids = [t["id"] for t in traps]
    if len(set(ids)) != len(ids):
        dup = sorted({k for k in ids if ids.count(k) > 1})
        return _reject(i, cid, "duplicate_trap_id", f"duplicate trap ids {dup}", f"ids de trampa repetidos {dup}")
    for t in traps:
        for axis in ("x_um", "y_um"):
            if abs(t[axis]) >= bound:
                return _reject(
                    i, cid, "out_of_field",
                    f"trap {t['id']} has {axis}={t[axis]:g} um, outside the unaliased field of view "
                    f"(abs must be below {bound:.1f} um = lambda f / (2 p))",
                    f"la trampa {t['id']} tiene {axis}={t[axis]:g} um, fuera del campo de visión sin solapamiento "
                    f"(abs debe ser menor que {bound:.1f} um = lambda f / (2 p))", bound_um=round(bound, 3))
    if rec["device"] is not None:
        if any(t["z_um"] != 0 or t["charge"] != 0 for t in traps):
            return _reject(i, cid, "device_scope", "a device model is read at the focal plane: traps need z_um=0 and charge=0",
                           "el modelo del dispositivo se lee en el plano focal: las trampas requieren z_um=0 y charge=0")
        if rec["aberration"] is not None:
            return _reject(i, cid, "device_scope", "a device model and an aberration are not modelled together",
                           "un modelo de dispositivo y una aberración no se modelan juntos")
    for key in ("feedback", "dynamics", "rearrangement"):
        if rec[key] is not None and target["kind"] != "traps":
            return _reject(i, cid, key, f"{key} needs a trap target", f"{key} necesita un objetivo de trampas")
    if rec["dynamics"] is not None and rec["dynamics"]["trap_id"] not in ids:
        return _reject(i, cid, "dynamics_trap", f"dynamics.trap_id {rec['dynamics']['trap_id']} is not a trap of the target",
                       f"dynamics.trap_id {rec['dynamics']['trap_id']} no es una trampa del objetivo")
    if rec["rearrangement"] is not None:
        unknown = [k for k in rec["rearrangement"]["target_ids"] if k not in ids]
        if unknown or not rec["rearrangement"]["target_ids"]:
            return _reject(i, cid, "rearrangement_ids", f"rearrangement.target_ids must be a non-empty subset of the trap ids "
                           f"(unknown: {unknown})", f"rearrangement.target_ids debe ser un subconjunto no vacío de los ids "
                           f"de trampa (desconocidos: {unknown})")
    if target["kind"] == "shaped":
        need = SHAPE_NEEDS[target["shape"]]
        missing = [k for k in need if not target.get(k, 0) > 0]
        if missing:
            return _reject(i, cid, "shape", f"shape {target['shape']} needs {list(need)} above 0 (missing: {missing})",
                           f"la forma {target['shape']} necesita {list(need)} sobre 0 (faltan: {missing})")
        extent = max(target.get("radius_um", 0) + target.get("width_um", 0) / 2, target.get("length_um", 0) / 2)
        if extent >= bound:
            return _reject(i, cid, "out_of_field", f"the shape reaches {extent:g} um, outside the field of view "
                           f"(below {bound:.1f} um)", f"la forma llega a {extent:g} um, fuera del campo de visión "
                           f"(menor que {bound:.1f} um)", bound_um=round(bound, 3))
    try:
        for key, (lo, hi) in rec["expect"].items():
            method, _ = parse_key(key)
            if method is not None and method not in methods:
                raise ExpectationError(f"{key}: {method} is not one of methods")
            if lo > hi:
                raise ExpectationError(f"{key}: empty range [{lo}, {hi}]")
    except ExpectationError as exc:
        return _reject(i, cid, "expect", str(exc), f"expectativa no válida: {exc}")
    return None


def _flags(rec: dict, cid: str) -> list[dict[str, str]]:
    out = []
    if rec["setup"]["na"] >= NA_SCALAR_LIMIT:
        out.append({"case_id": cid, "flag": f"scalar model beyond its validity: na={rec['setup']['na']:g} >= "
                                            f"{NA_SCALAR_LIMIT:g} (vectorial focusing not modelled)"})
    if rec["target"]["kind"] == "traps":
        b = bin_um(rec["setup"])
        pts = [(t["x_um"], t["y_um"], t["z_um"]) for t in rec["target"]["traps"]]
        if 1 < len(pts) <= 1100:
            dmin = min(math.dist(a, c) for k, a in enumerate(pts) for c in pts[:k])
            if dmin < 2 * b * rec["setup"]["pad"] / 2:
                out.append({"case_id": cid, "flag": f"traps closer than the focal spot: minimum spacing {dmin:.2f} um "
                                                    f"is below {rec['setup']['pad']:g} bins of {b:.3f} um"})
    return out


def _round_coordinates(rec: dict) -> dict:
    out = copy.deepcopy(rec)
    if out["target"]["kind"] == "traps":
        for t in out["target"]["traps"]:
            for k in ("x_um", "y_um", "z_um"):
                t[k] = round(float(t[k]), COORD_DECIMALS) + 0.0   # + 0.0: never -0.0
    return out


def validate_records(raw: list[Any], repo_root: Path | None = None) -> ContractReport:
    """Apply CONTRACT 1 to raw records (the parsed ``cases.json``). Pure; deterministic; no I/O besides the schema file."""
    schema = load_schema(repo_root)
    report = ContractReport(accepted=[])
    seen: set[str] = set()
    for i, row in enumerate(raw):
        cid = str(row.get("case_id", f"row{i}")) if isinstance(row, dict) else f"row{i}"
        problems = jsonschema_lite.errors(schema, row)
        if problems:
            detail = "; ".join(problems[:4]) + (f"; and {len(problems) - 4} more" if len(problems) > 4 else "")
            report.rejected.append(_reject(i, cid, "schema", detail, f"no cumple el esquema: {detail}"))
            continue
        if cid in seen:
            report.rejected.append(_reject(i, cid, "duplicate_case", f"case_id {cid} appears twice",
                                           f"case_id {cid} aparece dos veces"))
            continue
        bad = _cross_field(row, i, cid)
        if bad is not None:
            report.rejected.append(bad)
            continue
        seen.add(cid)
        report.accepted.append(_round_coordinates(row))
        report.flagged += _flags(row, cid)
    return report


def read_cases(path: str | Path) -> list[Any]:
    """The parsed source document: an array of records; ``ValueError`` when the file is not that."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, list):
        raise ValueError(f"{path}: the source document must be an array of params records")
    return doc
