"""The readiness document (catalog row readiness, ADR-0080 decisions 3 and 4): what is real in this build, computed
from docs/contracts/catalog.md and the repository state, never written by hand.

A pure function of its inputs: no clock, no randomness, rows in catalog order, ``missing`` sorted. The rules, their
order (first match wins) and their reasons are the catalog's ``## Missing-data states`` table; tests/contracts/
test_readiness.py parses that table and holds every reason here to it. Stdlib only, so scripts/check_readiness.py runs
in CI without installing the pipeline's dependencies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..io.contract import validate_rows
from ..io.formats import read_csv_rows, write_json
from ..model.baseline import is_valid_bundle

SCHEMA = "example.readiness/v1"
CATALOG_REL = "docs/contracts/catalog.md"
INDEX_REL = "manifests/index.json"
PARAMS_REL = "data/examples/params.csv"
MARKER_REL = "training/surrogate-model"
STATUSES = ("real", "active")  # the catalog's status vocabulary (its Contracts section), exactly, lower case
MODEL_SLOT = "surrogate-model"

# the catalog's reasons as (en, es) templates, in the order of its Missing-data table
T_PROVIDER = ("Served by its provider ({provider}); the real producer is not built yet.",
              "Lo sirve su proveedor ({provider}); el productor real aún no está construido.")
T_NOT_BAKED = ("The pipeline has not baked this build.", "El pipeline no ha generado esta versión.")
T_MANIFESTS = ("{n} of {total} manifests are absent.", "Faltan {n} de {total} manifiestos.")
T_ARTIFACTS = ("{n} of {total} artifacts are absent.", "Faltan {n} de {total} artefactos.")
T_STALE = ("Baked by {engine_version}; the product is {version}.",
           "Generado por {engine_version}; el producto es {version}.")
T_NO_PARAMS = ("No source table; the bake uses the registry's cases.",
               "No hay tabla de origen; la generación usa los casos del registro.")
T_REJECTED = ("{n} of {total} rows rejected by contract 1.", "{n} de {total} filas rechazadas por el contrato 1.")
T_NO_BUNDLE = ("No released surrogate; the analytic baseline answers.",
               "No hay un sustituto publicado; responde la línea base analítica.")
T_BASELINE_BAKE = ("The bake's metrics come from the analytic baseline; bake again to use the released surrogate.",
                   "Las métricas de la generación vienen de la línea base analítica; genere de nuevo para usar el "
                   "sustituto publicado.")
T_TRAINING = ("The released surrogate answers; a newer one is training.",
              "Responde el sustituto publicado; uno más nuevo está en entrenamiento.")
T_API = ("The API lane is dormant; the site reads the committed documents.",
         "La API está inactiva; el sitio lee los documentos versionados.")


def parse_catalog(text: str) -> list[dict[str, str]]:
    """The rows of the ``## Contracts`` table, one dict per row keyed by the lower-cased header cells."""
    lines = text.replace("\r\n", "\n").split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Contracts")
    table: list[list[str]] = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        if ln.startswith("|"):
            table.append([c.strip() for c in ln.strip().strip("|").split("|")])
    header = [c.lower() for c in table[0]]
    return [dict(zip(header, cells)) for cells in table[2:]]  # table[1] is the separator


def _fill(tpl: tuple[str, str], **vals: object) -> dict[str, str]:
    out = []
    for text in tpl:
        for k, v in vals.items():
            text = text.replace("{" + k + "}", str(v))
        out.append(text)
    return {"en": out[0], "es": out[1]}


def _json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _artifact_paths(manifest: dict) -> list[str]:
    """The artifact paths a manifest names, in either form of contract 2."""
    if isinstance(manifest.get("artifacts"), list):
        return [a["path"] for a in manifest["artifacts"] if isinstance(a, dict) and "path" in a]
    single = manifest.get("artifact")
    return [single["path"]] if isinstance(single, dict) and "path" in single else []


