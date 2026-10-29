#!/usr/bin/env python3
"""Run the product notebooks (CAOS_MANAGE ``conventions/product-notebooks.md`` section 7, template 0.10.000).

Executes each ``notebooks/<language>/<topic>/<notebook>.ipynb`` top to bottom in a fresh kernel (``nbclient``), with the
notebook's own folder as the working directory and a timeout per notebook, then strips the volatile metadata and writes the
notebook in place: the only writer of a notebook's outputs, so execution counts run 1, 2, 3 with no gap. Consecutive stream
outputs of one name are coalesced into one (as nbconvert does), so the committed bytes do not depend on kernel flush timing.

    python scripts/run_notebooks.py                 # every notebook, in place
    python scripts/run_notebooks.py --only notebooks/en/01-getting-started/01-first-run.ipynb
    python scripts/run_notebooks.py --check --tmp DIR   # executes copies under DIR, writes nothing in the repository, fails on any
                                                        # error and on committed bytes that differ from a fresh run (stale outputs)
    CAOS_TEMP_ROOT=DIR python scripts/run_notebooks.py --check      # the same, the temp root from the environment

``--check`` writes its copies to a fresh folder under the temp root the caller names (``--tmp DIR``, else ``CAOS_TEMP_ROOT``;
the device's temp root, never a path written in the repository) and removes it after the run; without a temp root it stops
with exit 2, and the system temp folder is never used. A product that declares method packages (``product.json``
``method_packages``, PyPI distributions) must have them installed here, each with an exact pin in ``notebooks/requirements.txt``,
and no notebook may define a name they define: the run stops before any notebook executes (``scripts/check_notebooks.py`` holds
the same names statically when the packages are installed).

It runs in ``.venv-notebooks`` (``scripts/setup.sh --notebooks`` or ``scripts/setup.ps1 -Notebooks``, built from
``notebooks/requirements.txt``): started with another interpreter, it re-runs itself in that venv. A local release gate, never CI
(ADR-0074). A missing artifact fails the notebook with its path in the error; nothing stands in for it.
A notebook outside ``notebooks/<language>/<topic>/<notebook>.ipynb`` fails the run before any notebook executes.
Exit 0 every notebook ran, 1 on any failure, 2 on a usage or environment problem.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
VENV = ROOT / ".venv-notebooks"
# the time one notebook may take, seconds (the example's longest runs in well under a minute)
TIMEOUT_SECONDS = 600
KERNEL = "python3"
KERNELSPEC = {"display_name": "Python 3", "language": "python", "name": "python3"}
KEEP_NOTEBOOK_METADATA = ("kernelspec", "language_info", "caos")
LANGS = ("en", "es")
LAYOUT = "notebooks/<language>/<topic>/<notebook>.ipynb"


def venv_python() -> Path | None:
    for rel in ("Scripts/python.exe", "bin/python"):
        if (VENV / rel).is_file():
            return VENV / rel
    return None


def coalesce_streams(outputs: list[dict]) -> list[dict]:
    """Consecutive ``stream`` outputs of one name joined into one: nbclient keeps each iopub message as its own output, so
    the split would follow the kernel's flush timing and rewrite a committed notebook from run to run."""
    merged: list[dict] = []
    for out in outputs:
        last = merged[-1] if merged else {}
        if out.get("output_type") == "stream" and last.get("output_type") == "stream" and last.get("name") == out.get("name"):
            merged[-1]["text"] = "".join(merged[-1]["text"]) + "".join(out["text"])
        else:
            merged.append(dict(out))
    for out in merged:
        if out.get("output_type") == "stream":
            out["text"] = "".join(out["text"]).splitlines(keepends=True)  # nbformat's own shape: a list of lines
    return merged


