"""Helpers of the adversarial tests: run a guard as a subprocess and plant one defect in a copy."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_REL = "frontend/node_modules/@fasl-work/caos-app-shell/src/content/executive.schema.json"


def add_schema(dest: Path) -> Path:
    """Copy the shell's executive schema, as ``npm ci`` installs it, into a copy: ``check_sdd.py`` validates the
    executive view against it and fails without it. A missing install fails the test with the reason."""
    src = ROOT / SCHEMA_REL
    assert src.is_file(), f"{SCHEMA_REL} is absent: run npm ci in frontend/ (the shell's schema is the contract under test)"
    (dest / SCHEMA_REL).parent.mkdir(parents=True, exist_ok=True)
    (dest / SCHEMA_REL).write_bytes(src.read_bytes())
    return dest


def guard(repo: Path, script: str, *args: str, ok_marker: str | None = None) -> subprocess.CompletedProcess:
    """Run ``repo/scripts/<script>`` as the CI does and prove that it ran: the script file exists, and the process
    returned an exit code and wrote to stdout. A guard that was never run cannot satisfy a caller's assertions."""
    path = repo / "scripts" / script
    assert path.is_file(), f"{script} is not in the copy"
    r = subprocess.run([sys.executable, str(path), *args], capture_output=True, encoding="utf-8", errors="replace", cwd=repo, timeout=120)
    assert isinstance(r.returncode, int) and r.stdout.strip(), f"{script} printed nothing (exit {r.returncode}): {r.stderr[:300]}"
    if ok_marker is not None and r.returncode == 0:
        assert ok_marker in r.stdout, r.stdout
    return r


def edit(repo: Path, rel: str, old: str, new: str, *, count: int = 1) -> None:
    """Replace ``old`` by ``new`` in a file of the copy; fails when ``old`` is absent (a plant that plants nothing)."""
    path = repo / rel
    text = path.read_bytes().decode("utf-8")
    assert old in text, f"{rel} does not contain {old!r}: the plant would change nothing"
    path.write_bytes(text.replace(old, new, count).encode("utf-8"))


def make_tree(dest: Path, *rels: str) -> Path:
    """Copy only the named files, directories or globs of the repository into ``dest`` (the inputs one guard reads), so
    a plant costs a few dozen files and not the whole repository. Generated and heavy trees are never copied."""
    skip = shutil.ignore_patterns("node_modules", "dist", "gate-output", "__pycache__", ".venv*", ".git", ".pytest_cache",
                                  ".ruff_cache", "*.pyc", "build")
    dest.mkdir(parents=True, exist_ok=True)
    for rel in rels:
        for src in sorted(ROOT.glob(rel)) if any(c in rel for c in "*?[") else [ROOT / rel]:
            target = dest / src.relative_to(ROOT)
            if src.is_dir():
                shutil.copytree(src, target, ignore=skip, dirs_exist_ok=True)
            elif src.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
    return dest


def set_cell(repo: Path, rel: str, rid: str, column: int, value: str) -> None:
    """Rewrite one cell of the table row whose first cell is ``rid`` (column 0 is the ID); fails when the row is absent."""
    path = repo / rel
    lines = path.read_bytes().decode("utf-8").split("\n")
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells and cells[0] == rid:
            parts = line.strip().strip("|").split("|")
            parts[column] = f" {value} "
            lines[i] = "|" + "|".join(parts) + "|"
            path.write_bytes("\n".join(lines).encode("utf-8"))
            return
    raise AssertionError(f"{rel} has no row {rid!r}: the plant would change nothing")


def drop_row(repo: Path, rel: str, rid: str) -> None:
    path = repo / rel
    lines = path.read_bytes().decode("utf-8").split("\n")
    kept = [ln for ln in lines if not ln.startswith(f"| {rid} ")]
    assert len(kept) == len(lines) - 1, f"{rel} has no row {rid!r}"
    path.write_bytes("\n".join(kept).encode("utf-8"))


def git_commit(repo: Path) -> str:
    """Make the copy a git repository with one commit (the base a ``--base`` check compares with); returns its SHA."""
    env = ["-c", "user.email=plant@example.invalid", "-c", "user.name=plant", "-c", "core.autocrlf=false"]
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", *env, "commit", "-q", "-m", "base"], cwd=repo, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


GATE_MODULE_REL = "frontend/node_modules/@fasl-work/caos-app-shell/gate/areas.mjs"


def add_gate_module(dest: Path) -> Path:
    """Copy the shell's gate analysis module (``gate/areas.mjs``, which holds ``analyseSvgAnimation`` and ``animationFailures``),
    as ``npm ci`` installs it, into a copy: ``check_svg_animation.py`` reuses it and fails without it."""
    src = ROOT / GATE_MODULE_REL
    assert src.is_file(), f"{GATE_MODULE_REL} is absent: run npm ci in frontend/ (the shell's animation analysis is what the guard reuses)"
    (dest / GATE_MODULE_REL).parent.mkdir(parents=True, exist_ok=True)
    (dest / GATE_MODULE_REL).write_bytes(src.read_bytes())
    return dest


