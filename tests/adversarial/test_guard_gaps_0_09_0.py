"""Plants for four gaps of the verbatim guards found while releasing 0.09.000 (requirements WB-016 to WB-019):

- a tracked file with no suffix is scanned by the content-standards guard (an em-dash in `scripts/.template_residue_allow` passed);
- a committed document that is not JSON (a model file, a table) is left to its row's contract test, which the row must name;
- the technology-matrix guard reads an npm alias `npm:<package>@<version>`;
- no file a product takes verbatim names the owner. The personal name is refused; the GitHub handle `fsantibanezleal` is the
  repositories' owner identifier (it stands in source URLs, for example `scripts/check_contracts.py`) and stays allowed."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from planting import ROOT, edit, git_commit, guard, make_tree, set_cell

DASH = "\u2014"


@pytest.fixture
def standards(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", "scripts/check_content_standards.py", "scripts/.template_residue_allow", "VERSION")


def track(repo: Path) -> None:
    if not (repo / ".git").exists():
        git_commit(repo)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)


def test_the_real_suffixless_files_of_the_template_pass_the_guard(standards: Path) -> None:
    track(standards)
    r = guard(standards, "check_content_standards.py", ok_marker="check_content_standards: OK")
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("rel", ["NOTICE", "scripts/.hidden_allow", "deploy/TARGET"])
def test_an_em_dash_in_a_tracked_file_with_no_suffix_fails(standards: Path, rel: str) -> None:
    path = standards / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# justified {DASH} it exists for the rare collision\n", encoding="utf-8")
    track(standards)
    r = guard(standards, "check_content_standards.py")
    assert r.returncode == 1 and f"{rel}:1:" in r.stdout and "em-dash" in r.stdout, r.stdout


def test_a_suffixless_file_that_is_not_text_is_not_read(standards: Path) -> None:
    (standards / "blob").write_bytes(b"\xff\xfe\x00" + DASH.encode("utf-8") + b"\x80")
    track(standards)
    r = guard(standards, "check_content_standards.py", ok_marker="check_content_standards: OK")
    assert r.returncode == 0, r.stdout


def test_emoji_diagnostic_survives_a_windows_ansi_pipe(standards: Path) -> None:
    (standards / "README.md").write_text("emoji \U0001f600\n", encoding="utf-8")
    track(standards)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    script = standards / "scripts" / "check_content_standards.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=standards,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 1
    assert "README.md:1:7" in result.stdout
    assert "emoji (U+1F600" in result.stdout


def test_the_residue_allow_file_of_the_template_has_no_em_dash() -> None:
    assert DASH not in (ROOT / "scripts" / ".template_residue_allow").read_text(encoding="utf-8")


CATALOG = "docs/contracts/catalog.md"
DOCUMENTS, PRODUCER, CONSUMER = 5, 6, 7  # the columns of the params-record row, whose documents cell is "-"


def declare_binary(repo: Path, glob: str, rel: str, payload: bytes) -> None:
    set_cell(repo, CATALOG, "params-record", DOCUMENTS, glob)
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def test_a_declared_onnx_file_passes_when_its_row_names_a_test(docs: Path) -> None:
    declare_binary(docs, "models/*.onnx", "models/net.onnx", b"\x08\x07onnx\x00\xff\xfe")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 0 and "documents:" in r.stdout and "not JSON" in r.stdout and "models/net.onnx" in r.stdout, r.stdout


def test_a_declared_onnx_file_fails_when_its_row_names_no_test(docs: Path) -> None:
    declare_binary(docs, "models/*.onnx", "models/net.onnx", b"\x08\x07onnx\x00\xff\xfe")
    set_cell(docs, CATALOG, "params-record", PRODUCER, "-")
    set_cell(docs, CATALOG, "params-record", CONSUMER, "")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "models/net.onnx" in r.stdout and "params-record" in r.stdout and "producer test" in r.stdout, r.stdout


def test_a_declared_csv_table_passes_with_a_test_and_fails_without_one(docs: Path) -> None:
    declare_binary(docs, "data/tables/*.csv", "data/tables/rates.csv", b"a,b\n1,2\n")
    assert guard(docs, "check_documents.py").returncode == 0
    set_cell(docs, CATALOG, "params-record", PRODUCER, "-")
    set_cell(docs, CATALOG, "params-record", CONSUMER, "-")
    r = guard(docs, "check_documents.py")
    assert r.returncode == 1 and "data/tables/rates.csv" in r.stdout, r.stdout


TECH_INPUTS = ("scripts/check_tech_matrix.py", "docs/design/SDD.md", "requirements*.txt", "data-pipeline/requirements.txt", "notebooks/requirements.txt",
               "pyproject.toml", "frontend/package.json", "frontend/package-lock.json")
ALIAS = "zz-typescript5"
SPEC = "npm:typescript@5.9.3"


@pytest.fixture
def tech(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *TECH_INPUTS)


def add_alias(repo: Path, spec: str, locked: str = "5.9.3", in_table: bool = True) -> None:
    pkg = repo / "frontend/package.json"
    doc = json.loads(pkg.read_text(encoding="utf-8"))
    doc.setdefault("devDependencies", {})[ALIAS] = spec
    pkg.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    lock_path = repo / "frontend/package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"][""].setdefault("devDependencies", {})[ALIAS] = spec
    lock["packages"][f"node_modules/{ALIAS}"] = {"name": "typescript", "version": locked, "dev": True}
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    if in_table:
        sdd = repo / "docs/design/SDD.md"
        text = sdd.read_text(encoding="utf-8")
        row = next(ln for ln in text.splitlines() if ln.startswith("| shell |"))
        sdd.write_text(text.replace(row, f"{row}\n| compiler alias | {ALIAS} | {locked} | the TypeScript 5 compiler API the contract generator needs | none |"), encoding="utf-8")


def test_an_exact_alias_listed_in_the_table_passes(tech: Path) -> None:
    add_alias(tech, SPEC)
    r = guard(tech, "check_tech_matrix.py", ok_marker="check_tech_matrix: OK")
    assert r.returncode == 0, r.stdout


def test_an_alias_with_a_range_fails(tech: Path) -> None:
    add_alias(tech, "npm:typescript@^5.9.3")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "exact" in r.stdout, r.stdout


def test_an_alias_missing_from_the_table_fails(tech: Path) -> None:
    add_alias(tech, SPEC, in_table=False)
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "absent from the SDD technology table" in r.stdout, r.stdout


def test_an_alias_whose_lock_holds_another_version_fails(tech: Path) -> None:
    add_alias(tech, SPEC, locked="5.9.2")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "5.9.2" in r.stdout, r.stdout


def test_an_alias_whose_table_row_gives_another_version_fails(tech: Path) -> None:
    add_alias(tech, SPEC)
    edit(tech, "docs/design/SDD.md", f"| {ALIAS} | 5.9.3 |", f"| {ALIAS} | 5.9.2 |")
    r = guard(tech, "check_tech_matrix.py")
    assert r.returncode == 1 and ALIAS in r.stdout and "5.9.2" in r.stdout, r.stdout
