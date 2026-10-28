"""Offline pipeline orchestrator and CLI.

The canonical bake is an explicit release operation. Tests and CI smoke runs must pass ``--output`` so they cannot mutate
committed scientific evidence. Never in CI (ADR-0074).

    python data-pipeline/run.py                           # all cases, then the readiness document
    python data-pipeline/run.py C02_grid_feedback         # one case
    python data-pipeline/run.py all --only C01_square_grid,C12_calibration --output "$CAOS_TEMP_ROOT/bake"
    python data-pipeline/run.py all --resume              # skip cases whose manifest has the same inputs and version
    python data-pipeline/run.py all --allow-missing-methods   # sandbox bake of the methods present (never canonical)
    python data-pipeline/run.py benchmark [--seeds 20] [--workers 12] [--reduced] [--only G1,G2] [--methods M04,M06]
    python data-pipeline/run.py readiness                 # recompute data/derived/readiness.json from the catalog (no bake)
    python data-pipeline/run.py cases                     # write data/examples/cases.json from the registry
    python data-pipeline/run.py units                     # the units gate over the shipped artifacts
    python data-pipeline/run.py ranges --output "$CAOS_TEMP_ROOT/m" # measure each case on 3 seeds and propose its expected ranges
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from . import __version__, registry
from .bake import BakeFailed, bake_case
from .core import readiness, units
from .core.manifest import build_index, index_entry_baked, index_entry_refused
from .io.contract import REPO_ROOT
from .io.formats import read_json, write_json
from .stages import preprocess

# data-pipeline/pipeline/pipeline.py -> parents[2] = repo root (works under `pip install -e .` too)
DERIVED = REPO_ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
MODELS = REPO_ROOT / "models"

REPO = REPO_ROOT  # the repository the readiness document describes (catalog, VERSION, cases table)

STAGES = ("preprocess", "feature_extraction", "train", "infer", "evaluate", "export")
COMMANDS = ("all", "readiness", "benchmark", "cases", "units", "ranges")


@dataclass(frozen=True)
class PipelinePaths:
    root: Path
    manifests: Path
    models: Path

    @classmethod
    def from_output(cls, output: str | Path | None = None) -> PipelinePaths:
        if output is None:
            return cls(root=DERIVED, manifests=MANIFESTS, models=MODELS)
        root = Path(output).resolve()
        return cls(root=root, manifests=root / "manifests", models=root / "models")


def write_cases(path: Path | None = None) -> Path:
    """Write the registry's twelve default records to ``data/examples/cases.json`` (one record per line)."""
    out = path or (REPO / "data" / "examples" / "cases.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in registry.records()]
    out.write_text("[\n" + ",\n".join(rows) + "\n]\n", encoding="utf-8")
    return out


def _unchanged(rec: dict, manifest_path: Path, allow_missing: bool) -> bool:
    """A manifest of this version whose params are the record's: the case need not be baked again (``--resume``)."""
    if not manifest_path.is_file():
        return False
    m = read_json(manifest_path)
    if m.get("engine", {}).get("version") != __version__:
        return False
    keys = ("setup", "device", "target", "aberration", "budget", "seed", "feedback", "dynamics", "rearrangement")
    same = all(m["params"].get(k) == rec[k] for k in keys)
    return same and (allow_missing or m["params"]["methods"] == rec["methods"])


def _refused_reason(rej: dict) -> dict:
    return {"en": rej["reason"], "es": rej["reason_es"]}


def write_readiness(paths: PipelinePaths) -> dict:
    """Compute the readiness document for the repository and the outputs under ``paths``, and write it."""
    doc = readiness.compute(repo_root=REPO, derived_root=paths.root, models_dir=paths.models)
    readiness.write(paths.root, doc)
    return doc


MAX_WORKERS = 12
SINGLE_THREAD = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")   # one BLAS thread per case process


def peak_memory_mb() -> float:
    """Peak resident memory of this process in MB (0.0 when the platform gives no figure)."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

            c = Counters()
            c.cb = ctypes.sizeof(c)
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
            ok = k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
            return c.PeakWorkingSetSize / 2**20 if ok else 0.0
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / 1024.0 / (1024.0 if sys.platform == "darwin" else 1.0)
    except Exception:  # noqa: BLE001 - a missing figure is reported as 0, never a bake failure
        return 0.0


def _bake_job(job: dict) -> dict:
    """One case in a worker process: the manifest, the failures, the wall seconds and the peak memory of the process."""
    t0 = time.perf_counter()
    manifest, fails = bake_case(job["rec"], derived_dir=Path(job["root"]), manifests_dir=Path(job["manifests"]),
                                models_dir=Path(job["models"]), allow_missing=job["allow_missing"],
                                contract_flags=job["flags"])
    return {"case_id": job["rec"]["case_id"], "manifest": manifest, "failures": fails,
            "seconds": time.perf_counter() - t0, "peak_mb": peak_memory_mb()}


def bake_jobs(jobs: list[dict], workers: int = MAX_WORKERS, fn=_bake_job) -> list[dict]:
    """Bake the jobs in parallel, one case per process (methods within a case run in sequence), at most ``MAX_WORKERS``
    processes; the results come back in the order of ``jobs`` whatever the completion order, so the outputs are the same
    as a sequential bake's. One BLAS thread per process keeps the warm timings that decide the lane stable under load."""
    n = max(1, min(int(workers), MAX_WORKERS, len(jobs)))
    if n == 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    saved = {k: os.environ.get(k) for k in SINGLE_THREAD}
    os.environ.update({k: "1" for k in SINGLE_THREAD})   # inherited by the spawned workers
    try:
        with ProcessPoolExecutor(max_workers=n) as pool:
            return list(pool.map(fn, jobs))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run_all(seed: int | None = None, *, output_root: str | Path | None = None, only: list[str] | None = None,
            resume: bool = False, allow_missing: bool = False, cases_path: str | Path | None = None,
            workers: int = 1) -> list[dict]:
    """Bake every accepted case (or ``only`` those), write the index and the readiness document, and raise ``BakeFailed``
    at the end when any case failed (the artifacts of the cases that did bake are written either way)."""
    paths = PipelinePaths.from_output(output_root)
    report, _source = preprocess.run(cases_path, REPO)
    ids = [r["case_id"] for r in report.accepted]
    unknown = sorted(set(only or []) - set(ids) - {r["case_id"] for r in report.rejected})
    if unknown:
        raise KeyError(f"unknown case(s) in --only: {unknown}; known: {ids + [r['case_id'] for r in report.rejected]}")
    failures: list[str] = []
    entries: list[dict] = []
    jobs: list[dict] = []
    for rec in report.accepted:
        rec = dict(rec, seed=rec["seed"] if seed is None else seed)
        mp = paths.manifests / f"{rec['case_id']}.json"
        selected = only is None or rec["case_id"] in only
        if selected and not (resume and _unchanged(rec, mp, allow_missing)):
            flags = [f for f in report.flagged if f.get("case_id") == rec["case_id"]]
            jobs.append({"rec": rec, "root": str(paths.root), "manifests": str(paths.manifests), "models": str(paths.models),
                         "allow_missing": allow_missing, "flags": flags})
    t0 = time.perf_counter()
    results = bake_jobs(jobs, workers)
    if results:
        print(f"bake: {len(results)} case(s) in {time.perf_counter() - t0:.1f} s on {min(workers, MAX_WORKERS, len(jobs))} "
              f"worker(s); peak memory of one case process {max(r['peak_mb'] for r in results):.0f} MB; slowest "
              + ", ".join(f"{r['case_id']} {r['seconds']:.0f} s" for r in sorted(results, key=lambda r: -r["seconds"])[:3]),
              file=sys.stderr)
    for r in results:
        failures += r["failures"]
    for rec in report.accepted:
        if (paths.manifests / f"{rec['case_id']}.json").is_file():
            entries.append(index_entry_baked(registry.case_for(rec)))
    for rej in report.rejected:
        entries.append(index_entry_refused(registry.case_for({"case_id": rej["case_id"]}), _refused_reason(rej)))
    baked = [e["case_id"] for e in entries if e["status"] == "baked"]
    if baked:
        default = registry.default_case() if registry.default_case() in baked else sorted(baked)[0]
        write_json(paths.manifests / "index.json", build_index(entries, default))
    write_readiness(paths)
    if failures:
        raise BakeFailed(failures)
    return entries


def precompute(case_id: str, seed: int | None = None, *, output_root: str | Path | None = None,
               allow_missing: bool = False, cases_path: str | Path | None = None) -> dict:
    """Bake one case into ``output_root`` (the sandbox roots of the tests when None) and return its manifest.

    Raises ``KeyError`` for an unknown id, ``ValueError`` naming the reason for a case contract 1 refuses, and
    ``BakeFailed`` when the case fails."""
    paths = PipelinePaths.from_output(output_root)
    report, _ = preprocess.run(cases_path, REPO)
    for rej in report.rejected:
        if rej["case_id"] == case_id:
            raise ValueError(f"{case_id} is refused by contract 1: {rej['reason']}")
    rec = next((r for r in report.accepted if r["case_id"] == case_id), None)
    if rec is None:
        raise KeyError(f"unknown case: {case_id!r}")
    rec = dict(rec, seed=rec["seed"] if seed is None else seed)
    flags = [f for f in report.flagged if f.get("case_id") == case_id]
    manifest, failures = bake_case(rec, derived_dir=paths.root, manifests_dir=paths.manifests, models_dir=paths.models,
                                   allow_missing=allow_missing, contract_flags=flags)
    if failures:
        raise BakeFailed(failures)
    assert manifest is not None
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.pipeline")
    ap.add_argument("case", nargs="?", default="all", help=f"a case id, or one of {', '.join(COMMANDS)}")
    ap.add_argument("--seed", type=int, help="override every record's seed (the record's own seed by default)")
    ap.add_argument("--output", type=Path, help="sandbox output root; omit only for an intentional canonical release bake")
    ap.add_argument("--only", help="all: case ids; benchmark: geometry ids (comma separated)")
    ap.add_argument("--resume", action="store_true", help="skip cases (bake) or cells (benchmark) already done with the "
                    "same version and inputs")
    ap.add_argument("--allow-missing-methods", action="store_true",
                    help="bake the methods that are registered; a method that is not is flagged (never canonical)")
    ap.add_argument("--cases", type=Path, help="a source document of cases other than data/examples/cases.json")
    ap.add_argument("--seeds", type=int, default=20, help="benchmark: seeds per cell")
    ap.add_argument("--workers", type=int, default=12, help="all, benchmark: worker processes (at most 12)")
    ap.add_argument("--reduced", action="store_true", help="benchmark: the reduced grid of the tests (not for release)")
    ap.add_argument("--methods", help="benchmark: method ids (comma separated)")
    args = ap.parse_args(argv)
    paths = PipelinePaths.from_output(args.output)
    only = args.only.split(",") if args.only else None
    try:
        if args.case == "readiness":
            doc = write_readiness(paths)
            print(f"readiness -> {paths.root / 'readiness.json'} " + ", ".join(f"{e['id']}={e['state']}" for e in doc["contracts"]))
        elif args.case == "cases":
            print(f"cases -> {write_cases()}")
        elif args.case == "units":
            problems = units.check_tree(paths.root)
            print("\n".join(problems) if problems else f"units gate: OK over {paths.root}")
            return 1 if problems else 0
        elif args.case == "benchmark":
            from .stages import benchmark
            doc = benchmark.run(paths.root, seeds=args.seeds, workers=args.workers, reduced=args.reduced,
                                geometries=only, methods=args.methods.split(",") if args.methods else None,
                                resume=args.resume)
            print(f"benchmark -> {paths.root / 'benchmark' / 'results.json'}: {len(doc['rows'])} rows, "
                  f"{len(doc.get('skipped', []))} skipped cells")
            write_readiness(paths)
        elif args.case == "ranges":
            from . import ranges
            doc = ranges.measure(paths.root, seeds=args.seeds if args.seeds != 20 else ranges.SEEDS, workers=args.workers,
                                 only=only, allow_missing=True, cases_path=args.cases)
            print(f"measured ranges -> {paths.root / 'measured_ranges.json'}: {sum(len(v) for v in doc['ranges'].values())} "
                  f"ranges over {len(doc['ranges'])} cases in {doc['seconds']} s")
        elif args.case == "all":
            entries = run_all(args.seed, output_root=args.output, only=only, resume=args.resume,
                              allow_missing=args.allow_missing_methods, cases_path=args.cases, workers=args.workers)
            print(f"precomputed {sum(e['status'] == 'baked' for e in entries)} cases, "
                  f"{sum(e['status'] == 'refused' for e in entries)} refused -> {paths.root}")
            for e in entries:
                print(f"  {e['case_id']:26s} [{e['category']['en']}] {e['status']}")
            print(f"index -> {paths.manifests / 'index.json'}")
        else:
            m = precompute(args.case, args.seed, output_root=args.output, allow_missing=args.allow_missing_methods,
                           cases_path=args.cases)
            print(f"precomputed {args.case}: lane={m['lane']} bytes={m['artifact']['bytes']} methods={sorted(m['methods'])} "
                  f"-> {paths.root / m['artifact']['path']}")
    except BakeFailed as exc:
        print(f"BAKE FAILED: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 0 if "refused by contract 1" in str(exc) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
