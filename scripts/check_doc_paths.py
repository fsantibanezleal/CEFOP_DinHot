#!/usr/bin/env python3
"""T6: every repository path a document names exists (failure class 12: docs that point at files that moved).

Checks, in every tracked Markdown file:
  - relative link targets ([text](path), images included), resolved against the file's folder;
  - inline code spans that name a repository path (start with a top-level folder or file of this repository).
External links, anchors, globs and placeholders (<...>, {...}, *) are skipped. The gates named by a feature's
requirements.md opened `Status: planned` are skipped too: they are the tests the unit will write, and
scripts/check_sdd.py holds them to naming a file (the two guards agree). Exit 1 on any missing path.

A path exists when the repository holds it as git sees it (its tracked and untracked-not-ignored files, and every
folder above them), never because this machine's disk has it: a gate's screenshots or a build output passed the
check on the machine that had made them and failed it in CI (CAOS_Contraste, 2026-10-05). A document may still name a
path the repository ignores on purpose (`git check-ignore`), an output its tools write; local runs and CI agree.
Usage: python scripts/check_doc_paths.py [repo_root]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE = re.compile(r"`([^`\s]+)`")
SKIP = re.compile(r"^(?:[a-z]+:|#|mailto:)|[<>{}*$]|\.\.\.")
PLANNED = re.compile(r"^Status:\s*planned", re.M | re.I)


def planned_requirements(rel: str, text: str) -> bool:
    """A feature's requirements opened before its gates exist (check_sdd.py's `Status: planned`)."""
    parts = rel.split("/")
    return (len(parts) == 5 and parts[:3] == ["docs", "design", "features"] and parts[4] == "requirements.md"
            and PLANNED.search("\n".join(text.splitlines()[:6])) is not None)


def tracked() -> list[str]:
    # tracked and untracked, ignored excluded: a tree not yet committed is checked too
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return sorted({ln.strip() for ln in out.splitlines() if ln.strip()})


def ignored(rel: str) -> bool:
    """A path the repository's ignore rules cover: an output its tools write, whether or not it exists here. A folder
    named alone is also tried with its slash, which a folder-only rule (`out/`) needs when the folder is absent."""
    return any(subprocess.run(["git", "check-ignore", "-q", "--no-index", p], cwd=ROOT).returncode == 0
               for p in (rel, f"{rel}/"))


def main() -> int:
    files = [f for f in tracked() if (ROOT / f).is_file()]
    if not any(f.endswith(".md") for f in files):
        print("doc paths: no Markdown file to check; this is not a product tree")
        return 1
    tops = {f.split("/", 1)[0] for f in files}
    # what the repository holds: its files and every folder above them
    present = set(files)
    for f in files:
        parts = f.split("/")
        present.update("/".join(parts[:i]) for i in range(1, len(parts)))
    root = ROOT.resolve()

    def known(rel_path: str) -> bool:
        rel_path = rel_path.strip("/")
        return rel_path in ("", ".") or rel_path in present or ignored(rel_path)

    missing: list[str] = []
    for rel in files:
        # the changelog records history, including files that were removed
        if not rel.endswith(".md") or rel == "CHANGELOG.md":
            continue
        md = ROOT / rel
        text = md.read_text(encoding="utf-8", errors="ignore")
        spans_checked = not planned_requirements(rel, text)
        in_fence = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK.findall(line):
                target = target.split("#", 1)[0]
                if not target or SKIP.search(target):
                    continue
                try:
                    to = (md.parent / target).resolve().relative_to(root).as_posix()
                except ValueError:
                    missing.append(f"{rel}:{n}: link to {target}, outside the repository")
                    continue
                if not known(to):
                    missing.append(f"{rel}:{n}: link to {target}")
            for span in (CODE.findall(line) if spans_checked else ()):
                # a test id (file::test) names its file here; check_sdd.py checks the test itself
                span = span.split("::", 1)[0].rstrip(".,;:")
                head = span.split("/", 1)[0]
                if "/" not in span and span not in tops:
                    continue
                if head not in tops or SKIP.search(span):
                    continue
                if not known(span):
                    missing.append(f"{rel}:{n}: names {span}")
    for m in missing:
        print(f"doc paths: {m}")
    if not missing:
        print("doc paths: OK, every named path exists")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
