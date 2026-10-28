#!/usr/bin/env python3
"""T7 addition (shell 0.14.0, ADR-0017 section 2.1): an animated SVG of the product carries its static final frame.

Every ``.svg`` under ``frontend/public/`` and ``frontend/src/`` is read by the shell's own analysis (``analyseSvgAnimation`` and
``animationFailures`` of ``gate/areas.mjs`` in the installed shell, through ``scripts/svg_animation.mjs``; the guard holds no rule
of its own, so it and the gate's G17 cannot disagree). A file with CSS keyframes or SMIL fails when it has no
``@media (prefers-reduced-motion: reduce)`` block, when that block does not stop its CSS animation (``animation: none``), or when
it plays for more than ten seconds. A still SVG is not checked further.

It fails, never passes, when node or the installed shell is absent. Run after ``npm ci`` in frontend/ (CI's checks job does).
Usage: python scripts/check_svg_animation.py [repo root]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
AREAS = FRONTEND / "node_modules" / "@fasl-work" / "caos-app-shell" / "gate" / "areas.mjs"
HELPER = ROOT / "scripts" / "svg_animation.mjs"
FOLDERS = ("public", "src")


def svg_files() -> list[Path]:
    return sorted(p for folder in FOLDERS for p in (FRONTEND / folder).rglob("*.svg") if p.is_file())


def main() -> int:
    node = shutil.which("node")
    if node is None:
        print("check_svg_animation: FAIL: node is not installed; the guard reuses the shell's JavaScript analysis")
        return 1
    if not AREAS.is_file():
        print(f"check_svg_animation: FAIL: {AREAS.relative_to(ROOT).as_posix()} is absent; run 'npm ci' in frontend/ with the pinned shell")
        return 1
    files = svg_files()
    if not files:
        print("check_svg_animation: OK (0 svg, 0 animated)")
        return 0
    run = subprocess.run([node, str(HELPER), str(FRONTEND), *map(str, files)], capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    if run.returncode != 0:
        print(f"check_svg_animation: FAIL: the shell analysis did not run: {run.stderr.strip()[:300]}")
        return 1
    report = json.loads(run.stdout)
    problems = [f"{Path(r['file']).relative_to(ROOT).as_posix()}: {m}" for r in report for m in r["failures"]]
    animated = sum(1 for r in report if r["animated"])
    if problems:
        print(f"check_svg_animation: FAIL ({len(problems)} problem(s) in {len(report)} svg, {animated} animated)")
        for p in problems:
            print(f"  - {p}")
        print("  An animated SVG needs a @media (prefers-reduced-motion: reduce) block that stops it (animation: none) and shows the "
              "static final frame, and plays for ten seconds at most (docs/guides/06_executive-brief.md, section 5.1).")
        return 1
    print(f"check_svg_animation: OK ({len(report)} svg, {animated} animated, each with its reduced-motion block)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
