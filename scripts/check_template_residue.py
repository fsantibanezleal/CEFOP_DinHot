#!/usr/bin/env python3
"""T6: an instantiated product carries none of the template's example (ADR-0057, ADR-0078).

The template ships a working example (an SIR model, five EX0*/CTRL cases, their artifacts, the example pages and
diagrams) so a fresh clone runs end to end. A product replaces all of it. Five products shipped pieces of the example
as their own docs; an earlier version of this guard then forbade the path data-pipeline/pipeline/, which is where a
product's own pipeline lives, and skipped everything whenever the sentinel file was present, even in a product that
had never been instantiated. This version:

  - detects the example by its CONTENT (the model, the case ids, the placeholder identity, the example schemas, the
    example references), never by a path a product legitimately keeps;
  - honours the `.template-source` sentinel only in the template repository itself; the sentinel in any other
    repository fails (instantiation deletes it);
  - fails on the template blueprint files that must not ship (STRUCTURE.md, .vscode/).

Scanned set: git-tracked text files. Allowlist: scripts/.template_residue_allow (path fragments, one per line).
Usage: python scripts/check_template_residue.py [repo_root]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SENTINEL = ".template-source"
TEMPLATE_REPO = "CAOS_PRODUCT_TEMPLATE"
# the guard, its allowlist, the history, and the guard's own tests (which must name what it looks for)
SELF = {"scripts/check_template_residue.py", "scripts/.template_residue_allow", "CHANGELOG.md", "tests/test_guards.py"}

# (name, pattern): each one is unambiguous for the template's example.
MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("the example SIR model", re.compile(r"\bSIR\b")),
    ("an example case id", re.compile(r"\b(?:EX0[1-4]_[a-z_]+|CTRL_degenerate)\b")),
    # the placeholder package name, never a longer identifier that starts with it (the Vite plugin caos-product-html)
    ("the placeholder product name", re.compile(r'"name"\s*:\s*"CAOS Product"|\bcaos-product(?:-frontend)?(?![\w-])')),
    ("an example contract schema id", re.compile(r"\bexample\.(?:trace|manifest|index)/v\d+\b")),
    ("an example reference", re.compile(r"\b(?:Kermack|McKendrick|Hethcote)\b")),
    # the example's constant, never a hyphenated id that contains the word (CAOS_Contraste's finding F-SCALED-COVERAGE)
    ("the example immunisation variants", re.compile(r"(?<![\w-])COVERAGE(?![\w-])|herd threshold")),
    ("prose about the example engine", re.compile(r"\bEXAMPLE engine\b|\bteaching engine\b")),
    # the example's executive view (content/executive.json): a product writes its own, never keeps the example's
    ("the example executive view", re.compile(r"Hospital capacity in respiratory seasons|Capacidad hospitalaria en las temporadas respiratorias|Managing-the-flow-of-patients-through-hospital")),
)
FORBIDDEN_FILES = ("STRUCTURE.md", ".vscode/")
# the helper scripts too: precompute.sh and precompute.ps1 named an example case and were never scanned
TEXT_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".md", ".json", ".css", ".html", ".svg",
    ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini", ".sh", ".ps1",
    ".ipynb",  # the example notebooks (template 0.10.000): JSON text, scanned line by line
}


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""


def is_template_repo() -> bool:
    origin = git("remote", "get-url", "origin").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    return origin.rstrip("/").removesuffix(".git").endswith(f"/{TEMPLATE_REPO}") or repo.endswith(f"/{TEMPLATE_REPO}")


def allowlist() -> list[str]:
    f = ROOT / "scripts" / ".template_residue_allow"
    if not f.exists():
        return []
    return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def main() -> int:
    # The files of the product as they stand: tracked and untracked, ignored excluded, on disk. A product instantiated
    # by copying into an existing repository has nothing tracked yet, and a scan of tracked files alone passed it with
    # nothing scanned (CAOS_Contraste, 2026-10-05).
    listed = git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    files = sorted({ln.strip() for ln in listed if ln.strip() and (ROOT / ln.strip()).is_file()})
    if len(files) < 10:
        print(f"::error::check_template_residue: only {len(files)} files to scan; this is not a product tree")
        return 1
    if (ROOT / SENTINEL).exists():
        if is_template_repo():
            print(f"check_template_residue: {SENTINEL} present in {TEMPLATE_REPO}: the example is intentional here.")
            return 0
        print(f"::error::{SENTINEL} is present in a repository that is not {TEMPLATE_REPO}: "
              "run scripts/instantiate.py (it replaces the identity and deletes the sentinel).")
        return 1
    allow = allowlist()
    hits: list[str] = []
    for rel in files:
        if rel in SELF or any(a in rel for a in allow):
            continue
        if any(rel == f or rel.startswith(f) for f in FORBIDDEN_FILES):
            hits.append(f"{rel}: a template blueprint file; delete it")
            continue
        if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = (ROOT / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for name, pat in MARKERS:
                if pat.search(line):
                    hits.append(f"{rel}:{n}: {name}")
                    break
    if not hits:
        print(f"check_template_residue: OK, no example content in {len(files)} tracked files.")
        return 0
    print(f"::error::{len(hits)} line(s) of the template's example remain in this product:")
    for h in hits[:200]:
        print(f"  {h}")
    if len(hits) > 200:
        print(f"  ... and {len(hits) - 200} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
