"""List the boundaries of a contract catalog that are still served by a provider (phase 3, walking skeleton).

A provider (stub, simulator, fixture, baseline) behind a contract is scaffolding: allowed while the
skeleton is built, never counted as done. This check keeps listing every boundary still on a provider.

A row is served by a provider when its optional ``status`` column says ``active``, ``provider``,
``stub``, ``simulator``, ``fixture`` or ``baseline``; it is real when the status says ``real`` or
``live``. Without a ``status`` column, a row is served by a provider when its ``provider`` cell
carries the marker ``active`` (for example ``stub:path/x.py (active)``).

Exit codes: 0 every boundary is real, 2 at least one boundary is still on a provider, 1 the catalog
is malformed (no table, no rows, no ``id`` or ``provider`` column, a blank or unknown status).

Usage (from the CAOS_MANAGE root, with the repo .venv)::

    python tools/agents/skeleton_check.py <catalog.md>
"""
# Vendored from fsantibanezleal/CAOS_MANAGE tools/agents/skeleton_check.py at bd0251f2; update from the source, never edit here.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_contracts import parse_catalog

REAL = {"real", "live"}
ON_PROVIDER = {"active", "provider", "stub", "simulator", "fixture", "baseline"}


def check_text(text: str) -> tuple[int, list[dict[str, str]], list[str]]:
    """(exit code, rows still on a provider, problems)."""
    parsed = parse_catalog(text)
    if parsed is None:
        return 1, [], ["no contract catalog table found"]
    header, rows = parsed
    missing = [c for c in ("id", "provider") if c not in header]
    if missing:
        return 1, [], [f"catalog lacks column(s): {', '.join(missing)}"]
    if not rows:
        return 1, [], ["catalog has no contract rows"]
    has_status = "status" in header
    active: list[dict[str, str]] = []
    problems: list[str] = []
    for row in rows:
        cid = row["id"] or "(unnamed)"
        if not row["id"]:
            problems.append("a row has no id")
        if has_status:
            status = row.get("status", "").strip().lower()
            if status in REAL:
                continue
            if status in ON_PROVIDER:
                active.append(row)
            else:
                problems.append(f"{cid}: status '{status}' is not one of {', '.join(sorted(REAL | ON_PROVIDER))}")
        elif re.search(r"\bactive\b", row["provider"], re.IGNORECASE):
            active.append(row)
    if problems:
        return 1, active, problems
    return (2 if active else 0), active, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List boundaries still served by a provider (walking skeleton).")
    parser.add_argument("catalog", type=Path, help="path to the catalog markdown file")
    args = parser.parse_args(argv)
    try:
        text = args.catalog.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"DEFECTIVE: cannot read {args.catalog}: {exc}")
        return 1
    code, active, problems = check_text(text)
    if problems:
        print(f"DEFECTIVE: {len(problems)} problem(s) in {args.catalog}")
        for problem in problems:
            print(f"- {problem}")
        return 1
    if active:
        print(f"INCOMPLETE: {len(active)} boundary(ies) still served by a provider")
        for row in active:
            print(f"- {row['id']}: {row['provider']}")
        return 2
    print("OK: every boundary is real")
    return 0


if __name__ == "__main__":
    sys.exit(main())