def strip_volatile(nb: dict) -> dict:
    """The notebook without what changes from run to run or machine to machine: timings, widget state, the kernel's Python
    version and every cell metadata key but ``tags``, with consecutive streams coalesced. Cell ids stay (nbformat 4.5)."""
    nb = copy.deepcopy(nb)
    meta = nb.get("metadata", {})
    nb["metadata"] = {k: meta[k] for k in KEEP_NOTEBOOK_METADATA if k in meta}
    nb["metadata"]["kernelspec"] = dict(KERNELSPEC)
    nb["metadata"]["language_info"] = {"name": "python"}
    for cell in nb.get("cells", []):
        tags = cell.get("metadata", {}).get("tags")
        cell["metadata"] = {"tags": tags} if tags else {}
        if cell.get("cell_type") == "code":
            cell["outputs"] = coalesce_streams(cell.get("outputs", []))
    return nb


def dump(nb: dict, path: Path) -> None:
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def misplaced() -> list[str]:
    """Notebooks anywhere but ``notebooks/<language>/<topic>/<notebook>.ipynb``: the layout the static check holds, and the
    only one the runner executes."""
    out: list[str] = []
    for p in sorted(NOTEBOOKS.rglob("*.ipynb")) if NOTEBOOKS.is_dir() else []:
        parts = p.relative_to(NOTEBOOKS).parts
        if not (len(parts) == 3 and parts[0] in LANGS):
            out.append(p.relative_to(ROOT).as_posix())
    return out


def discover(only: str | None) -> list[Path]:
    if only:
        p = (ROOT / only).resolve() if not Path(only).is_absolute() else Path(only).resolve()
        return [p] if p.is_file() else []
    return sorted(p for lang in LANGS for p in NOTEBOOKS.glob(f"{lang}/*/*.ipynb"))


def warm_matplotlib() -> None:
    """Build matplotlib's font cache before the kernels start, so its one-off message never lands in a notebook's stderr."""
    try:
        import matplotlib
        matplotlib.use("agg")
        import matplotlib.pyplot as plt
        plt.figure().text(0, 0, "warm")
        plt.close("all")
    except ImportError:
        pass


def execute(src: Path, dest: Path) -> str | None:
    """Execute ``src`` in a fresh kernel in its own folder and write the clean result to ``dest``; None when it ran, else why not."""
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    nb = nbformat.read(src, as_version=4)
    for cell in nb.cells:  # a fresh run: no stale output or count survives
        if cell.cell_type == "code":
            cell.outputs, cell.execution_count = [], None
    client = NotebookClient(nb, timeout=TIMEOUT_SECONDS, kernel_name=KERNEL, resources={"metadata": {"path": str(src.parent)}},
                            allow_errors=False)
    try:
        client.execute()
    except CellExecutionError as e:
        return f"{type(e).__name__}: {str(e).strip().splitlines()[-1] if str(e).strip() else e}"
    except Exception as e:  # a dead kernel, a timeout: the run fails and says why
        return f"{type(e).__name__}: {e}"
    dump(strip_volatile(json.loads(nbformat.writes(nb))), dest)
    return None


