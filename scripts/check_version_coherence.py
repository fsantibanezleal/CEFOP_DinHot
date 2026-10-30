#!/usr/bin/env python3
"""T4: VERSION is the single source of the version, and everything that states a version agrees with it.

Fails when:
  - VERSION is not X.XX.XXX;
  - frontend/package.json's version is not the semver form of VERSION (0.02.000 -> 0.2.0);
  - the top entry of CHANGELOG.md is not VERSION;
  - a source file writes a version literal (X.XX.XXX) in CODE instead of reading VERSION (Python, TypeScript,
    TSX, JavaScript modules). Comments, docstrings and the prose of the documentation pages are history, not a
    source: "Until 0.05.000 the gate never read the benchmark" explains why a check exists and stays
    (CAOS_PRODUCT_TEMPLATE#19, found adopting the base on CAOS_Fragmenta: 23 of its 26 reports were history);
  - VERSION is behind the latest vX.XX.XXX tag.
Every manifest records the version it was baked with; that is a record, not a source, so data/ is not scanned.
Stdlib only. Usage: python scripts/check_version_coherence.py [repository root]
"""
from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path

DISPLAY = re.compile(r"^(\d+)\.(\d{2})\.(\d{3})$")
LITERAL = re.compile(r"(?<![\d.])\d+\.\d{2}\.\d{3}(?![\d.])")
SCANNED = ("data-pipeline", "app", "frontend/src", "frontend/scripts", "scripts", "tests")
# instantiate.py writes a new product's first version (0.01.000) by design, and the guards' test plants
# versions in throwaway trees; neither is a source of this version.
SKIP = {"scripts/check_version_coherence.py", "scripts/instantiate.py", "tests/test_guards.py"}
# The documentation routes and the content modules are prose: a release they cite ("measured at 0.06.000
# between Windows and Linux") is history, as in a comment (CAOS_Fragmenta's Implementation page, 2026-10-07).
PROSE = ("frontend/src/pages/", "frontend/src/content/")


def semver(display: str) -> str:
    major, minor, patch = DISPLAY.match(display).groups()
    return f"{int(major)}.{int(minor)}.{int(patch)}"


def key(display: str) -> tuple[int, int, int]:
    return tuple(int(x) for x in DISPLAY.match(display).groups())


def python_code(text: str) -> list[str]:
    """The lines of a Python file with comments blanked and docstrings removed; the text itself when it does
    not parse (a file that does not parse is scanned whole, never skipped)."""
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return lines
    out = list(lines)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            value = first.value if isinstance(first, ast.Expr) else None
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for n in range(first.lineno - 1, (first.end_lineno or first.lineno)):
                    out[n] = ""
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                out[row - 1] = out[row - 1][:col]
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def script_code(text: str) -> list[str]:
    """The lines of a TypeScript or JavaScript file with `//` and `/* */` comments blanked; strings and
    template literals are kept (a URL's `//` inside a string is not a comment)."""
    out: list[str] = []
    buf: list[str] = []
    i, n = 0, len(text)
    state = "code"
    quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block"
                i += 2
                continue
            if c in "'\"`":
                state, quote = "string", c
            buf.append(c)
        elif state == "string":
            buf.append(c)
            if c == "\\" and nxt:
                buf.append(nxt)
                i += 2
                continue
            if c == quote:
                state = "code"
        elif state == "line":
            if c == "\n":
                state = "code"
                buf.append(c)
        elif state == "block":
            if c == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            if c == "\n":
                buf.append(c)
        i += 1
    out = "".join(buf).split("\n")
    return out


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errs: list[str] = []
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not DISPLAY.match(version):
        print(f"VERSION {version!r} is not X.XX.XXX")
        return 1
    pkg = json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))
    if pkg.get("version") != semver(version):
        stated = pkg.get("version")
        errs.append(f"frontend/package.json version {stated} is not {semver(version)} (VERSION {version})")
    top = re.search(r"^## \[([^\]]+)\]", (root / "CHANGELOG.md").read_text(encoding="utf-8"), re.MULTILINE)
    if not top or top.group(1) != version:
        errs.append(f"the top CHANGELOG entry is {top.group(1) if top else 'missing'}, not {version}")
    for base in SCANNED:
        for f in sorted((root / base).rglob("*")):
            rel = f.relative_to(root).as_posix()
            if f.suffix not in {".py", ".ts", ".tsx", ".mjs", ".js"} or "node_modules" in f.parts:
                continue
            if rel in SKIP or rel.startswith(PROSE):
                continue
            text = f.read_text(encoding="utf-8")
            code = python_code(text) if f.suffix == ".py" else script_code(text)
            for n, line in enumerate(code, 1):
                if LITERAL.search(line):
                    errs.append(f"{rel}:{n}: a version literal in code; read VERSION instead")
    try:
        listed = subprocess.run(
            ["git", "tag", "--list", "v*"], cwd=root, capture_output=True, text=True, check=True
        )
        tags = listed.stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tags = []
    released = sorted((t[1:] for t in tags if DISPLAY.match(t[1:])), key=key)
    if released and key(version) < key(released[-1]):
        errs.append(f"VERSION {version} is behind the latest tag v{released[-1]}")
    for e in errs:
        print(f"version: {e}")
    if not errs:
        print(f"version: OK, {version} everywhere")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
