"""The README-by-areas gate (scripts/check_readme_areas.py): one plant per rule, built in a temporary repository, a control,
the committed README, and the README that scripts/instantiate.py writes for a product."""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_readme_areas")
FOLDERS = ["frontend", "app", "data-pipeline", "notebooks", "data", "docs/contracts", "docs", "tests", "scripts", "deploy"]

ROWS = {
    "Web": "| Web | [`frontend/`](frontend/) | active | the workbench and its routes |",
    "API": "| API | [`app/`](app/) | dormant: this solution does not require it at the moment | the API and its tests |",
    "Core pipelines": "| Core pipelines | [`data-pipeline/`](data-pipeline/) | active | the bake and its checks |",
    "Packages": "| Packages | (PyPI) [numpy](https://pypi.org/project/numpy/) | active: consumes numpy | the packages it consumes |",
    "Notebooks": "| Notebooks | [`notebooks/`](notebooks/) | active | the notebooks in two languages |",
    "Data": "| Data | [`data/`](data/) | active | the committed derived artifacts |",
    "Contracts": "| Contracts | [`docs/contracts/`](docs/contracts/) | active | the catalog and the schemas |",
    "Documentation": "| Documentation | [`docs/`](docs/) | active | the SDD and the guides |",
    "Tests and gates": "| Tests and gates | [`tests/`](tests/), [`scripts/`](scripts/) | active | the suites and the checks |",
    "Deploy": "| Deploy | [`deploy/`](deploy/) | active: GitHub Pages | where it is deployed |",
}


PREAMBLE = "# Product\n\n[![CI](https://img.shields.io/badge/ci-passing-green)](https://github.com/o/product/actions)\n\nWhat the product is and who it serves.\n\n"


def readme(rows: dict[str, str] | None = None, head: str = "## Areas") -> str:
    body = "\n".join((rows or ROWS).values())
    return f"{PREAMBLE}{head}\n\n| Area | Folder | Status | What it holds |\n|---|---|---|---|\n{body}\n\n## Run it\n\ntext\n"


def make(tmp_path: Path, text: str) -> Path:
    for f in FOLDERS:
        (tmp_path / f).mkdir(parents=True, exist_ok=True)
    (tmp_path / "README.md").write_text(text, encoding="utf-8")
    return tmp_path


def found(root: Path, *needles: str) -> bool:
    return any(all(n in f for n in needles) for f in CHECK.findings_of(root))


def test_a_complete_readme_passes(tmp_path: Path) -> None:
    assert CHECK.findings_of(make(tmp_path, readme())) == []


def test_a_readme_without_the_areas_section_is_found(tmp_path: Path) -> None:
    assert found(make(tmp_path, readme(head="## What is in it")), "no section '## Areas'")
    (tmp_path / "README.md").unlink()
    assert found(tmp_path, "README.md: missing")
    # a heading inside a code fence is not the section
    root = make(tmp_path, "# P\n\n```\n## Areas\n```\n")
    assert found(root, "no section '## Areas'")


def test_an_area_without_its_row_is_found(tmp_path: Path) -> None:
    for area in ROWS:
        rows = {k: v for k, v in ROWS.items() if k != area}
        assert found(make(tmp_path, readme(rows)), f"the area {area!r} has no row"), area
    rows = dict(ROWS, Web=ROWS["Web"] + "\n" + ROWS["Web"])
    assert found(make(tmp_path, readme(rows)), "'Web'", "more than one row")


def test_a_row_without_a_status_is_found(tmp_path: Path) -> None:
    rows = dict(ROWS, Data="| Data | [`data/`](data/) | in progress | the committed derived artifacts |")
    assert found(make(tmp_path, readme(rows)), "'Data'", "no status")
    rows = dict(ROWS, API="| API | [`app/`](app/) | dormant | the API and its tests |")
    assert found(make(tmp_path, readme(rows)), "'API'", "dormant with no reason")
    rows = dict(ROWS, API="| API | [`app/`](app/) | dormant: not needed | the API and its tests |")
    assert found(make(tmp_path, readme(rows)), "'API'", "dormant with no reason")
    rows = dict(ROWS, Web="| Web | [`frontend/`](frontend/) | active |  |")
    assert found(make(tmp_path, readme(rows)), "'Web'", "no 'What it holds' cell")


def test_a_folder_link_that_does_not_exist_is_found(tmp_path: Path) -> None:
    root = make(tmp_path, readme())
    shutil.rmtree(root / "notebooks")
    assert found(root, "'Notebooks'", "links 'notebooks/', which does not exist")
    rows = dict(ROWS, Web="| Web | [`web/`](web/) | active | the workbench and its routes |")
    assert found(make(tmp_path, readme(rows)), "'Web'", "does not link its folder frontend/")
    rows = dict(ROWS, **{"Tests and gates": "| Tests and gates | [`tests/`](tests/) | active | the suites and the checks |"})
    assert found(make(tmp_path, readme(rows)), "'Tests and gates'", "does not link its folder scripts/")


def test_the_packages_row_must_link_pypi(tmp_path: Path) -> None:
    rows = dict(ROWS, Packages="| Packages | (PyPI) | active: none yet | the packages it consumes |")
    assert found(make(tmp_path, readme(rows)), "'Packages'", "links no package on PyPI")


def test_the_template_readme_states_every_area() -> None:
    assert CHECK.findings_of(ROOT) == []
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## What is in it" not in text and "## Areas" in text