def same_bytes(a: Path, b: Path) -> bool:
    """The two files hold the same bytes, line endings aside (a checkout may convert them)."""
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def method_problems() -> list[str]:
    """What stops the run before any notebook executes: a method package of ``product.json`` that is not installed here or has no
    exact pin, and a notebook cell that defines a name a method package defines. The rules are the static check's, which this
    runner loads from the folder it lives in."""
    checker = Path(__file__).resolve().parent / "check_notebooks.py"
    if not checker.is_file():
        product = ROOT / "product.json"
        return ["scripts/check_notebooks.py is missing next to the runner, so the method packages cannot be checked"] if (
            product.is_file() and "method_packages" in product.read_text(encoding="utf-8")) else []
    spec = importlib.util.spec_from_file_location("check_notebooks_for_runner", checker)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True  # --check writes nothing in the repository, not even a bytecode cache of the checker
    spec.loader.exec_module(module)
    methods, problems = module.method_state(ROOT, strict=True)
    for path in sorted(NOTEBOOKS.glob("*/*/*.ipynb")) if methods else []:
        try:
            cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
        except (OSError, ValueError):
            continue
        problems.extend(module.method_copy_findings(path.relative_to(ROOT).as_posix(), cells, methods))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(prog="run_notebooks", description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="execute copies under the temp root; write nothing, fail on any error")
    ap.add_argument("--tmp", metavar="DIR", help="the temp root of --check (default: the environment variable CAOS_TEMP_ROOT)")
    ap.add_argument("--only", metavar="PATH", help="run one notebook (a path from the repository root)")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()

    temp_root: Path | None = None
    if a.check:
        named = a.tmp or os.environ.get("CAOS_TEMP_ROOT") or ""
        if not named.strip():
            print("run_notebooks: --check needs a temp root: pass --tmp DIR or set CAOS_TEMP_ROOT (the device's temp root)")
            return 2
        temp_root = Path(named).expanduser().resolve()
        if temp_root.exists() and not temp_root.is_dir():
            print(f"run_notebooks: the temp root {temp_root} is not a folder")
            return 2

    py = venv_python()
    if not a.inner and py is not None and Path(sys.prefix).resolve() != VENV.resolve():
        return subprocess.run([str(py), __file__, "--inner", *sys.argv[1:]], cwd=ROOT).returncode
    try:
        import nbclient  # noqa: F401
        import nbformat  # noqa: F401
    except ImportError:
        print("run_notebooks: nbclient and nbformat are not installed; build the notebook environment with "
              "scripts/setup.sh --notebooks (scripts/setup.ps1 -Notebooks on Windows)")
        return 2
    stray = misplaced()
    if stray:
        print(f"run_notebooks: no notebook ran; a notebook lives at {LAYOUT}: {', '.join(stray)}")
        return 1
    problems = method_problems()
    if problems:
        print("run_notebooks: no notebook ran; the method packages of the product do not hold:")
        for line in problems:
            print(f"  - {line}")
        return 1
    books = discover(a.only)
    if not books:
        print(f"run_notebooks: no notebook to run ({a.only or 'notebooks/*/*/*.ipynb'})")
        return 2
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")  # the kernels import data-pipeline/ by path: leave no cache behind
    warm_matplotlib()
    tmp_root = None
    if temp_root is not None:
        temp_root.mkdir(parents=True, exist_ok=True)
        tmp_root = Path(tempfile.mkdtemp(prefix="run-notebooks-", dir=temp_root))
    failures: list[str] = []
    try:
        for book in books:
            rel = book.relative_to(ROOT).as_posix()
            if tmp_root is not None:
                # a copy of the repository's inputs at the same relative depth: the notebook reads `../../../data/...`
                work = tmp_root / "repo"
                for item in ("data", "data-pipeline", "docs", "content", "models", "notebooks"):
                    if (ROOT / item).exists() and not (work / item).exists():
                        shutil.copytree(ROOT / item, work / item, ignore=shutil.ignore_patterns("__pycache__", ".ipynb_checkpoints"))
                work.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / "VERSION", work / "VERSION")  # the pipeline package reads it at import
                src = work / rel
            else:
                src = book
            fresh = (tmp_root / "out.ipynb") if tmp_root else src
            why = execute(src, fresh)
            if why is None and tmp_root is not None and not same_bytes(fresh, book):
                why = ("stale: the committed outputs differ from a fresh run; run scripts/run_notebooks.py and commit the result "
                       "(a notebook edited by hand keeps outputs it no longer produces)")
            if why is None:
                print(f"  ran   {rel}")
            else:
                failures.append(rel)
                print(f"  FAIL  {rel}: {why}")
    finally:
        if tmp_root is not None:
            shutil.rmtree(tmp_root, ignore_errors=True)
    if failures:
        print(f"run_notebooks: {len(failures)} of {len(books)} notebooks failed: {', '.join(failures)}")
        return 1
    print(f"run_notebooks: OK, {len(books)} notebooks executed top to bottom in fresh kernels" + (" (check, nothing written)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
