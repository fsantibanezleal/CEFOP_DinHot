"""Plants of the fix round of template 0.09.000 (the Opus review, 2026-10-20): each defect the review found is planted in a copy and the
real guard or the real runner is run, so the fix is caught the day it regresses (requirements WB-014, WB-016, WB-017, CT-035)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from planting import ROOT, guard, make_tree, set_cell
from test_base_integrity_plants import declare, plant, track

NODE = shutil.which("node")
MB = 1024 * 1024
INTEGRITY = ("scripts/check_base_integrity.py", "scripts/check_contracts.py", "scripts/check_content_standards.py",
             "scripts/.content_standards_allow", "docs/contracts/catalog.md")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *INTEGRITY)


# ---------------------------------------------------------------- B1: the template passes its own content guard

@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="needs the git checkout the guard reads")
def test_the_template_itself_passes_the_content_standards_guard() -> None:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_content_standards.py")], capture_output=True, encoding="utf-8",
                       errors="replace", cwd=ROOT, timeout=120)
    assert r.returncode == 0 and "check_content_standards: OK" in r.stdout, r.stdout


# ---------------------------------------------------------------- B2: a declared file is exempt from the model rule only

def test_a_declared_heavy_parquet_is_refused(tree: Path) -> None:
    declare(tree, "data/raw/*.parquet")
    plant(tree, "data/raw/big.parquet", b"\0" * (12 * MB))
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "data/raw/big.parquet" in r.stdout and "raw or heavy data" in r.stdout, r.stdout


@pytest.mark.parametrize("name", ["native.dll", "libx.so", "libx.dylib"])
def test_a_declared_native_binary_is_refused(tree: Path, name: str) -> None:
    declare(tree, "models/bin/*")
    plant(tree, f"models/bin/{name}", b"\0" * 1024)
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and f"models/bin/{name}" in r.stdout and "native" in r.stdout, r.stdout


def test_a_declared_venv_file_is_refused(tree: Path) -> None:
    declare(tree, ".venv/**/*")
    plant(tree, ".venv/Lib/site-packages/x.py", "x = 1\n")
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and ".venv/Lib/site-packages/x.py" in r.stdout, r.stdout


def test_a_declared_small_pt_is_still_admitted(tree: Path) -> None:
    declare(tree, "data/models/*.pt")
    plant(tree, "data/models/a.pt", b"\0" * 1024)
    track(tree)
    r = guard(tree, "check_base_integrity.py", ok_marker="1 model file(s) admitted")
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- M1: a machine path inside a binary

def test_a_machine_path_inside_a_tracked_binary_fails(tree: Path) -> None:
    # built in two pieces: the guard reads this very file, and a machine path in a test source would fail it
    plant(tree, "assets/blob.bin", b"\x00\x01\x02 " + b"D:" + b"/_Repos/secret/thing \x00\xff")
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "machine path" in r.stdout and "blob.bin" in r.stdout, r.stdout


# ---------------------------------------------------------------- m1: .npy is not a model file

def test_a_declared_npy_array_is_not_admitted_as_a_model_file(tree: Path) -> None:
    declare(tree, "data/derived/*.npy")
    plant(tree, "data/derived/raw.npy", b"\0" * 1024)
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "data/derived/raw.npy" in r.stdout, r.stdout


# ---------------------------------------------------------------- m2: the documents guard alone refuses a glob outside the repository

DOC_INPUTS = ("scripts/check_documents.py", "scripts/check_contracts.py", "tests/contracts/contract_schemas.py", "docs/contracts", "data", "models")


@pytest.mark.parametrize("glob", ["../outside/*.json", "/etc/*.json", "C:/Windows/*.json", "data/../../x/*.json"])
def test_a_documents_glob_outside_the_repository_fails_the_guard_run_alone(tmp_path: Path, glob: str) -> None:
    repo = make_tree(tmp_path / "repo", *DOC_INPUTS)
    set_cell(repo, "docs/contracts/catalog.md", "params-record", 5, glob)
    r = guard(repo, "check_documents.py")
    assert r.returncode == 1 and glob in r.stdout and "outside the repository" in r.stdout, r.stdout


# ---------------------------------------------------------------- m6: a non-ASCII path is read

def test_an_em_dash_in_a_tracked_file_with_a_non_ascii_name_fails(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", "scripts/check_content_standards.py")
    plant(repo, "docs/caf\u00e9.md", "a line \u2014 with a dash\n")
    track(repo)
    r = guard(repo, "check_content_standards.py")
    assert r.returncode == 1 and "caf" in r.stdout and "em-dash" in r.stdout, r.stdout


# ---------------------------------------------------------------- M2: the runner refuses arguments that redirect what G18 measures

GATE_INPUTS = ("frontend/scripts", "product.json", "deploy/TARGET", "docs/design/SDD.md")


def run_gate(repo: Path, *extra: str) -> tuple[subprocess.CompletedProcess, list[str] | None]:
    frontend = repo / "frontend"
    shell = frontend / "node_modules" / "@fasl-work" / "caos-app-shell"
    (shell / "bin").mkdir(parents=True, exist_ok=True)
    (shell / "package.json").write_text('{"name":"@fasl-work/caos-app-shell","version":"0.0.0"}', encoding="utf-8")
    (shell / "bin" / "caos-shell-gate.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\nwriteFileSync(process.env.STUB_OUT, JSON.stringify(process.argv.slice(2)));\n", encoding="utf-8")
    out = repo / "stub-args.json"
    out.unlink(missing_ok=True)
    r = subprocess.run([NODE, str(frontend / "scripts" / "gate.mjs"), *extra], capture_output=True, encoding="utf-8", errors="replace",
                       cwd=frontend, env={**os.environ, "STUB_OUT": str(out)})
    return r, (json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None)


@pytest.mark.skipif(NODE is None, reason="needs node")
@pytest.mark.parametrize("extra", [["--workbench", "/app", "--routes", "/introduction"], ["--routes", "/introduction"], ["--app-route", "/x"]])
def test_the_runner_refuses_arguments_that_make_the_focus_check_measure_nothing(tmp_path: Path, extra: list[str]) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    r, args = run_gate(repo, *extra)
    assert r.returncode != 0 and args is None, (extra, r.stdout, r.stderr)
    assert "--require-focus" in r.stderr or "Focus" in r.stderr, r.stderr


@pytest.mark.skipif(NODE is None, reason="needs node")
def test_the_runner_still_accepts_a_route_list_that_keeps_the_app_route(tmp_path: Path) -> None:
    repo = make_tree(tmp_path / "repo", *GATE_INPUTS)
    r, args = run_gate(repo, "--routes", "/,/app", "--sizes", "1280x800")
    assert r.returncode == 0 and args and "--require-focus" in args, (r.stderr, args)
