#!/usr/bin/env python3
"""Fail the build if tracked product content contains an EM-DASH or an EMOJI (ADR-0067).

The standing rule for every product (ADR-0067): no emojis and no em-dashes in repo content. Both read as
an AI tell and are banned from product content (code, docs, UI strings, commit-tracked files alike).
This guard enforces it structurally so no product, and the template itself, can drift.

What it flags (precise, to avoid punishing legitimate glyphs):
  - EM-DASH  U+2014  and HORIZONTAL BAR U+2015  (the banned dashes).
  - EMOJI: any codepoint in the Supplementary emoji/pictograph planes U+1F000..U+1FAFF, plus the
    emoji-presentation selector U+FE0F. This catches the pictographic emojis while intentionally
    NOT touching functional glyphs products do use: the info mark U+24D8 (the ADR-0058 modal button),
    the middot U+00B7 (the preferred separator), arrows like U+2197, check/cross marks, stars.

Not flagged: the ASCII double hyphen "--" (ubiquitous and legitimate in CLI flags and code) and the
en-dash U+2013. The rule as stated is em-dash + emoji; keep enforcement to exactly that.

Scanned set = git-tracked text files only: a file with a text suffix, and a file with no suffix (``LICENSE``, ``VERSION``,
``deploy/TARGET``, ``scripts/.template_residue_allow``) that decodes as UTF-8; a file that does not decode is binary and is not read.
Exit 1 on any hit, printing file:line:col.

Third-party text kept verbatim is not the product's content (an upstream licence notice has em-dashes). It is declared, never
masked, in ``scripts/.content_standards_allow``, one entry per line: ``<path> <sha256> <source URL>`` (``#`` starts a comment).
A listed file is skipped only while its SHA-256, over its content with line endings normalised to LF (so a Windows checkout and
Linux CI agree), equals the listed digest: a file edited after it was pinned fails, naming it, as does a listed path that does
not exist, a malformed entry, or a path outside the repository. An absent allow file means no exception; the template's has none.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "scripts/check_content_standards.py"
ALLOW_REL = "scripts/.content_standards_allow"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

BANNED_DASHES = {0x2014, 0x2015}  # em dash, horizontal bar
EMOJI_SELECTOR = 0xFE0F


def is_emoji(cp: int) -> bool:
    return 0x1F000 <= cp <= 0x1FAFF or cp == EMOJI_SELECTOR


TEXT_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".md", ".json",
    ".css", ".html", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".ini", ".svg", ".ipynb",
}


def tracked_files() -> list[str]:
    # -z: a path with a non-ASCII character is listed verbatim (without it git quotes the path and the file is never read)
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8", errors="replace").split("\0") if p]


def digest(path: Path) -> str:
    """SHA-256 of the file with CRLF read as LF, so the digest is the same on Windows and on Linux CI."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_allow() -> tuple[dict[str, str], list[str]]:
    """({path: digest} of the allow file, its problems). An absent file means no exception."""
    allowed: dict[str, str] = {}
    problems: list[str] = []
    path = ROOT / ALLOW_REL
    if not path.is_file():
        return allowed, problems
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        where = f"{ALLOW_REL}:{n}"
        if len(parts) != 3 or not _SHA256.match(parts[1].lower()) or not parts[2].startswith(("http://", "https://")):
            problems.append(f"  {where}  malformed allow file entry, expected '<path> <sha256> <source URL>': {line[:80]!r}")
            continue
        rel = parts[0].replace("\\", "/")
        if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or ".." in rel.split("/"):
            problems.append(f"  {where}  {rel} is outside the repository (a path relative to the root, no '..')")
        elif not (ROOT / rel).is_file():
            problems.append(f"  {where}  {rel} does not exist (the allow file lists a file that is gone: remove the entry)")
        else:
            allowed[rel] = parts[1].lower()
    return allowed, problems


def main() -> int:
    hits: list[str] = []
    allowed, allow_problems = read_allow()
    skipped = 0
    for rel in tracked_files():
        if rel in allowed:
            if digest(ROOT / rel) == allowed[rel]:
                skipped += 1
            else:
                allow_problems.append(f"  {rel}  changed since it was pinned in {ALLOW_REL} (its content no longer has the listed SHA-256: "
                                      "restore the upstream text, or pin the new text's digest from its source)")
            continue
        suffix = Path(rel).suffix.lower()
        if rel == SELF or (suffix != "" and suffix not in TEXT_SUFFIXES):
            continue  # a file with no suffix is read when it decodes as UTF-8 text (below); any other suffix is skipped
        try:
            lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(lines, 1):
            for col, ch in enumerate(line, 1):
                cp = ord(ch)
                if cp in BANNED_DASHES:
                    hits.append(f"  {rel}:{lineno}:{col}  em-dash (U+{cp:04X})")
                elif is_emoji(cp):
                    hits.append(f"  {rel}:{lineno}:{col}  emoji (U+{cp:04X} {ch!r})")

    if allow_problems:
        print(f"::error::the content-standards allow file ({ALLOW_REL}) is not sound:")
        for p in allow_problems:
            print(p)
    if not hits and not allow_problems:
        note = f" ({skipped} allow-listed file(s) skipped by digest)" if skipped else ""
        print(f"check_content_standards: OK, no em-dash or emoji in tracked content{note}.")
        return 0
    if not hits:
        return 1

    print("::error::banned characters found (no em-dash, no emoji in product content, ADR-0067):")
    for h in hits:
        print(h)
    print("\nReplace an em-dash with a comma, colon, semicolon, period, parentheses, or a middot "
          "as the sense requires. Remove emojis. This applies to code, docs, and UI strings alike.")
    return 1


if __name__ == "__main__":
    # A pipe uses the process's locale encoding on Windows (often cp1252). Findings contain the offending
    # character's repr, so force a UTF-8 diagnostic stream before emitting any content-standard message.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