def test_the_readme_instantiate_writes_states_every_area(tmp_path: Path) -> None:
    """A product made from the template starts with a README that passes the check (the CI step runs on the first push)."""
    spec = importlib.util.spec_from_file_location("instantiate", ROOT / "scripts" / "instantiate.py")
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    args = argparse.Namespace(slug="demo", name="Demo", repo="CAOS_Demo", deploy="pages", domain="demo.example.org", visibility="public",
                              tagline_en="One line.", tagline_es="Una línea.", holder="H", year=2026, no_run=True)
    text = inst.readme(args)
    assert "## Areas" in text and re.search(r"setup\.sh --notebooks", text)
    root = make(tmp_path, text)
    for target in CHECK.LINK.findall(text):  # the docs the rows point to exist in a product (here: an empty file each)
        path = root / target.split("#")[0]
        if not target.startswith(("http", "#")) and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
    assert CHECK.findings_of(root) == []


# instantiate.py refuses a tree that is not the template: in a product the step has nothing to run on (BD-1)
TEMPLATE_ONLY = pytest.mark.skipif(not (ROOT / ".template-source").exists(),
                                   reason="instantiate runs only in the template repository (.template-source)")


@TEMPLATE_ONLY
def test_instantiate_leaves_a_passing_readme_and_the_notebooks(tmp_path: Path) -> None:
    """The whole instantiate step, on a copy: the product README passes, the example notebooks stay (the residue guard lists them)."""
    product = tmp_path / "p"
    for rel in ("scripts", "docs", "deploy", ".github", "frontend/package.json", "frontend/package-lock.json", "product.json", "VERSION",
                "CHANGELOG.md", "LICENSE", ".template-source", "notebooks", "data-pipeline", "tests", "data", "app"):
        src = ROOT / rel
        if src.is_dir():
            shutil.copytree(src, product / rel, ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".venv*", "dist"))
        elif src.is_file():
            (product / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, product / rel)
    (product / "frontend" / "public").mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(product / "scripts" / "instantiate.py"), "--slug", "demo", "--name", "Demo", "--repo", "CAOS_Demo",
                        "--deploy", "pages", "--domain", "demo.example.org", "--visibility", "public", "--tagline-en", "One line.",
                        "--tagline-es", "Una linea.", "--no-run"], capture_output=True, text=True, cwd=product)
    assert r.returncode == 0, r.stdout + r.stderr
    check = subprocess.run([sys.executable, str(product / "scripts" / "check_readme_areas.py"), str(product)], capture_output=True, text=True, cwd=product)
    assert check.returncode == 0, check.stdout
    assert (product / "notebooks" / "en" / "README.md").is_file() and not (product / ".template-source").exists()


@pytest.mark.parametrize("area", [a for a, _ in CHECK.AREAS])
def test_every_conventional_area_is_a_row_of_the_template_readme(area: str) -> None:
    assert re.search(rf"^\| {re.escape(area)} \|", (ROOT / "README.md").read_text(encoding="utf-8"), re.M), area


def test_the_areas_section_follows_the_purpose_and_the_live_urls(tmp_path: Path) -> None:
    """F15 (convention section 8): the section comes after the one-paragraph purpose and the live URLs, never before them."""
    rows = "\n".join(ROWS.values())
    table = f"## Areas\n\n| Area | Folder | Status | What it holds |\n|---|---|---|---|\n{rows}\n"
    first = make(tmp_path / "a", f"# Product\n\n{table}\n## Purpose\n\nWhat the product is. https://example.org/live\n")
    assert found(first, "'## Areas'", "after the purpose and the live URLs")
    no_url = make(tmp_path / "b", f"# Product\n\nWhat the product is and who it serves.\n\n{table}")
    assert found(no_url, "'## Areas'", "after the purpose and the live URLs")
    no_purpose = make(tmp_path / "c", f"# Product\n\n[![CI](https://img.shields.io/badge/ci-passing-green)](https://github.com/o/p/actions)\n\n{table}")
    assert found(no_purpose, "'## Areas'", "after the purpose and the live URLs")


def test_what_it_holds_is_more_than_a_dash(tmp_path: Path) -> None:
    for n, cell in enumerate(("-", "n/a", "the web")):
        rows = dict(ROWS, Web=f"| Web | [`frontend/`](frontend/) | active | {cell} |")
        assert found(make(tmp_path / str(n), readme(rows)), "'Web'", "'What it holds'", "three words"), cell


def test_a_dead_link_in_what_it_holds_is_found(tmp_path: Path) -> None:
    rows = dict(ROWS, Web="| Web | [`frontend/`](frontend/) | active | the workbench, see [the guide](docs/guides/absent.md) |")
    root = make(tmp_path, readme(rows))
    assert found(root, "'Web'", "links 'docs/guides/absent.md', which does not exist")
    (root / "docs" / "guides").mkdir(parents=True)
    (root / "docs" / "guides" / "absent.md").write_text("x", encoding="utf-8")
    assert not found(root, "'Web'", "does not exist")


def test_the_packages_row_may_link_a_release_tag_instead_of_pypi(tmp_path: Path) -> None:
    tag = "[riskvalidation v0.8.0](https://github.com/fsantibanezleal/CAOS_RiskValidation/releases/tag/v0.8.0)"
    rows = dict(ROWS, Packages=f"| Packages | (GitHub) {tag} | active: consumes riskvalidation | not yet published on PyPI |")
    assert CHECK.findings_of(make(tmp_path / "a", readme(rows))) == []
    branch = "[riskvalidation](https://github.com/fsantibanezleal/CAOS_RiskValidation/tree/main)"
    rows = dict(ROWS, Packages=f"| Packages | (GitHub) {branch} | active: consumes riskvalidation | not yet published on PyPI |")
    assert found(make(tmp_path / "b", readme(rows)), "'Packages'", "links no package on PyPI")
