"""Plants for the base-integrity guard and the content-standards allow file (0.09.000, requirements CT-035 to CT-038): each
defect is planted in a copy of the repository's guard inputs and the real guard is run as CI runs it."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from planting import git_commit, guard, make_tree

INPUTS = ("scripts/check_base_integrity.py", "scripts/check_contracts.py", "scripts/check_content_standards.py",
          "scripts/.content_standards_allow", "docs/contracts/catalog.md")
CATALOG = "docs/contracts/catalog.md"
MB = 1024 * 1024
URL = "https://example.invalid/NOTICES"


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *INPUTS)


def plant(repo: Path, rel: str, data: bytes | str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


def track(repo: Path) -> None:
    """Make the copy a git repository once, then track what was planted."""
    if not (repo / ".git").exists():
        git_commit(repo)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)


def declare(repo: Path, documents: str) -> None:
    """Point the first catalog row's documents cell at ``documents`` (the template's row has one fixed path there)."""
    lines = (repo / CATALOG).read_bytes().decode("utf-8").split("\n")
    header = next(i for i, ln in enumerate(lines) if ln.startswith("|") and "| documents |" in ln)
    col = [c.strip() for c in lines[header].strip().strip("|").split("|")].index("documents")
    row = next(i for i in range(header + 2, len(lines)) if lines[i].startswith("|"))
    parts = lines[row].strip().strip("|").split("|")
    parts[col] = f" {documents}, {parts[col].strip()} " if parts[col].strip() not in ("", "-") else f" {documents} "
    lines[row] = "|" + "|".join(parts) + "|"
    (repo / CATALOG).write_bytes("\n".join(lines).encode("utf-8"))


def test_the_slim_tree_passes_both_guards(tree: Path) -> None:
    track(tree)
    assert guard(tree, "check_base_integrity.py", ok_marker="guards: OK").returncode == 0
    assert guard(tree, "check_content_standards.py", ok_marker="check_content_standards: OK").returncode == 0


def test_a_model_file_named_by_no_row_fails(tree: Path) -> None:
    plant(tree, "data/models/loose.pt", b"\0" * 10)
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "data/models/loose.pt" in r.stdout and "named by no catalog row" in r.stdout, r.stdout


def test_a_declared_model_file_over_five_mb_fails(tree: Path) -> None:
    declare(tree, "data/models/*.pt")
    plant(tree, "data/models/big.pt", b"\0" * (5 * MB + 1))
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "data/models/big.pt" in r.stdout and "5 MB" in r.stdout, r.stdout


def test_declared_model_files_over_fifty_mb_in_total_fail(tree: Path) -> None:
    declare(tree, "data/models/*.pt")
    for i in range(11):
        plant(tree, f"data/models/m{i}.pt", b"\0" * (5 * MB))
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "50 MB" in r.stdout, r.stdout


def test_a_declared_small_model_file_passes(tree: Path) -> None:
    declare(tree, "data/models/*.pt")
    plant(tree, "data/models/small.pt", b"\0" * 1000)
    track(tree)
    r = guard(tree, "check_base_integrity.py", ok_marker="1 model file(s) admitted")
    assert r.returncode == 0, r.stdout


def test_a_product_with_no_catalog_admits_no_model_file(tree: Path) -> None:
    (tree / CATALOG).unlink()
    plant(tree, "data/models/small.pt", b"\0" * 10)
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "no model file is admitted" in r.stdout, r.stdout


def test_a_real_env_file_tracked_fails(tree: Path) -> None:
    plant(tree, ".env", "SECRET=1\n")
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "a real .env is tracked" in r.stdout, r.stdout


def test_a_machine_path_in_a_source_fails(tree: Path) -> None:
    plant(tree, "src/a.py", "ROOT = '" + "D:" + "/_Repos/x'\n")
    track(tree)
    r = guard(tree, "check_base_integrity.py")
    assert r.returncode == 1 and "a local machine path in a tracked file" in r.stdout, r.stdout


def _allow(repo: Path, notice: str, *, listed: str = "vendor/NOTICES.txt") -> None:
    digest = hashlib.sha256(notice.encode("utf-8")).hexdigest()
    path = repo / "scripts/.content_standards_allow"
    path.write_bytes(path.read_bytes() + f"{listed} {digest} {URL}\n".encode("utf-8"))


def test_an_allow_listed_notice_passes_and_an_edited_one_fails(tree: Path) -> None:
    notice = "Third party \u2014 verbatim\n"
    plant(tree, "vendor/NOTICES.txt", notice)
    _allow(tree, notice)
    track(tree)
    assert guard(tree, "check_content_standards.py", ok_marker="1 allow-listed").returncode == 0
    plant(tree, "vendor/NOTICES.txt", notice + "an added line\n")
    r = guard(tree, "check_content_standards.py")
    assert r.returncode == 1 and "vendor/NOTICES.txt" in r.stdout and "changed" in r.stdout, r.stdout


def test_an_allow_listed_path_that_does_not_exist_fails(tree: Path) -> None:
    _allow(tree, "x\n", listed="vendor/GONE.txt")
    track(tree)
    r = guard(tree, "check_content_standards.py")
    assert r.returncode == 1 and "vendor/GONE.txt" in r.stdout and "does not exist" in r.stdout, r.stdout


def test_an_unlisted_notice_with_an_em_dash_fails(tree: Path) -> None:
    plant(tree, "vendor/NOTICES.txt", "Third party \u2014 verbatim\n")
    track(tree)
    r = guard(tree, "check_content_standards.py")
    assert r.returncode == 1 and "vendor/NOTICES.txt:1" in r.stdout, r.stdout

