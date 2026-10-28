"""Measured expected ranges of the cases: bake every accepted case on several seeds, record each method's metrics and the
drivers' case metrics, and propose a range per value (``data-pipeline/run.py ranges``).

The rule (stated here so a reader of ``cases/measured_ranges.json`` can re-derive it): for a metric measured on the seeds
``v_1..v_k`` the range is ``mean +- half`` with ``half = max(REL * |mean|, max(v) - min(v))`` (plus or minus ``REL`` of the mean,
or the seed spread, whichever is wider), clipped to the metric's domain. Every method metric is keyed ``<method>.<metric>`` so
a range is never applied to another method (the reference method stands in only when it did not run, and then the bake drops
the keys of methods that did not run). A published anchor is not measured: the case keeps its own band and the report lists
where the measurement falls outside it.

The measurement runs the bake itself (``bake.bake_case``) with ``expect.check`` replaced by a recorder, so the numbers are the
ones the canonical bake will check, through the same code. Artifacts go to the sandbox ``output`` root, never to
``data/derived``.
"""
from __future__ import annotations

import time
from pathlib import Path

from . import bake as bake_mod
from .core import expect as expectations
from .io.formats import write_json
from .pipeline import MAX_WORKERS, REPO, PipelinePaths, bake_jobs
from .stages import infer, preprocess

REL = 0.10
SEEDS = 3
SCHEMA = "dinhot.measured-ranges/v1"
FRACTIONS = ("efficiency", "uniformity", "zero_order", "ghost", "signal_efficiency")
METHOD_KEYS = ("efficiency", "uniformity", "rel_std_pct")
SHAPED_KEYS = ("efficiency", "signal_rms_error_pct", "signal_efficiency")
SORTING_KEYS = ("efficiency",)   # a sorting method (M16) lights the target sites only: its spread over all sites is not a result


def capture_job(job: dict) -> dict:
    """Bake one record in a worker with the expectation check replaced by a recorder (it checks nothing, keeps the numbers)."""
    caught: dict = {}

    def recorder(case_id, expect, method_metrics, reference, case_metrics=None):
        caught.update(methods=method_metrics, case=dict(case_metrics or {}), reference=reference)
        return {k: [float(v[0]), float(v[1])] for k, v in expect.items()}

    orig = expectations.check
    expectations.check = recorder
    try:
        out = bake_mod.bake_case(job["rec"], derived_dir=Path(job["root"]), manifests_dir=Path(job["manifests"]),
                                 models_dir=Path(job["models"]), allow_missing=job["allow_missing"],
                                 contract_flags=job["flags"])
    finally:
        expectations.check = orig
    return {"case_id": job["rec"]["case_id"], "seed": job["rec"]["seed"], "caught": caught, "failures": out[1]}


def propose(values: list[float], metric: str, rel: float = REL) -> list[float]:
    """The range of one metric from its per-seed values (module docstring), clipped to the metric's domain."""
    mean = sum(values) / len(values)
    half = max(rel * abs(mean), max(values) - min(values))
    lo, hi = mean - half, mean + half
    if metric in FRACTIONS:
        lo, hi = max(lo, 0.0), min(hi, 1.0)
    else:
        lo = max(lo, 0.0)
    return [float(f"{lo:.4g}"), float(f"{hi:.4g}")]


def measure(output: Path, *, seeds: int = SEEDS, workers: int = MAX_WORKERS, only: list[str] | None = None,
            allow_missing: bool = True, cases_path: str | Path | None = None) -> dict:
    """The measured document: per case and key the per-seed values and the proposed range."""
    paths = PipelinePaths.from_output(output)
    report, _ = preprocess.run(cases_path, REPO)
    jobs = []
    for rec in report.accepted:
        if only and rec["case_id"] not in only:
            continue
        for k in range(seeds):
            sub = PipelinePaths.from_output(Path(output) / f"seed{k}")
            jobs.append({"rec": dict(rec, seed=rec["seed"] + k), "root": str(sub.root), "manifests": str(sub.manifests),
                         "models": str(sub.models), "allow_missing": allow_missing, "flags": []})
    t0 = time.perf_counter()
    results = bake_jobs(jobs, workers, capture_job)
    per_key: dict[str, dict[str, list[float]]] = {}
    failures: dict[str, list[str]] = {}
    for r in results:
        cid, c = r["case_id"], r["caught"]
        rows = per_key.setdefault(cid, {})
        failures.setdefault(cid, []).extend(f"seed {r['seed']}: {f}" for f in r["failures"] if "outside" not in f)
        shaped_keys = [m for m, row in c.get("methods", {}).items() if "signal_rms_error_pct" in row]
        for m, row in c.get("methods", {}).items():
            for k in (SHAPED_KEYS if m in shaped_keys else SORTING_KEYS if m in infer.ATOM_METHODS else METHOD_KEYS):
                rows.setdefault(f"{m}.{k}", []).append(float(row[k]))
        for k, v in c.get("case", {}).items():
            rows.setdefault(k, []).append(float(v))
    ranges = {cid: {key: propose(vals, key.split(".")[-1]) for key, vals in sorted(rows.items())}
              for cid, rows in sorted(per_key.items())}
    doc = {"schema": SCHEMA, "seeds": seeds, "rule": {"rel": REL, "half_width": "max(rel * |mean|, max - min) over the seeds"},
           "ranges": ranges, "measured": {cid: {k: [float(f"{v:.6g}") for v in vals] for k, vals in sorted(rows.items())}
                                          for cid, rows in sorted(per_key.items())},
           "failures": {k: v for k, v in failures.items() if v}, "seconds": round(time.perf_counter() - t0, 1)}
    write_json(paths.root / "measured_ranges.json", doc)
    return doc

