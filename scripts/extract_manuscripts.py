#!/usr/bin/env python3
"""Re-extract every manuscript number that reads the committed bake and benchmark, in dependency order.

Run it from the repository root with the pipeline environment after every promoted bake or benchmark (``02_generate-data --release``),
before a manuscript is revised or published, so that no paper prints a number of an earlier bake:

    .venv-pipeline/Scripts/python.exe scripts/extract_manuscripts.py            # every step
    .venv-pipeline/Scripts/python.exe scripts/extract_manuscripts.py --dry-run  # print the steps only
    .venv-pipeline/Scripts/python.exe scripts/extract_manuscripts.py --skip-engine

The steps, in the order their inputs require:

1. ``device-aware``: the device-aware refinement paper's bake and benchmark readings (``measure.py --parts ""`` re-reads the bake and
   the benchmark only and keeps its measured parts); the technical report reads its ``beyond.json`` and imports its macros.
2. ``efficiency-uniformity``: the continuation paper's stored-curve readings of the benchmark and the bake (``measure.py --parts
   stored``); the report imports its macros.
3. ``report-acceptance``: the measured acceptance quantity of every method on the current engine (``acceptance.py``; it runs the
   engine, minutes, and reads ``data/derived/models/metrics.json``). ``--skip-engine`` leaves the committed ``acceptance.json``.
4. ``report``: the report's macros and tables (``extract.py``; reads ``acceptance.json``, ``beyond.json``, the bake, the benchmark,
   the SDD's method ladder and the warm-start paper's macros) and writes ``studio.json``.
5. ``report-methods``: the per-method macros and tables (``extract_methods.py``; reads ``studio.json`` and ``acceptance.json``).

The flicker-bounded, aberration-robust and learned warm-start papers measure their own runs and read no benchmark cell; the learned
warm-start paper checks ``data/derived/models/warmstart-model-rejected.json`` before it runs, so a changed record shows there.
Stops at the first failing step and exits with its code.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MS = "manuscripts"

# (name, script relative to the root, arguments, runs the engine)
STEPS: list[tuple[str, str, list[str], bool]] = [
    ("device-aware", f"{MS}/device-aware-refinement/data/measure.py", ["--parts", ""], False),
    ("efficiency-uniformity", f"{MS}/efficiency-uniformity-front/data/measure.py", ["--parts", "stored"], False),
    ("report-acceptance", f"{MS}/holographic-trap-studio/data/acceptance.py", [], True),
    ("report", f"{MS}/holographic-trap-studio/data/extract.py", [], False),
    ("report-methods", f"{MS}/holographic-trap-studio/data/extract_methods.py", [], False),
]


def plan(only: list[str] | None = None, skip_engine: bool = False) -> list[tuple[str, list[str]]]:
    """The commands to run, in order: (name, argv)."""
    names = [s[0] for s in STEPS]
    unknown = sorted(set(only or []) - set(names))
    if unknown:
        raise SystemExit(f"unknown steps {unknown}; known: {names}")
    out = []
    for name, script, args, engine in STEPS:
        if only and name not in only:
            continue
        if skip_engine and engine:
            continue
        out.append((name, [sys.executable, script, *args]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="comma-separated step names (default: every step)")
    ap.add_argument("--skip-engine", action="store_true", help="leave the steps that run the engine (acceptance.py)")
    ap.add_argument("--dry-run", action="store_true", help="print the steps and exit")
    a = ap.parse_args(argv)
    steps = plan(a.only.split(",") if a.only else None, a.skip_engine)
    for name, cmd in steps:
        shown = " ".join(c if c else '""' for c in cmd[1:])
        if a.dry_run:
            print(f"{name}: {shown}")
            continue
        t0 = time.perf_counter()
        print(f"[{name}] {shown}", flush=True)
        rc = subprocess.run(cmd, cwd=ROOT).returncode
        print(f"[{name}] exit {rc} in {time.perf_counter() - t0:.0f} s", flush=True)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
