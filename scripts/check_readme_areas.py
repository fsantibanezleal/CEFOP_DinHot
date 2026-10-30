#!/usr/bin/env python3
"""The README states the repository by areas (CAOS_MANAGE ``conventions/product-notebooks.md`` section 8, template 0.10.000).

The README has a section ``## Areas`` with a table ``| Area | Folder | Status | What it holds |`` and one row per area of the
convention: Web, API, Core pipelines, Packages, Notebooks, Data, Contracts, Documentation, Tests and gates, Deploy. The check
fails, naming the area, on

- a README without the section or without the table, or with the section before the one-paragraph purpose and the live URLs
  (convention section 8: the section comes after them);
- an area without its row, or a row twice;
- a row whose 'What it holds' is shorter than three words, or links (in any cell) a path that does not exist;
- a row whose Status does not start with ``active`` or ``dormant``, or a dormant one with no reason
  (``dormant: <why, three words or more>``);
- a row that does not link its folder (the convention's folder, as a relative markdown link), or links a folder that does not
  exist; the Packages row has no folder and links the package on PyPI (``https://pypi.org/...``) instead, or, for a package installed from its release tag, that tag on
  GitHub (``https://github.com/<owner>/<repo>/releases/tag/<tag>``).

Standard library only. Usage: ``python scripts/check_readme_areas.py [repo_root]``. Exit 0 complete, 1 on any finding.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# (area, folders its row links): the convention's table; the Packages row links PyPI, not a folder
AREAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Web", ("frontend/",)),
    ("API", ("app/",)),
    ("Core pipelines", ("data-pipeline/",)),
    ("Packages", ()),
    ("Notebooks", ("notebooks/",)),
    ("Data", ("data/",)),
    ("Contracts", ("docs/contracts/",)),
    ("Documentation", ("docs/",)),
    ("Tests and gates", ("tests/", "scripts/")),
    ("Deploy", ("deploy/",)),
)
HEAD = ["area", "folder", "status", "what it holds"]
MIN_REASON_WORDS = 3
MIN_HOLDS_WORDS = 3
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
LINK_TEXT = re.compile(r"\[[^\]]*\]\([^)]*\)")
# a package not yet on PyPI is linked by its release tag (convention section 5, decided 2026-10-20)
RELEASE_TAG = re.compile(r"^https://github\.com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/(?:releases/tag|tree)/v?[0-9][0-9A-Za-z.+_-]*/?$")
FENCE = re.compile(r"^\s*(```+|~~~+)")


def section(text: str) -> tuple[list[str], list[str]] | None:
    """(the lines before the section, the lines of ``## Areas``), or None without the section."""
    before: list[str] = []
    body: list[str] | None = None
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        if not fenced and re.match(r"^##\s", line):
            if body is not None:
                break
            if re.match(r"^##\s+Areas\s*$", line):
                body = []
            continue
        if body is not None:
            body.append(line)
        else:
            before.append(line)
    return None if body is None else (before, body)


def preamble_findings(before: list[str]) -> list[str]:
    """The purpose (a prose line that is not a heading, a badge or a table row) and a live URL come before the section."""
    prose = [ln for ln in before if ln.strip() and not ln.lstrip().startswith(("#", "[![", "|", "<", "```", "~~~"))]
    urls = [ln for ln in before if re.search(r"https?://", ln)]
    if prose and urls:
        return []
    missing = " and ".join(w for w, ok in (("the one-paragraph purpose", bool(prose)), ("the live URLs", bool(urls))) if not ok)
    return [f"README.md: the section '## Areas' comes after the purpose and the live URLs (convention section 8), and {missing} "
            "is missing before it"]


def findings_of(root: Path) -> list[str]:
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md: missing"]
    parts = section(readme.read_text(encoding="utf-8"))
    if parts is None:
        return ["README.md: no section '## Areas' (the repository stated by areas, after the purpose and the live URLs)"]
    before, body = parts
    rows: dict[str, list[list[str]]] = {}
    header = False
    for line in body:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if [c.lower() for c in cells] == HEAD:
            header = True
        elif cells and not set(cells[0]) <= set("-: "):
            rows.setdefault(cells[0], []).append(cells)
    if not header:
        return [f"README.md: the section '## Areas' has no table with the columns {' | '.join(HEAD)}"]
    out: list[str] = preamble_findings(before)
    for area, folders in AREAS:
        found = rows.get(area, [])
        if not found:
            out.append(f"README.md: the area {area!r} has no row in '## Areas'")
            continue
        if len(found) > 1:
            out.append(f"README.md: the area {area!r} has more than one row")
        cells = found[0]
        if len(cells) < 4 or not cells[3]:
            out.append(f"README.md: the area {area!r} row has no 'What it holds' cell (four cells: {' | '.join(HEAD)})")
            continue
        holds = re.sub(r"[^A-Za-z ]", " ", LINK_TEXT.sub(" ", cells[3]))
        if len([w for w in holds.split() if len(w) > 1]) < MIN_HOLDS_WORDS:
            out.append(f"README.md: the area {area!r} says too little in 'What it holds' (three words or more: what the area contains)")
        status = cells[2]
        word = status.split(":", 1)[0].strip().lower()
        if word not in {"active", "dormant"}:
            out.append(f"README.md: the area {area!r} has no status ('active' or 'dormant: <reason>'), got {status!r}")
        elif word == "dormant" and len(status.split(":", 1)[1].split() if ":" in status else []) < MIN_REASON_WORDS:
            out.append(f"README.md: the area {area!r} is dormant with no reason ('dormant: <why, {MIN_REASON_WORDS} words or more>')")
        links = LINK.findall(cells[1])
        local = [t.split("#")[0] for t in links if not re.match(r"^[a-z]+:", t)]
        # a link of the other cells (the area's own README or doc) must resolve too
        extra = [t.split("#")[0] for t in LINK.findall(cells[2] + " " + cells[3]) if not re.match(r"^[a-z]+:", t) and t.split("#")[0]]
        for t in [*local, *extra]:
            if not (root / t).exists():
                out.append(f"README.md: the area {area!r} links {t!r}, which does not exist")
        for f in folders:
            if f not in {t if t.endswith("/") else t + "/" for t in local}:
                out.append(f"README.md: the area {area!r} does not link its folder {f} (a relative markdown link)")
        if not folders and not any("pypi.org/" in t or RELEASE_TAG.match(t) for t in links):
            out.append(f"README.md: the area {area!r} links no package on PyPI (each package the product publishes or consumes), "
                       "or, for one installed from its release tag, that release tag on GitHub")
    return out


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    findings = findings_of(root)
    if findings:
        print("README AREAS CHECK FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 1
    print(f"check_readme_areas: OK, {len(AREAS)} areas stated, each active or dormant, every folder link present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