# ---- the web plants: the copy's frontend/node_modules is the real one, linked (shared by the kept and the template's own plants)
NODE = shutil.which("node")
NODE_MODULES = ROOT / "frontend" / "node_modules"


def link_node_modules(frontend: Path) -> None:
    """Make the copy's frontend/node_modules the real one (a junction on Windows, a symlink elsewhere)."""
    target = frontend / "node_modules"
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)  # the copy holds only the executive schema the SDD guard reads (conftest add_schema)
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(NODE_MODULES)], check=True, capture_output=True)
    else:
        target.symlink_to(NODE_MODULES, target_is_directory=True)


def unlink_node_modules(frontend: Path) -> None:
    target = frontend / "node_modules"
    if os.name == "nt":
        os.rmdir(target)  # a junction: removes the link, never the real tree
    elif target.is_symlink():
        target.unlink()  # a symlink: os.rmdir raises NotADirectoryError on it (Linux CI)


def copy_node_modules(frontend: Path) -> None:
    """Give a generator plant disposable local dependency bytes, never a borrowed writable store."""
    frontend = frontend.resolve(strict=True)
    assert frontend != ROOT and ROOT not in frontend.parents, "dependency copies belong outside the real checkout"
    target = frontend / "node_modules"
    assert not target.is_symlink() and not target.is_junction(), "refuse a borrowed fixture dependency tree"
    assert target.resolve().is_relative_to(frontend), "fixture dependencies escape the fixture"
    assert NODE_MODULES.is_dir(), "installed frontend/node_modules is required; no install is performed by the test"
    install_is_the_locks(NODE_MODULES)
    # The budget is the product's own install (0.15.001, issue #102): the template's is about 156 MB, a product with
    # onnxruntime-web about 337 MB, and a fixed number refused the second. What bounds the copy is the drive it lands on.
    skipped = {".bin", "__tests__"}
    size = sum(p.stat().st_size for p in NODE_MODULES.rglob("*")
               if p.is_file() and not skipped.intersection(p.relative_to(NODE_MODULES).parts))
    free = shutil.disk_usage(frontend).free
    assert free - size >= COPY_FREE_FLOOR, (f"dependency fixture exceeded its copy budget: {size} bytes would leave "
                                           f"{max(free - size, 0)} free, under {COPY_FREE_FLOOR} on the plant's drive")
    # Vendor test fixtures are not runtime dependencies and can exceed Windows path limits in a nested copy.
    shutil.copytree(NODE_MODULES, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*skipped))


# a dependency copy never leaves its drive with less free space than this
COPY_FREE_FLOOR = 2 * 1024 ** 3


def install_is_the_locks(node_modules: Path) -> None:
    """The copied tree is what ``npm ci`` installed from the product's lock: every package npm recorded as installed
    (node_modules/.package-lock.json) is a package of package-lock.json at the same version."""
    hidden = node_modules / ".package-lock.json"
    lock = node_modules.parent / "package-lock.json"
    assert hidden.is_file() and lock.is_file(), "node_modules was not installed from a lock: run npm ci in frontend/"
    installed = json.loads(hidden.read_text(encoding="utf-8")).get("packages", {})
    locked = json.loads(lock.read_text(encoding="utf-8")).get("packages", {})
    stray = sorted(name for name, meta in installed.items()
                   if name and (name not in locked or locked[name].get("version") != meta.get("version")))
    assert not stray, f"node_modules holds packages its lock does not ({', '.join(stray[:5])}): run npm ci in frontend/"


SDD = "docs/design/SDD.md"


def sdd(repo: Path):
    """Run the spec guard (check_sdd.py) on a copy."""
    return guard(repo, "check_sdd.py")


def sdd_text(repo: Path) -> str:
    return (repo / SDD).read_bytes().decode("utf-8")


def section(text: str, name: str) -> tuple[int, int]:
    """A real level-2 section, retaining offsets for LF/CRLF text and optional numbered headings."""
    # Mask comments without changing positions; match the guard's same-character fence rules.
    visible = re.sub(r"<!--.*?(?:-->|\Z)", lambda m: re.sub(r"[^\r\n]", " ", m[0]), text, flags=re.S)
    headings = []
    fence = None
    offset = 0
    for line in visible.splitlines(keepends=True):
        marker = re.match(r"^\s*(```+|~~~+)", line)
        if fence is None:
            if marker:
                fence = marker[1]
            elif heading := re.match(r"^## (?:\d+[.)]?\s+)?(?P<title>.+?)\s*$", line):
                headings.append((offset, heading["title"].casefold()))
        elif marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not line.strip().lstrip(fence[0]).strip():
            fence = None
        offset += len(line)
    hits = [i for i, (_, title) in enumerate(headings) if title == name.casefold()]
    assert len(hits) == 1, f"SDD plant needs exactly one visible level-2 section {name!r}; found {len(hits)}"
    i = hits[0]
    return headings[i][0], (headings[i + 1][0] if i + 1 < len(headings) else len(text))
