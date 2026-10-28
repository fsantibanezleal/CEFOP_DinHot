"""ADR-0074 gate: CI and CD are cheap checks, run only for develop and main.

Fails when a workflow:
  - triggers on pull_request, on a schedule, or on a push to a branch other than
    develop/main/master;
  - has no top-level concurrency group;
  - has a job without timeout-minutes;
  - installs the training stack (precompute lane, pipeline requirements, torch & co.);
  - runs a training, pipeline, bake or benchmark entry point;
  - runs a test suite in a product repo (data-pipeline/ or requirements-precompute.txt):
    tests run locally; the only exception is one command, matched whole (`re.fullmatch`) after the backslash
    line continuations of a `run:` block are joined: `[pip install pytest==X.Y.Z && ]python -m pytest tests/adversarial[ -q]`
    (the guards' planted-defect suite). A second command, another path, `..`, a config or plugin option
    (`-c`, `--rootdir`, `-o`, `--override-ini`, `-p`, `--pyargs`) or a trailing comment is a test run and a finding.
    `pip install pytest==X.Y.Z` on a line of its own installs, it does not run a suite.
    A `run:` value is read the way YAML reads it, not line by line: a plain or quoted scalar continued on deeper lines
    is folded into one command, a `>` block is judged folded and line by line, a `|` block line by line after its
    backslash continuations, and a block is every line deeper than the `run:` key, however deep. Any pytest
    environment variable (`PYTEST_ADDOPTS`, `PYTEST_PLUGINS`, `PYTEST_CONFIG` ...) in a product's workflow, in `env:` at
    any level or in a command, is a finding: it changes what the allowed command collects (measured: `tests` in
    `PYTEST_ADDOPTS` makes `python -m pytest tests/adversarial` collect all 493 tests instead of 111).
Stdlib only, so it runs before any install.
Usage: python scripts/check_ci_budget.py [repo_dir]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
TRUNKS = {"develop", "main", "master"}
STACK_INSTALL = re.compile(
    r"download\.pytorch\.org|(pip|uv)\s+(pip\s+)?install\b[^\n#]*("
    r"requirements-precompute|requirements-gpu|data-pipeline/requirements|"
    r"\b(torch|torchvision|tensorflow|jax|jaxlib|transformers|lightning)\b)"
)
PIPELINE_RUN = re.compile(
    r"data-pipeline/\S+\.py|\brun_all\b|\bprecompute\b|\bbenchmark\b|stages\.train|--epochs\b|"
    r"\bcompare_bakes\b|\bbake\b|lab\.pipeline\b|-m\s+\S+\.pipeline\b"
)
PYTEST_ENV = re.compile(r"(?<![A-Za-z0-9_])PYTEST_[A-Z0-9_]+")
RUN_KEY = re.compile(r"^(?P<indent>\s*)(?P<dash>-\s+)?run\s*:(?:\s+(?P<value>.*?))?\s*$")
BLOCK_HEADER = re.compile(r"^[|>][+-]?\d*$")
PYTEST = re.compile(r"(^|[\s;&|(])(python3?\s+-m\s+)?pytest\b")
PIP_INSTALL = re.compile(r"\bpip3?\s+install\b[^;&|\n]*")
# the one suite CI may run: the adversarial plants of the guards (copies of the guards' inputs, standard library and
# pytest only); the product's own tests stay local. The whole command must be this, nothing before, after or between.
# In the template the base guards' plants that need the example run too (tests/template/adversarial, BD-3); instantiate.py
# drops that path from the product's workflow together with the folder.
ADVERSARIAL = re.compile(r"(?:pip install pytest==\d+\.\d+\.\d+ && )?python -m pytest tests/adversarial(?: tests/template/adversarial)?(?: -q)?")


def runs_a_suite(cmd: str) -> bool:
    """True when the command starts pytest (a ``pip install pytest==X`` only installs it)."""
    return PYTEST.search(PIP_INSTALL.sub(" ", cmd)) is not None


def logical_lines(text: str) -> list[tuple[int, str]]:
    """The file's lines as (first line number, text), a line ending in a backslash joined with the next one."""
    out: list[tuple[int, str]] = []
    pending: tuple[int, str] | None = None
    for i, raw in enumerate(text.splitlines(), 1):
        first, line = (pending[0], pending[1] + " " + raw.strip()) if pending is not None else (i, raw)
        if line.rstrip().endswith("\\"):
            pending = (first, line.rstrip()[:-1].rstrip())
            continue
        pending = None
        out.append((first, line))
    if pending is not None:
        out.append(pending)
    return out


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def run_commands(text: str) -> list[tuple[int, str]]:
    """Every command a ``run:`` key hands to the shell, as (line number, command), each value read as YAML reads it."""
    lines = text.splitlines()
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        m = RUN_KEY.match(lines[i])
        if m is None or lines[i].lstrip().startswith("#"):
            i += 1
            continue
        key_col = len(m["indent"]) + len(m["dash"] or "")
        value = (m["value"] or "").strip()
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or indent_of(lines[j]) > key_col):
            j += 1
        body = [ln.strip() for ln in lines[i + 1:j]]
        while body and not body[-1]:
            body.pop()
        start = i + 2  # the number of the first body line
        if BLOCK_HEADER.match(value):
            if value[0] == "|":
                out += [(start + n - 1, cmd.strip()) for n, cmd in logical_lines(chr(10).join(body)) if cmd.strip()]
            else:  # folded: lines join with a space, a blank line separates; judge the folded text and each line
                group: list[tuple[int, str]] = []
                for n, ln in enumerate(body + [""]):
                    if ln:
                        group.append((start + n, ln))
                    elif group:
                        out.append((group[0][0], " ".join(t.rstrip("\\").strip() for _, t in group)))
                        out += group
                        group = []
        else:
            parts = [p for p in [value, *body] if p]
            if parts:
                out.append((i + 1, " ".join(p.rstrip("\\").strip() for p in parts)))
        i = j
    return out