class _Facts:
    """What the repository says, read once: the index, the absent manifests and artifacts, the rejected rows."""

    def __init__(self, repo_root: Path, derived_root: Path, models_dir: Path, version: str) -> None:
        self.version = version
        index = _json(derived_root / INDEX_REL)
        self.index: dict | None = index if isinstance(index, dict) else None
        self.engine_version = str(self.index.get("engine_version")) if self.index else ""
        self.manifests_total = 0
        self.manifests_missing: list[str] = []
        self.artifacts_total = 0
        self.artifacts_missing: list[str] = []
        self.baseline_bake = False  # a manifest records that the slot's baseline produced its metrics
        if self.index:
            for entry in self.index.get("cases", []):
                rel = entry["manifest_path"]
                self.manifests_total += 1
                manifest = _json(derived_root / rel)
                if not isinstance(manifest, dict):
                    self.manifests_missing.append(rel)
                    continue
                models = manifest.get("models")
                if isinstance(models, dict) and models.get(MODEL_SLOT) == "baseline":
                    self.baseline_bake = True
                for art in _artifact_paths(manifest):
                    self.artifacts_total += 1
                    if not (derived_root / art).is_file():
                        self.artifacts_missing.append(art)
        params = repo_root / PARAMS_REL
        self.params_present = params.is_file()
        self.params_total = 0
        self.params_rejected_rows = 0
        self.params_rejected: list[str] = []
        if self.params_present:
            rows = read_csv_rows(params)
            report = validate_rows(rows)
            self.params_total = len(rows)
            self.params_rejected_rows = len(report.rejected)
            self.params_rejected = sorted({r["case_id"] for r in report.rejected})
        self.bundle_ok = is_valid_bundle(_json(models_dir / "surrogate.json"))
        self.marker = (models_dir / MARKER_REL).is_file()


def _entry(row: dict[str, str], state: str, provenance: str | None, reason: dict | None,
           missing: list[str] | None = None) -> dict:
    return {"id": row["id"], "version": row["version"], "status": row["status"], "provenance": provenance,
            "state": state, "reason": reason, "missing": sorted(missing or [])}


def _rule(row: dict[str, str], f: _Facts) -> dict:
    """The first rule of the catalog's Missing-data table that matches ``row``."""
    rid = row["id"]
    provider = row.get("provider", "").replace("`", "")
    if row["status"] not in STATUSES:
        raise ValueError(f"catalog row {rid!r}: status {row['status']!r} is not one of "
                         f"{' or '.join(repr(s) for s in STATUSES)} (lower case, no other value)")
    if row["status"] == "active":
        return _entry(row, "provider", provider.split(":", 1)[0] or "stub", _fill(T_PROVIDER, provider=provider))
    derived = rid in ("case-index", "case-manifest", "trace")
    if derived and f.index is None:
        return _entry(row, "missing", None, _fill(T_NOT_BAKED))
    if rid == "case-manifest" and f.manifests_missing:
        return _entry(row, "partial", "real", _fill(T_MANIFESTS, n=len(f.manifests_missing), total=f.manifests_total),
                      f.manifests_missing)
    if rid == "trace" and f.artifacts_missing:
        return _entry(row, "partial", "real", _fill(T_ARTIFACTS, n=len(f.artifacts_missing), total=f.artifacts_total),
                      f.artifacts_missing)
    if derived and f.engine_version != f.version:
        return _entry(row, "stale", "real", _fill(T_STALE, engine_version=f.engine_version, version=f.version))
    if rid == "params-record" and not f.params_present:
        return _entry(row, "missing", None, _fill(T_NO_PARAMS))
    if rid == "params-record" and f.params_rejected_rows:
        return _entry(row, "partial", "real", _fill(T_REJECTED, n=f.params_rejected_rows, total=f.params_total),
                      f.params_rejected)
    if rid == "surrogate-model" and not f.bundle_ok:
        return _entry(row, "training", "baseline", _fill(T_NO_BUNDLE))
    if rid == MODEL_SLOT and f.baseline_bake:
        return _entry(row, "training", "baseline", _fill(T_BASELINE_BAKE))
    if rid == "surrogate-model" and f.marker:
        return _entry(row, "training", "real", _fill(T_TRAINING))
    if rid == "api":
        return _entry(row, "missing", None, _fill(T_API))
    return _entry(row, "available", "real", None)


def compute(*, repo_root: str | Path, derived_root: str | Path, models_dir: str | Path,
            catalog_path: str | Path | None = None, version: str | None = None) -> dict:
    """The readiness document of the repository at ``repo_root``, whose baked documents are under ``derived_root``
    and whose released model is in ``models_dir``. ``catalog_path`` and ``version`` default to the repository's."""
    root = Path(repo_root)
    catalog = Path(catalog_path) if catalog_path else root / CATALOG_REL
    raw = catalog.read_bytes().replace(b"\r\n", b"\n")
    ver = version if version is not None else (root / "VERSION").read_text(encoding="utf-8").strip()
    facts = _Facts(root, Path(derived_root), Path(models_dir), ver)
    rows = [r for r in parse_catalog(raw.decode("utf-8")) if r["id"] != "readiness"]
    return {"schema": SCHEMA, "product_version": ver, "catalog_sha256": hashlib.sha256(raw).hexdigest(),
            "contracts": [_rule(r, facts) for r in rows]}


def write(derived_root: str | Path, doc: dict) -> int:
    """Write ``<derived_root>/readiness.json`` as compact JSON; return its byte size."""
    return write_json(Path(derived_root) / "readiness.json", doc)
