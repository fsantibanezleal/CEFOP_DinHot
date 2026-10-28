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

from ..io.contract import read_cases, validate_records
from ..io.formats import write_json
from ..io.model_card import is_valid_slot, marker_path

SCHEMA = "example.readiness/v1"   # the const of readiness.schema.json (byte-identical to the template's, U3a open question 1)
CATALOG_REL = "docs/contracts/catalog.md"
INDEX_REL = "manifests/index.json"
CASES_REL = "data/examples/cases.json"
BENCHMARK_REL = "benchmark/results.json"
METRICS_REL = "models/metrics.json"
ENGINE_REF_DIR = "tests/fixtures/engine"
STATUSES = ("real", "active")  # the catalog's status vocabulary (its Contracts section), exactly, lower case
SLOTS = ("cgh-net", "warmstart-model")

# the catalog's reasons as (en, es) templates, in the order of its Missing-data table
T_PROVIDER = ("Served by its provider ({provider}); the real producer is not built yet.",
              "Lo sirve su proveedor ({provider}); el productor real aún no está construido.")
T_NOT_BAKED = ("The pipeline has not baked this build.", "El pipeline no ha generado esta versión.")
T_MANIFESTS = ("{n} of {total} manifests are absent.", "Faltan {n} de {total} manifiestos.")
T_ARTIFACTS = ("{n} of {total} artifacts are absent.", "Faltan {n} de {total} artefactos.")
T_STALE = ("Baked by {engine_version}; the product is {version}.",
           "Generado por {engine_version}; el producto es {version}.")
T_NO_CASES = ("No source document; the bake uses the registry's cases.",
              "No hay documento de origen; la generación usa los casos del registro.")
T_REJECTED = ("{n} of {total} records rejected by contract 1.", "{n} de {total} registros rechazados por el contrato 1.")
T_NO_BENCHMARK = ("The benchmark has not run for this build.", "El benchmark no se ha ejecutado para esta versión.")
T_SKIPPED = ("{n} of {total} benchmark cells were not run.", "{n} de {total} celdas del benchmark no se ejecutaron.")
T_NO_METRICS = ("The model metrics have not been computed for this build.",
                "Las métricas de los modelos no se han calculado para esta versión.")
T_NO_MODEL = ("No released model; the slot's baseline answers (GS for cgh-net, random trap phases for warmstart-model).",
              "No hay un modelo publicado; responde la línea base del espacio (GS para cgh-net, fases aleatorias de las "
              "trampas para warmstart-model).")
T_BASELINE_BAKE = ("The bake's metrics come from the baseline; bake again to use the released model.",
                   "Las métricas de la generación vienen de la línea base; genere de nuevo para usar el modelo publicado.")
T_TRAINING = ("The released model answers; a newer one is training.",
              "Responde el modelo publicado; uno más nuevo está en entrenamiento.")
T_NO_ENGINE_REF = ("The engine reference values are absent; the parity tests cannot run.",
                   "Faltan los valores de referencia del motor; las pruebas de paridad no pueden ejecutarse.")
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
    """The artifact paths a manifest names."""
    single = manifest.get("artifact")
    return [single["path"]] if isinstance(single, dict) and "path" in single else []


