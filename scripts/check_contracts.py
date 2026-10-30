"""Check a product contract catalog (phase 2 of the contract-first method).

The template is ``tools/agents/contracts-template.md``: one table, one row per contract (boundary or
model slot). The check is deterministic, offline, and reports every problem:

* a required column is absent, or a required cell is empty (``model io`` may be empty: it marks model slots)
* the schema file, a producer or consumer test, or a provider path does not exist under the repo root
* a provider has no known kind (``stub``, ``simulator``, ``fixture``, ``baseline``) or no path
* a model slot (non-empty ``model io``) has no ``baseline`` provider
* an id appears twice
* the ``documents`` column (added in template 0.09.000) is absent, empty, or malformed: a cell is ``-`` (no committed
  document) or globs relative to the repository root separated by ``, `` (``!`` excludes; ``path#Component`` on a row whose
  schema file is the OpenAPI document); a path outside the repository (``..``, absolute) is an error

Cell formats: a test cell is ``path`` or ``path::test_name`` (several separated by commas); a provider
cell is ``kind:path``. An optional trailing ``status`` column is read by ``skeleton_check.py``.

Exit codes: 0 catalog is sound, 1 defective or unreadable. A table of the rows is printed.

Usage (from the CAOS_MANAGE root, with the repo .venv)::

    python tools/agents/contracts_check.py <catalog.md> [--repo-root <dir>]
"""
# Vendored from fsantibanezleal/CAOS_MANAGE tools/agents/contracts_check.py at bd0251f2; update from the source, never edit here. The source carries the `documents` column check (RELEASE_COLUMNS, split_documents,
# parse_document_glob, document_problems) since template 0.09.000; check_documents.py imports the parser.

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED = (
    "id", "version", "owner", "schema file", "example", "producer test", "consumer test",
    "missing-data behavior", "provider", "swap test",
)
# required columns added after the first catalog format: name -> the template release that added it (a tuple, not a version
# literal: scripts/check_version_coherence.py reads a literal in code as a stale version)
RELEASE_COLUMNS = {"documents": "%d.%02d.%03d" % (0, 9, 0)}
COLUMNS = REQUIRED + ("model io",)
PROVIDER_KINDS = ("stub", "simulator", "fixture", "baseline")
_NONE = {"", "-", "n/a", "na", "none", "no"}

