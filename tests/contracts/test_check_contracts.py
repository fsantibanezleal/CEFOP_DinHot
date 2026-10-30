"""scripts/check_contracts.py validates the catalog's `documents` column (template 0.09.000): the column is required, a
cell is `-` or globs relative to the repository root, `!` excludes, an OpenAPI row names a component after `#`."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from contract_schemas import ROOT

SCRIPT = ROOT / "scripts" / "check_contracts.py"
CATALOG = ROOT / "docs" / "contracts" / "catalog.md"


def run(text: str, tmp_path: Path) -> subprocess.CompletedProcess:
    cat = tmp_path / "catalog.md"
    cat.write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(cat), "--repo-root", str(ROOT)], capture_output=True, text=True)


def contracts_table_lines(text: str) -> tuple[list[str], int, int]:
    lines = text.split("\n")
    first = next(i for i, ln in enumerate(lines) if ln.startswith("| id | version"))
    last = first
    while last + 1 < len(lines) and lines[last + 1].startswith("|"):
        last += 1
    return lines, first, last


def with_documents(row_id: str, cell: str) -> str:
    """The template's catalog with the `documents` cell of one row replaced."""
    lines, first, last = contracts_table_lines(CATALOG.read_text(encoding="utf-8"))
    col = [c.strip() for c in lines[first].strip().strip("|").split("|")].index("documents")
    for i in range(first + 2, last + 1):
        cells = lines[i].strip().strip("|").split("|")
        if cells[0].strip() == row_id:
            cells[col] = f" {cell} "
            lines[i] = "|" + "|".join(cells) + "|"
            return "\n".join(lines)
    raise AssertionError(f"no row {row_id}")


def without_column() -> str:
    """The template's catalog with the `documents` column removed everywhere in its Contracts table."""
    lines, first, last = contracts_table_lines(CATALOG.read_text(encoding="utf-8"))
    col = [c.strip() for c in lines[first].strip().strip("|").split("|")].index("documents")
    for i in range(first, last + 1):
        cells = lines[i].strip().strip("|").split("|")
        del cells[col]
        lines[i] = "|" + "|".join(cells) + "|"
    return "\n".join(lines)


def test_the_template_catalog_is_sound(tmp_path):
    p = run(CATALOG.read_text(encoding="utf-8"), tmp_path)
    assert p.returncode == 0, p.stdout


def test_a_catalog_without_the_column_names_it_and_the_release(tmp_path):
    p = run(without_column(), tmp_path)
    assert p.returncode == 1, p.stdout
    assert "documents" in p.stdout and re.search(r"template \d\.\d\d\.\d{3}", p.stdout)


def test_a_dash_cell_is_accepted(tmp_path):
    assert run(with_documents("trace", "-"), tmp_path).returncode == 0


def test_an_empty_cell_fails(tmp_path):
    p = run(with_documents("trace", ""), tmp_path)
    assert p.returncode == 1 and "trace: empty documents" in p.stdout, p.stdout


def test_adversarial_paths_outside_the_repository_fail(tmp_path):
    for bad in ("../outside/*.json", "data/../../x.json", "/etc/x.json", "C:/x/y.json", "data\\derived\\x.json", "!../x.json"):
        p = run(with_documents("trace", f"data/derived/*/trace.json, {bad}"), tmp_path)
        assert p.returncode == 1 and "trace: documents" in p.stdout and "outside the repository" in p.stdout, (bad, p.stdout)


def test_a_dash_mixed_with_globs_fails(tmp_path):
    p = run(with_documents("trace", "-, data/derived/*/trace.json"), tmp_path)
    assert p.returncode == 1 and "trace: documents" in p.stdout, p.stdout


def test_a_row_of_exclusions_only_fails(tmp_path):
    p = run(with_documents("trace", "!data/derived/*/trace.json"), tmp_path)
    assert p.returncode == 1 and "no glob to include" in p.stdout, p.stdout


def test_a_component_is_required_on_an_openapi_row_and_forbidden_elsewhere(tmp_path):
    p = run(with_documents("api", "docs/contracts/examples/api-unavailable.json"), tmp_path)
    assert p.returncode == 1 and "api: documents" in p.stdout and "component" in p.stdout, p.stdout
    p = run(with_documents("trace", "data/derived/*/trace.json#Foo"), tmp_path)
    assert p.returncode == 1 and "trace: documents" in p.stdout and "component" in p.stdout, p.stdout
