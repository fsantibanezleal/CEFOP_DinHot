"""Adversarial plants for the README by areas (RP-001 to RP-005, RP-008 to RP-010): each requirement is attacked on a copy of DinHot's own
README, with the real guard (``scripts/check_readme_areas.py``) run as a subprocess. The unplanted copy is the control: it passes, so a plant
that fails proves the rule and not a broken copy. Standard library and pytest only, so CI runs them."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from planting import ROOT, guard

LINK = re.compile(r"\]\(([^)]+)\)")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """DinHot's README and the guard, with every repository path the README links present (as a placeholder)."""
    dest = tmp_path / "repo"
    (dest / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "README.md", dest / "README.md")
    shutil.copyfile(ROOT / "scripts" / "check_readme_areas.py", dest / "scripts" / "check_readme_areas.py")
    for target in LINK.findall((ROOT / "README.md").read_text(encoding="utf-8")):
        rel = target.split("#")[0]
        if not rel or re.match(r"^[a-z]+:", rel):
            continue
        path = dest / rel
        if rel.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    assert guard(dest, "check_readme_areas.py", str(dest)).returncode == 0, "the unplanted copy must pass"
    return dest


def edit(repo: Path, old: str, new: str) -> None:
    path = repo / "README.md"
    text = path.read_text(encoding="utf-8")
    assert old in text, f"README.md does not contain {old!r}: the plant would change nothing"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def fails(repo: Path, *needles: str) -> None:
    result = guard(repo, "check_readme_areas.py", str(repo))
    assert result.returncode == 1, result.stdout
    for needle in needles:
        assert needle in result.stdout, (needle, result.stdout)


def areas(repo: Path) -> tuple[str, str, str]:
    text = (repo / "README.md").read_text(encoding="utf-8")
    start = text.index("## Areas")
    end = text.index("\n## ", start + 5)
    return text[:start], text[start:end], text[end:]


def test_adversarial_a_readme_without_areas_is_found(repo: Path) -> None:
    edit(repo, "## Areas", "## What is in it")
    fails(repo, "no section '## Areas'")


def test_adversarial_a_dropped_area_row_is_found(repo: Path) -> None:
    text = (repo / "README.md").read_text(encoding="utf-8")
    (repo / "README.md").write_text("\n".join(ln for ln in text.split("\n") if not ln.startswith("| Notebooks |")), encoding="utf-8")
    fails(repo, "the area 'Notebooks' has no row")


def test_adversarial_a_row_with_no_status_is_found(repo: Path) -> None:
    edit(repo, "| [`data/`](data/) | active |", "| [`data/`](data/) | somewhere in between |")
    fails(repo, "the area 'Data' has no status")
    edit(repo, "dormant: this solution does not require it at the moment", "dormant")
    fails(repo, "'API' is dormant with no reason")


def test_adversarial_a_dead_folder_link_is_found(repo: Path) -> None:
    shutil.rmtree(repo / "deploy")
    fails(repo, "links 'deploy/', which does not exist")


def test_adversarial_a_packages_row_without_pypi_is_found(repo: Path) -> None:
    pre, block, rest = areas(repo)
    row = next(ln for ln in block.splitlines() if ln.startswith("| Packages |"))
    cells = row.split("|")
    cells[2] = " numpy "
    cells[3] = " active: consumes numpy "
    (repo / "README.md").write_text(pre + block.replace(row, "|".join(cells)) + rest, encoding="utf-8")
    fails(repo, "links no package on PyPI")


def test_adversarial_the_areas_section_before_the_purpose_is_found(repo: Path) -> None:
    pre, block, rest = areas(repo)
    title, _, body = pre.partition("\n")
    (repo / "README.md").write_text(f"{title}\n\n{block}\n{body}{rest}", encoding="utf-8")
    fails(repo, "comes after the purpose and the live URLs")


def test_adversarial_a_row_that_holds_a_dash_is_found(repo: Path) -> None:
    pre, block, rest = areas(repo)
    row = next(ln for ln in block.splitlines() if ln.startswith("| Data |"))
    cells = row.split("|")
    cells[4] = " - "
    (repo / "README.md").write_text(pre + block.replace(row, "|".join(cells)) + rest, encoding="utf-8")
    fails(repo, "'Data'", "'What it holds'")


def test_adversarial_a_dead_document_link_in_a_row_is_found(repo: Path) -> None:
    edit(repo, "[guide 04](docs/guides/04_run-the-api.md)", "[guide 04](docs/guides/04_absent.md)")
    fails(repo, "links 'docs/guides/04_absent.md', which does not exist")
