"""Plant a defect in the web code and run the requirement's own vitest test on it (local-only: needs node and `npm ci` in frontend/).

``web_refute`` copies the files the web tests read into a throwaway tree, links the real ``node_modules``, runs the named test
untouched (the control, which must pass), edits the source (each edit must find its text, else the plant plants nothing), and runs
the test again, which must fail. The checks job installs neither node nor the frontend, so the callers skip there; the web job
runs the vitest suite itself."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from planting import NODE, NODE_MODULES, ROOT, link_node_modules, unlink_node_modules

COPIED = ("frontend", "data", "docs", "tests/fixtures", "content", "models", "VERSION", "product.json")
SKIP = shutil.ignore_patterns("node_modules", "dist", "gate-output", "__pycache__", ".git", "*.pyc")
LF, CRLF = "\n", "\r\n"


def _vitest(frontend: Path, test_file: str, title: str) -> subprocess.CompletedProcess:
    cmd = [NODE, str(frontend / "node_modules" / "vitest" / "vitest.mjs"), "run", test_file, "-t", re.escape(title)]
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", cwd=frontend, timeout=300)


def web_refute(tmp_path: Path, test_file: str, title: str, edits: list[tuple[str, str, str]]) -> str:
    """``edits``: ``(path relative to frontend/, old text, new text)``. Returns the planted run's output."""
    assert NODE and (NODE_MODULES / "@fasl-work").is_dir(), "needs node and `npm ci` in frontend/"
    test_file = test_file.removeprefix("frontend/")
    tree = tmp_path / "tree"
    for rel in COPIED:
        src = ROOT / rel
        if src.is_dir():
            shutil.copytree(src, tree / rel, ignore=SKIP if rel == "frontend" else shutil.ignore_patterns("__pycache__"))
        elif src.is_file():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tree / rel)
    frontend = tree / "frontend"
    link_node_modules(frontend)
    try:
        ok = _vitest(frontend, test_file, title)
        assert ok.returncode == 0 and "passed" in ok.stdout + ok.stderr, (
            f"the control run of {test_file} -t {title!r} must pass:\n{(ok.stdout + ok.stderr)[-1500:]}")
        for rel, old, new in edits:
            path = frontend / rel
            text = path.read_bytes().decode("utf-8")
            if CRLF in text:  # a checkout with CRLF line ends: the plant's own line breaks follow it
                old, new = old.replace(LF, CRLF), new.replace(LF, CRLF)
            assert old in text, f"{rel} does not contain {old!r}: the plant would change nothing"
            path.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        bad = _vitest(frontend, test_file, title)
        out = bad.stdout + bad.stderr
        assert bad.returncode != 0 and "failed" in out, (
            f"planting {[e[0] for e in edits]} did not make {test_file} -t {title!r} fail:\n{out[-1500:]}")
        return out
    finally:
        unlink_node_modules(frontend)