_FENCE = re.compile(r"^\s*```")
_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def _split(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_catalog(text: str) -> tuple[list[str], list[dict[str, str]]] | None:
    """The first table that has an ``id`` and a ``provider`` column: (header, rows). None if there is none.

    Rows whose cells are all blank are dropped; text in fenced blocks is ignored.
    """
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    in_fence = False
    for line in text.splitlines() + [""]:
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _ROW.match(line):
            cells = _split(line)
            if header is None:
                header, rows = [c.lower() for c in cells], []
            elif all(_SEPARATOR_CELL.match(c) or not c for c in cells) and any(_SEPARATOR_CELL.match(c) for c in cells):
                continue
            elif any(cells):
                rows.append(dict(zip(header, cells)))
        elif header is not None:
            tables.append((header, rows))
            header = None
    for found in tables:
        if "id" in found[0] and "provider" in found[0]:
            return found
    return tables[0] if tables else None


def parse_provider(cell: str) -> tuple[str, str]:
    """(kind, path) of a ``kind:path`` provider cell; a trailing ``(active)`` style marker is dropped."""
    cell = re.sub(r"\((?:active|real)\)", "", cell.strip().strip("`"), flags=re.IGNORECASE).strip()
    kind, _, path = cell.partition(":")
    return kind.strip().lower(), path.strip().strip("`").split(" ")[0] if path.strip() else ""


def _paths(cell: str) -> list[str]:
    """Paths of a test or schema cell: comma separated, ``::node`` and ``#anchor`` suffixes removed."""
    out = []
    for part in cell.split(","):
        path = part.strip().strip("`").split("::")[0].split("#")[0].strip()
        if path:
            out.append(path)
    return out


_DRIVE = re.compile(r"^[A-Za-z]:")


def split_documents(cell: str) -> list[str]:
    """The entries of a ``documents`` cell: ``[]`` for ``-`` (or an empty cell), else the globs, ``, `` separated."""
    cell = cell.strip()
    if cell in ("", "-"):
        return []
    return [part.strip().strip("`") for part in cell.split(", ") if part.strip()]


def parse_document_glob(entry: str) -> tuple[bool, str, str]:
    """(exclude, glob, component) of one entry: a leading ``!`` excludes, ``#Component`` names an OpenAPI component."""
    exclude = entry.startswith("!")
    glob, _, component = entry.lstrip("!").partition("#")
    return exclude, glob.strip(), component.strip()


def document_problems(row: dict[str, str]) -> list[str]:
    """What is wrong with one row's ``documents`` cell (see the module docstring); empty when it is sound."""
    cid = row.get("id") or "(unnamed)"
    cell = row.get("documents", "").strip()
    if cell == "":
        return []  # the empty cell is reported with the other required cells
    entries = split_documents(cell)
    if not entries:
        return []
    problems: list[str] = []
    openapi = row.get("schema file", "").strip().strip("`").endswith("openapi.json")
    included = 0
    for entry in entries:
        exclude, glob, component = parse_document_glob(entry)
        if entry == "-":
            problems.append(f"{cid}: documents: '-' stands alone, it is not a glob")
            continue
        if not glob:
            problems.append(f"{cid}: documents: empty glob in '{entry}'")
            continue
        parts = glob.replace("\\", "/").split("/")
        if "\\" in glob or glob.startswith("/") or _DRIVE.match(glob) or ".." in parts:
            problems.append(f"{cid}: documents: '{glob}' is outside the repository (use a path relative to the root, '/' separated, no '..')")
        if not exclude:
            included += 1
            if openapi and not component:
                problems.append(f"{cid}: documents: '{glob}' needs a component (path#ComponentName): the schema file is an OpenAPI document")
        if component and (exclude or not openapi):
            problems.append(f"{cid}: documents: '{entry}' names a component, only a non-excluded glob of an OpenAPI row may")
    if included == 0:
        problems.append(f"{cid}: documents: no glob to include (only exclusions)")
    return problems


def is_model_slot(row: dict[str, str]) -> bool:
    return row.get("model io", "").strip().lower() not in _NONE


def check_text(text: str, repo_root: Path) -> tuple[list[dict[str, str]], list[str]]:
    """(rows, problems) for a catalog document."""
    parsed = parse_catalog(text)
    if parsed is None:
        return [], ["no contract catalog table found"]
    header, rows = parsed
    problems: list[str] = []
    absent = [c for c in REQUIRED if c not in header]
    if absent:
        return rows, [f"catalog lacks column(s): {', '.join(absent)}"]
    late = [f"'{c}' (added in template {rel}: one cell per row, '-' for a contract with no committed document, else globs)"
            for c, rel in RELEASE_COLUMNS.items() if c not in header]
    if late:
        return rows, [f"catalog lacks column {', '.join(late)}"]
    if not rows:
        return rows, ["catalog has no contract rows"]

    seen: set[str] = set()
    for row in rows:
        cid = row["id"] or "(unnamed)"
        if row["id"] in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(row["id"])
        for column in REQUIRED + tuple(RELEASE_COLUMNS):
            if not row.get(column, "").strip():
                problems.append(f"{cid}: empty {column}")
        problems += document_problems(row)
        for column in ("schema file", "producer test", "consumer test"):
            for path in _paths(row.get(column, "")):
                if not (repo_root / path).exists():
                    problems.append(f"{cid}: {column} path not found: {path}")
        kind, path = parse_provider(row.get("provider", ""))
        if row.get("provider", "").strip():
            if kind not in PROVIDER_KINDS:
                problems.append(f"{cid}: provider kind '{kind}' is not one of {', '.join(PROVIDER_KINDS)}")
            elif not path:
                problems.append(f"{cid}: provider has no path (expected kind:path)")
            elif not (repo_root / path).exists():
                problems.append(f"{cid}: provider path not found: {path}")
        if is_model_slot(row) and kind != "baseline":
            problems.append(f"{cid}: model slot without a baseline provider (provider is '{kind or 'empty'}')")
    return rows, problems


def _print_table(rows: list[dict[str, str]]) -> None:
    print(f"{'id':<28} {'version':<9} {'provider':<44} model")
    for row in rows:
        print(f"{row.get('id', ''):<28} {row.get('version', ''):<9} {row.get('provider', ''):<44} "
              f"{'yes' if is_model_slot(row) else 'no'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a contract catalog (contract-first phase 2).")
    parser.add_argument("catalog", type=Path, help="path to the catalog markdown file")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="root that catalog paths are relative to")
    args = parser.parse_args(argv)
    try:
        text = args.catalog.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"DEFECTIVE: cannot read {args.catalog}: {exc}")
        return 1
    rows, problems = check_text(text, args.repo_root)
    if rows:
        _print_table(rows)
    if problems:
        print(f"DEFECTIVE: {len(problems)} problem(s) in {args.catalog}")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"OK: {len(rows)} contract(s) in {args.catalog}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
