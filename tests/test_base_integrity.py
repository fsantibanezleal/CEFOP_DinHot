"""The base-integrity guard (scripts/check_base_integrity.py) and the content-standards allow file
(scripts/.content_standards_allow), each run as CI runs it on a throwaway git tree with one case planted (0.09.000)."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MB = 1024 * 1024
HEAD = ("| id | version | owner | schema file | example | documents | producer test | consumer test | missing-data behavior | provider | swap test |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|\n")


def catalog(documents: str) -> str:
    return HEAD + f"| m1 | 1.0.0 | o | s | e | {documents} | p | c | m | baseline:x | t |\n"


def tree(tmp: Path, files: dict, *, with_scripts: tuple[str, ...] = ("check_base_integrity.py", "check_contracts.py")) -> Path:
    """A git repository holding the named files and a copy of the named guard scripts (the guards locate the repository
    from their own path)."""
    root = tmp / "tree"
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    (root / "scripts").mkdir(exist_ok=True)
    for name in with_scripts:
        shutil.copy2(SCRIPTS / name, root / "scripts" / name)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    return root


def run(root: Path, script: str = "check_base_integrity.py") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(root / "scripts" / script)], cwd=root, capture_output=True, encoding="utf-8", errors="replace")


# ---- the rules of the former inline step, with the same messages

@pytest.mark.parametrize(
    ("files", "error"),
    [
        ([".env.example", "README.md"], None),
        (["frontend/.env.example", "README.md"], None),
        ([".env", ".env.example", "README.md"], "a real .env is tracked"),
        (["frontend/.env.local", ".env.example"], "a real .env is tracked"),
        ([".env.example", "models/weights.pt"], "a venv or native/heavy binary is tracked"),
        ([".venv/pyvenv.cfg"], "a venv or native/heavy binary is tracked"),
        (["lib/native.dll"], "a venv or native/heavy binary is tracked"),
        ([".env.example", "data/raw/table.parquet"], "raw or heavy data tracked"),
        (["data/raw/table.npy"], "raw or heavy data tracked"),
    ],
)
def test_the_inline_rules_and_messages_are_kept(tmp_path, files, error):
    res = run(tree(tmp_path, {f: "x\n" for f in files}))
    if error is None:
        assert res.returncode == 0 and "guards: OK" in res.stdout, res.stdout + res.stderr
    else:
        assert res.returncode == 1 and error in res.stdout and "guards: OK" not in res.stdout, res.stdout + res.stderr


def test_a_local_machine_path_in_a_source_fails_and_the_workflow_folder_is_exempt(tmp_path):
    path = "D:" + "/_Repos/x"
    bad = run(tree(tmp_path / "a", {"src/a.py": f"P = '{path}'\n"}))
    assert bad.returncode == 1 and "a local machine path in a tracked file" in bad.stdout, bad.stdout
    ok = run(tree(tmp_path / "b", {".github/workflows/ci.yml": f"# {path}\n", "README.md": "x\n"}))
    assert ok.returncode == 0, ok.stdout


def test_the_guard_is_stable_on_a_large_clean_tree(tmp_path):
    # the inline step's `git ls-files | grep -q` died of SIGPIPE under pipefail and flipped run to run; the script reads the list once
    files = {".env.example": "x\n"} | {f"src/part{i // 500}/file{i}.txt": "x\n" for i in range(6000)}
    root = tree(tmp_path, files)
    for _ in range(5):
        res = run(root)
        assert res.returncode == 0, res.stdout + res.stderr


# ---- the model admission

def model_tree(tmp: Path, documents: str, sizes: dict[str, int], *, cat: bool = True) -> Path:
    files: dict = {rel: b"\0" * n for rel, n in sizes.items()}
    if cat:
        files["docs/contracts/catalog.md"] = catalog(documents)
    return tree(tmp, files)


def test_a_declared_small_model_file_is_admitted(tmp_path):
    res = run(model_tree(tmp_path, "data/models/*.pt, data/models/a.onnx", {"data/models/a.pt": 100, "data/models/b.pt": 100, "data/models/a.onnx": 10}))
    assert res.returncode == 0 and "guards: OK" in res.stdout and "3 model file(s) admitted" in res.stdout, res.stdout + res.stderr


def test_a_model_file_no_row_names_fails_and_the_message_names_it(tmp_path):
    res = run(model_tree(tmp_path, "data/models/a.pt", {"data/models/a.pt": 10, "data/models/other.pt": 10}))
    assert res.returncode == 1 and "data/models/other.pt" in res.stdout and "named by no catalog row" in res.stdout, res.stdout
    assert "data/models/a.pt" not in res.stdout


def test_an_undeclared_onnx_file_fails(tmp_path):
    res = run(model_tree(tmp_path, "-", {"web/m.onnx": 10}))
    assert res.returncode == 1 and "web/m.onnx" in res.stdout, res.stdout


def test_a_declared_model_file_over_five_mb_fails(tmp_path):
    res = run(model_tree(tmp_path, "data/models/*.pt", {"data/models/big.pt": 5 * MB + 1, "data/models/ok.pt": 5 * MB}))
    assert res.returncode == 1 and "data/models/big.pt" in res.stdout and "5 MB" in res.stdout, res.stdout
    assert "ok.pt" not in res.stdout


def test_declared_model_files_over_fifty_mb_in_total_fail(tmp_path):
    res = run(model_tree(tmp_path, "data/models/*.pt", {f"data/models/m{i}.pt": 5 * MB for i in range(11)}))
    assert res.returncode == 1 and "50 MB" in res.stdout and "11 model file(s)" in res.stdout, res.stdout


def test_exactly_fifty_mb_in_total_passes(tmp_path):
    res = run(model_tree(tmp_path, "data/models/*.pt", {f"data/models/m{i}.pt": 5 * MB for i in range(10)}))
    assert res.returncode == 0, res.stdout


def test_an_excluded_file_is_not_declared(tmp_path):
    res = run(model_tree(tmp_path, "data/models/*.pt, !data/models/x.pt", {"data/models/a.pt": 1, "data/models/x.pt": 1}))
    assert res.returncode == 1 and "data/models/x.pt" in res.stdout, res.stdout


def test_a_product_without_a_catalog_admits_no_model_file_and_says_so(tmp_path):
    res = run(model_tree(tmp_path, "", {"data/models/a.pt": 10}, cat=False))
    assert res.returncode == 1 and "docs/contracts/catalog.md is absent" in res.stdout and "no model file is admitted" in res.stdout, res.stdout


def test_a_catalog_without_the_documents_column_admits_nothing(tmp_path):
    old = "| id | provider |\n|---|---|\n| m1 | baseline:x |\n"
    root = tree(tmp_path, {"docs/contracts/catalog.md": old, "data/models/a.pt": b"\0"})
    res = run(root)
    assert res.returncode == 1 and "documents" in res.stdout and "data/models/a.pt" in res.stdout, res.stdout


def test_a_model_file_that_is_not_tracked_is_not_judged(tmp_path):
    root = model_tree(tmp_path, "-", {})
    (root / "data").mkdir()
    (root / "data/untracked.pt").write_bytes(b"\0")
    assert run(root).returncode == 0


def test_a_tree_with_no_catalog_and_no_model_file_passes(tmp_path):
    assert run(tree(tmp_path, {"README.md": "x\n"})).returncode == 0


# ---- the content-standards allow file

NOTICE = "Third party notice \u2014 verbatim\n"
URL = "https://example.invalid/NOTICES"


def sha(text) -> str:
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def notice_tree(tmp: Path, allow: str, notice=NOTICE) -> Path:
    files: dict = {"scripts/.content_standards_allow": "# header\n" + allow}
    if notice is not None:
        files["vendor/NOTICES.txt"] = notice
    return tree(tmp, files, with_scripts=("check_content_standards.py",))


def standards(root: Path) -> subprocess.CompletedProcess:
    return run(root, "check_content_standards.py")


def test_an_unlisted_notice_with_an_em_dash_fails(tmp_path):
    res = standards(notice_tree(tmp_path, ""))
    assert res.returncode == 1 and "vendor/NOTICES.txt:1" in res.stdout, res.stdout


def test_a_listed_notice_with_its_digest_passes(tmp_path):
    res = standards(notice_tree(tmp_path, f"vendor/NOTICES.txt {sha(NOTICE)} {URL}\n"))
    assert res.returncode == 0 and "check_content_standards: OK" in res.stdout and "1 allow-listed" in res.stdout, res.stdout


def test_the_digest_is_taken_over_lf_normalised_content(tmp_path):
    crlf = "line one \u2014 a\r\nline two\r\n"
    lf = crlf.replace("\r", "")
    res = standards(notice_tree(tmp_path, f"vendor/NOTICES.txt {sha(lf)} {URL}\n", crlf))
    assert res.returncode == 0, res.stdout


def test_a_listed_notice_edited_after_its_digest_fails_naming_it(tmp_path):
    root = notice_tree(tmp_path, f"vendor/NOTICES.txt {sha(NOTICE)} {URL}\n")
    (root / "vendor/NOTICES.txt").write_bytes((NOTICE + "one more line\n").encode("utf-8"))
    res = standards(root)
    assert res.returncode == 1 and "vendor/NOTICES.txt" in res.stdout and "changed" in res.stdout, res.stdout


def test_a_listed_path_that_does_not_exist_fails(tmp_path):
    res = standards(notice_tree(tmp_path, f"vendor/GONE.txt {sha(NOTICE)} {URL}\n", notice=None))
    assert res.returncode == 1 and "vendor/GONE.txt" in res.stdout and "does not exist" in res.stdout, res.stdout


@pytest.mark.parametrize("entry", ["vendor/NOTICES.txt", "vendor/NOTICES.txt nothex https://x", f"vendor/NOTICES.txt {'a' * 64}"])
def test_a_malformed_entry_fails(tmp_path, entry):
    res = standards(notice_tree(tmp_path, entry + "\n"))
    assert res.returncode == 1 and "allow file" in res.stdout, res.stdout


def test_a_path_outside_the_repository_fails(tmp_path):
    res = standards(notice_tree(tmp_path, f"../x.txt {sha(NOTICE)} {URL}\n"))
    assert res.returncode == 1 and "outside the repository" in res.stdout, res.stdout


def test_the_allow_exempts_only_the_listed_file(tmp_path):
    root = notice_tree(tmp_path, f"vendor/NOTICES.txt {sha(NOTICE)} {URL}\n")
    (root / "docs.md").write_text("bad \u2014 dash\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    res = standards(root)
    assert res.returncode == 1 and "docs.md:1" in res.stdout and "vendor/NOTICES.txt:1" not in res.stdout, res.stdout


def test_an_absent_allow_file_means_no_exception(tmp_path):
    root = tree(tmp_path, {"vendor/NOTICES.txt": NOTICE}, with_scripts=("check_content_standards.py",))
    assert standards(root).returncode == 1


def test_the_templates_allow_file_has_a_header_and_no_entry():
    lines = (SCRIPTS / ".content_standards_allow").read_text(encoding="utf-8").splitlines()
    assert lines and all(not ln.strip() or ln.startswith("#") for ln in lines)
    assert any("sha256" in ln for ln in lines)


# ---- the workflow calls the script

def test_the_workflow_runs_the_script_and_keeps_no_inline_copy():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python scripts/check_base_integrity.py" in ci
    assert "git ls-files" not in ci and "git grep" not in ci
