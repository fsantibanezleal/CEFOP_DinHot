#!/usr/bin/env python3
"""The base-integrity guard: the regressions this archetype forbids (ADR-0074, ADR-0080). A product takes this file verbatim.

It judges the tracked paths (``git ls-files``) and fails on:

* a real ``.env`` (an ``.env.example`` may be tracked);
* a venv, or a native or heavy binary (``.dll``, ``.so``, ``.dylib``, ``.pt``, ``.pth``);
* raw or heavy data (``.parquet``, ``.h5``, ``.hdf5``, ``.nc``, ``.mat``, ``.npy``);
* a local machine path in a tracked source (the ``.github`` folder is exempt).

The base rule stands: data and models live in the device's data and models roots. What a product commits BY DESIGN, its compact
baked artifacts, is declared, never exempted: a tracked model file (``.pt``, ``.pth``, ``.onnx``) passes only when

1. a row of ``docs/contracts/catalog.md`` names it in its ``documents`` column (the globs of ``scripts/check_contracts.py``'s
   parser: relative to the root, ``!`` excludes, applied in the provider tree ``docs/contracts/fixtures/`` too under ``data/``
   and ``models/``), and
2. it is at most 5 MB on its own, and all the admitted model files together are at most 50 MB (MB is 1024 * 1024 bytes).

A product with no catalog, or a catalog without the ``documents`` column, admits no model file. Anything else still fails.

The tracked paths are read once, from ``git ls-files`` into a list: no pipe, no early-closing reader (``git ls-files | grep -q``
died of SIGPIPE under ``bash -o pipefail`` and flipped the result run to run).

Exit 0 and ``guards: OK``; exit 1 with an ``::error::`` line per finding. Usage: python scripts/check_base_integrity.py [repo_root]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from check_contracts import RELEASE_COLUMNS, parse_catalog, parse_document_glob, split_documents  # noqa: E402  (the one parser of the column)

CATALOG_REL = "docs/contracts/catalog.md"
FIXTURES_REL = "docs/contracts/fixtures"
ROOTED = ("data/", "models/")  # a glob under these also applies in the provider tree
MODEL_SUFFIXES = (".pt", ".pth", ".onnx")
MB = 1024 * 1024
MAX_FILE = 5 * MB
MAX_TOTAL = 50 * MB

ENV = re.compile(r"(^|/)\.env(\..+)?$", re.M)
ENV_EXAMPLE = re.compile(r"(^|/)\.env(\..+)?\.example$")
BINARY = re.compile(r"(^|/)\.?venv|\.(dll|so|dylib|pt|pth)$", re.I | re.M)
HEAVY_DATA = re.compile(r"\.(parquet|h5|hdf5|nc|mat|npy)$", re.I | re.M)
MACHINE_PATH = r"[A-Z]:\\_(Repos|worktrees|Temp)|[A-Z]:/_(Repos|worktrees|Temp)"


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8", errors="replace").split("\0") if p]


def declared(root: Path, files: set[str]) -> tuple[set[str], str | None]:
    """(the tracked files some catalog row's ``documents`` globs name, why none can be: None when the catalog is usable)."""
    catalog = root / CATALOG_REL
    if not catalog.is_file():
        return set(), f"{CATALOG_REL} is absent: no model file is admitted"
    parsed = parse_catalog(catalog.read_text(encoding="utf-8", errors="replace"))
    if parsed is None:
        return set(), f"{CATALOG_REL} has no contract table: no model file is admitted"
    header, rows = parsed
    if "documents" not in header:
        return set(), f"{CATALOG_REL} lacks the documents column (added in template {RELEASE_COLUMNS['documents']}): no model file is admitted"
    names: set[str] = set()
    for row in rows:
        include: list[str] = []
        exclude: list[str] = []
        for entry in split_documents(row.get("documents", "")):
            out, glob, _component = parse_document_glob(entry)
            for g in [glob] + ([f"{FIXTURES_REL}/{glob}"] if glob.startswith(ROOTED) else []):
                (exclude if out else include).append(g)
        drop = {p.relative_to(root).as_posix() for g in exclude for p in root.glob(g) if p.is_file()}
        names |= {p.relative_to(root).as_posix() for g in include for p in root.glob(g) if p.is_file()} - drop
    return names & files, None


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else HERE.parent
    files = tracked(root)
    fileset = set(files)
    fail = False

    def error(message: str, detail: list[str] | None = None) -> None:
        nonlocal fail
        fail = True
        print(f"::error::{message}")
        for line in detail or []:
            print(f"  {line}")

    # a real .env must never be tracked; an example file (.env.example, frontend/.env.example) may be
    envs = [f for f in files if ENV.search(f) and not ENV_EXAMPLE.search(f)]
    if envs:
        error(f"a real .env is tracked (only an .env.example may be): {' '.join(envs)} ", envs)

    # the model files a catalog row declares are judged on their own below; every other file is judged by suffix
    names, why = declared(root, fileset)
    models = [f for f in files if f.lower().endswith(MODEL_SUFFIXES)]
    admitted = [f for f in models if f in names]
    refused = [f for f in models if f not in names]

    # venvs, native binaries and heavy model blobs must never be tracked; only an admitted model file (declared, small) is exempt,
    # never a file a glob merely names (a declared .dll, .parquet or venv file is still refused)
    binaries = [f for f in files if BINARY.search(f) and f not in admitted]
    if binaries:
        error("a venv or native/heavy binary is tracked", binaries)
    # raw or heavy data must never be tracked; commit only compact derived artifacts under data/derived/
    heavy = [f for f in files if HEAVY_DATA.search(f) and f not in admitted]
    if heavy:
        error("raw or heavy data tracked; commit only compact derived artifacts (data/derived/)", heavy)

    # a model file a product commits by design is declared in the catalog and small; .onnx has no suffix rule of its own
    if refused:
        error("a tracked model file is not admitted: " + (why or f"named by no catalog row (add its path to a row's documents cell in {CATALOG_REL})"), refused)
    sizes = {f: (root / f).stat().st_size for f in admitted if (root / f).is_file()}
    over = [f"{f} ({sizes[f] / MB:.2f} MB)" for f in admitted if sizes.get(f, 0) > MAX_FILE]
    if over:
        error(f"a declared model file is over {MAX_FILE // MB} MB", over)
    total = sum(sizes.values())
    if total > MAX_TOTAL:
        error(f"the declared model files total {total / MB:.2f} MB in {len(admitted)} model file(s), over {MAX_TOTAL // MB} MB", sorted(admitted))

    # no leaked local machine paths in tracked sources; binary files are searched too (no -I), as the inline step did
    grep = subprocess.run(["git", "grep", "-nE", MACHINE_PATH, "--", ".", ":!.github"], cwd=root, capture_output=True)
    if grep.returncode == 0:
        hits = grep.stdout.decode("utf-8", errors="replace").splitlines()
        error("a local machine path in a tracked file", [h[:160] for h in hits[:20]])

    if fail:
        return 1
    print("guards: OK" + (f" ({len(admitted)} model file(s) admitted, {total / MB:.2f} MB)" if admitted else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