class _Facts:
    """What the repository says, read once: the index, the absent manifests and artifacts, the rejected records, the
    benchmark and metrics documents, the model slots."""

    def __init__(self, repo_root: Path, derived_root: Path, models_dir: Path, version: str) -> None:
        self.version = version
        index = _json(derived_root / INDEX_REL)
        self.index: dict | None = index if isinstance(index, dict) else None
        self.engine_version = str(self.index.get("engine_version")) if self.index else ""
        self.manifests_total = 0
        self.manifests_missing: list[str] = []
        self.artifacts_total = 0
        self.artifacts_missing: list[str] = []
        self.baseline_bake = {slot: False for slot in SLOTS}   # a manifest records that a slot's baseline produced its metrics
        if self.index:
            for entry in self.index.get("cases", []):
                rel = entry.get("path")
                if rel is None:   # a refused case has no manifest
                    continue
                self.manifests_total += 1
                manifest = _json(derived_root / rel)
                if not isinstance(manifest, dict):
                    self.manifests_missing.append(rel)
                    continue
                models = manifest.get("models")
                for slot in SLOTS:
                    if isinstance(models, dict) and models.get(slot) == "baseline":
                        self.baseline_bake[slot] = True
                for art in _artifact_paths(manifest):
                    self.artifacts_total += 1
                    if not (derived_root / art).is_file():
                        self.artifacts_missing.append(art)
        cases = repo_root / CASES_REL
        self.cases_present = cases.is_file()
        self.cases_total = 0
        self.cases_rejected_n = 0
        self.cases_rejected: list[str] = []
        if self.cases_present:
            try:
                raw = read_cases(cases)
            except (OSError, ValueError):
                raw = []
            report = validate_records(raw, repo_root)
            self.cases_total = len(raw)
            self.cases_rejected_n = len(report.rejected)
            self.cases_rejected = sorted({r["case_id"] for r in report.rejected})
        bench = _json(derived_root / BENCHMARK_REL)
        self.benchmark: dict | None = bench if isinstance(bench, dict) else None
        self.benchmark_version = str(self.benchmark.get("engine_version")) if self.benchmark else ""
        self.skipped: list[str] = []
        self.cells_total = 0
        if self.benchmark:
            self.skipped = sorted({f"{c['method']}/{c['geometry']}" for c in self.benchmark.get("skipped", [])})
            ran = {(r["method"], r["geometry"]) for r in self.benchmark.get("rows", [])}
            self.cells_total = len(ran) + len(self.skipped)
        metrics = _json(derived_root / METRICS_REL)
        self.metrics: dict | None = metrics if isinstance(metrics, dict) else None
        self.metrics_version = str(self.metrics.get("engine_version")) if self.metrics else ""
        self.valid_slot = {slot: is_valid_slot(models_dir, slot, repo_root) for slot in SLOTS}
        self.marker = {slot: marker_path(models_dir, slot).is_file() for slot in SLOTS}
        ref = repo_root / ENGINE_REF_DIR
        self.engine_ref = ref.is_dir() and any(ref.glob("*.json"))


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
    stale = {"case-index": f.engine_version if f.index else None, "case-manifest": f.engine_version if f.index else None,
             "trace": f.engine_version if f.index else None,
             "benchmark-results": f.benchmark_version if f.benchmark else None,
             "model-metrics": f.metrics_version if f.metrics else None}
    if stale.get(rid) is not None and stale[rid] != f.version:
        return _entry(row, "stale", "real", _fill(T_STALE, engine_version=stale[rid], version=f.version))
    if rid == "params-record" and not f.cases_present:
        return _entry(row, "missing", None, _fill(T_NO_CASES))
    if rid == "params-record" and f.cases_rejected_n:
        return _entry(row, "partial", "real", _fill(T_REJECTED, n=f.cases_rejected_n, total=f.cases_total), f.cases_rejected)
    if rid == "benchmark-results" and f.benchmark is None:
        return _entry(row, "missing", None, _fill(T_NO_BENCHMARK))
    if rid == "benchmark-results" and f.skipped:
        return _entry(row, "partial", "real", _fill(T_SKIPPED, n=len(f.skipped), total=f.cells_total), f.skipped)
    if rid == "model-metrics" and f.metrics is None:
        return _entry(row, "missing", None, _fill(T_NO_METRICS))
    if rid in SLOTS and not f.valid_slot[rid]:
        return _entry(row, "training", "baseline", _fill(T_NO_MODEL))
    if rid in SLOTS and f.baseline_bake[rid]:
        return _entry(row, "training", "baseline", _fill(T_BASELINE_BAKE))
    if rid in SLOTS and f.marker[rid]:
        return _entry(row, "training", "real", _fill(T_TRAINING))
    if rid == "engine-reference" and not f.engine_ref:
        return _entry(row, "missing", None, _fill(T_NO_ENGINE_REF))
    if rid == "api":
        return _entry(row, "missing", None, _fill(T_API))
    return _entry(row, "available", "real", None)


def compute(*, repo_root: str | Path, derived_root: str | Path, models_dir: str | Path,
            catalog_path: str | Path | None = None, version: str | None = None) -> dict:
    """The readiness document of the repository at ``repo_root``, whose baked documents are under ``derived_root``
    and whose released models are in ``models_dir``. ``catalog_path`` and ``version`` default to the repository's."""
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