def check_workflow(path: Path, product: bool) -> list[str]:
    errs: list[str] = []
    text = path.read_text(encoding="utf-8")
    name = path.relative_to(ROOT).as_posix()
    if re.search(r"^\s{2}pull_request(_target)?\s*:", text, re.MULTILINE):
        errs.append(f"{name}: pull_request trigger (ADR-0074 rule 4)")
    if re.search(r"^\s{2}schedule\s*:", text, re.MULTILINE):
        errs.append(f"{name}: schedule trigger (ADR-0074 rule 4)")
    for m in re.finditer(r"^\s{4}branches\s*:\s*\[([^\]]*)\]", text, re.MULTILINE):
        bad = {b.strip().strip("'\"") for b in m.group(1).split(",")} - TRUNKS - {""}
        if bad:
            errs.append(f"{name}: triggers on branches {sorted(bad)} (ADR-0074 rule 4)")
    if not re.search(r"^concurrency\s*:", text, re.MULTILINE):
        errs.append(f"{name}: no top-level concurrency group (ADR-0074 rule 5)")

    in_jobs, job, has_timeout, reusable = False, None, False, False
    jobs: list[tuple[str, bool, bool]] = []
    for line in text.splitlines():
        if re.match(r"^jobs\s*:", line):
            in_jobs = True
            continue
        if in_jobs and re.match(r"^\S", line):
            in_jobs = False
        if not in_jobs:
            continue
        m = re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*$", line)
        if m:
            if job:
                jobs.append((job, has_timeout, reusable))
            job, has_timeout, reusable = m.group(1), False, False
        elif re.match(r"^    timeout-minutes\s*:", line):
            has_timeout = True
        elif re.match(r"^    uses\s*:", line):
            reusable = True
    if job:
        jobs.append((job, has_timeout, reusable))
    for j, t, r in jobs:
        if not t and not r:
            errs.append(f"{name}: job '{j}' has no timeout-minutes (ADR-0074 rule 5)")

    def add(msg: str) -> None:
        if msg not in errs:
            errs.append(msg)

    for i, line in logical_lines(text):
        if not line.strip().startswith("#") and STACK_INSTALL.search(line):
            add(f"{name}:{i}: installs the training stack (ADR-0074 rule 2)")
    if product:
        for i, line in enumerate(text.splitlines(), 1):
            hit = None if line.strip().startswith("#") else PYTEST_ENV.search(line)
            if hit:
                add(f"{name}:{i}: sets {hit.group(0)}, which changes what the allowed command collects; "
                    "tests run locally (ADR-0074 rule 3)")
    for i, cmd in run_commands(text):
        if STACK_INSTALL.search(cmd):
            add(f"{name}:{i}: installs the training stack (ADR-0074 rule 2)")
        elif PIPELINE_RUN.search(cmd):
            add(f"{name}:{i}: trains, bakes or runs the pipeline (ADR-0074 rule 1)")
        elif product and runs_a_suite(cmd) and not ADVERSARIAL.fullmatch(cmd):
            add(f"{name}:{i}: runs the test suite in CI; tests run locally (ADR-0074 rule 3)")
    return errs


def main() -> int:
    # A product has an offline lane: data-pipeline/ or a precompute requirements file.
    product = (ROOT / "data-pipeline").is_dir() or (ROOT / "requirements-precompute.txt").is_file()
    errs: list[str] = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        errs += check_workflow(wf, product)
    for e in errs:
        print(f"::error::{e}")
    if not errs:
        print("ci budget: OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
