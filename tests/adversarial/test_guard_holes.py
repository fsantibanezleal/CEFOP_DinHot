"""The holes an adversarial review found in the spec-area guards (0.05.000), one plant each: a defect planted in a copy of
the repository's real files, the real guard run on it, exit 1 and the message that names the defect expected. The ids
(S-1a, C-3, T-8, B-1 ...) are the rows of the review's refutation table
(CAOS_MANAGE wip/product-template/review-0-05-000-guards-2026-10-11.md, D2).

Each plant copies only the inputs its guard reads (`make_tree`), so the suite stays cheap; every plant asserts the guard
printed, so a guard that never ran cannot pass."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from planting import SDD, sdd, sdd_text, section, edit, guard, make_tree


TECH_INPUTS = ("scripts/check_tech_matrix.py", "docs/design/SDD.md", "requirements*.txt", "data-pipeline/requirements.txt",
               "notebooks/requirements.txt", "pyproject.toml", "frontend/package.json", "frontend/package-lock.json")
BUDGET_INPUTS = ("scripts/check_ci_budget.py", ".github", "requirements-precompute.txt")


def test_the_slim_tree_passes_the_guard_it_stands_for(sdd_repo: Path) -> None:
    r = guard(sdd_repo, "check_sdd.py", ok_marker="check_sdd: OK")
    assert r.returncode == 0, r.stdout


@pytest.fixture
def tech_repo(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *TECH_INPUTS)


def _tech(repo: Path):
    return guard(repo, "check_tech_matrix.py")


def test_tech_the_slim_tree_passes(tech_repo: Path) -> None:
    r = guard(tech_repo, "check_tech_matrix.py", ok_marker="check_tech_matrix: OK")
    assert r.returncode == 0, r.stdout


def test_tech_t1b_a_pin_added_only_in_requirements_api(tech_repo: Path) -> None:
    api = tech_repo / "requirements-api.txt"
    api.write_text(api.read_text(encoding="utf-8") + "uvicorn[standard]==0.54.0\nfastapi==0.144.0\n", encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "uvicorn" in r.stdout and "fastapi" in r.stdout, r.stdout


def test_tech_t3_a_range_in_package_json_that_the_lock_does_not_record(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"react": "^19.3.0"', '"react": "^19.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "react" in r.stdout, r.stdout


def test_tech_t3b_a_greater_than_range(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"vite": "8.3.5"', '"vite": ">=8.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout, r.stdout


def test_tech_t3c_an_x_range_that_the_sdd_repeats(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"react": "^19.3.0"', '"react": "19.x"')
    edit(tech_repo, SDD, "| react | 19.3.0 |", "| react | 19.x |")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "react" in r.stdout, r.stdout


def test_tech_t8_a_range_the_lock_does_not_satisfy(tech_repo: Path) -> None:
    edit(tech_repo, "frontend/package.json", '"vite": "8.3.5"', '"vite": "^9.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout, r.stdout


def test_tech_a_lock_whose_version_does_not_satisfy_its_own_spec(tech_repo: Path) -> None:
    lock = tech_repo / "frontend/package-lock.json"
    doc = json.loads(lock.read_text(encoding="utf-8"))
    doc["packages"][""]["devDependencies"]["vite"] = "^9.0.0"
    lock.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    edit(tech_repo, "frontend/package.json", '"vite": "8.3.5"', '"vite": "^9.0.0"')
    r = _tech(tech_repo)
    assert r.returncode == 1 and "vite" in r.stdout and "8.3.5" in r.stdout, r.stdout


def test_tech_t4_a_dependency_in_optional_dependencies(tech_repo: Path) -> None:
    pkg = tech_repo / "frontend/package.json"
    doc = json.loads(pkg.read_text(encoding="utf-8"))
    doc["optionalDependencies"] = {"left-pad": "^1.3.0"}
    pkg.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "left-pad" in r.stdout, r.stdout


def test_tech_t5b_the_same_package_pinned_twice_with_different_versions(tech_repo: Path) -> None:
    path = tech_repo / "requirements-precompute.txt"
    path.write_text("numpy==2.4.7\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "numpy" in r.stdout and "2.4.7" in r.stdout, r.stdout


def test_tech_t6_an_editable_unpinned_requirement(tech_repo: Path) -> None:
    path = tech_repo / "requirements-dev.txt"
    path.write_text(path.read_text(encoding="utf-8") + "-e git+https://github.com/example/unpinned.git#egg=unpinned\n", encoding="utf-8")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "unpinned" in r.stdout, r.stdout


def test_tech_t7_a_wildcard_pin(tech_repo: Path) -> None:
    edit(tech_repo, "data-pipeline/requirements.txt", "numpy==2.4.6", "numpy==2.*")
    edit(tech_repo, SDD, "| numpy | 2.4.6 |", "| numpy | 2.* |")
    r = _tech(tech_repo)
    assert r.returncode == 1 and "numpy" in r.stdout, r.stdout


@pytest.fixture
def budget_repo(tmp_path: Path) -> Path:
    return make_tree(tmp_path / "repo", *BUDGET_INPUTS)


# the allowance as the workflow writes it: the template also runs tests/template/adversarial (BD-3), a product does not
ALLOWED = next(ln.strip()[len("run: "):] for ln in (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml")
               .read_text(encoding="utf-8").splitlines() if ln.strip().startswith("run: pip install pytest=="))


def _step(repo: Path, command: str) -> None:
    edit(repo, ".github/workflows/ci.yml", f"run: {ALLOWED}", command)


def test_ci_budget_the_allowance_itself_passes(budget_repo: Path) -> None:
    r = guard(budget_repo, "check_ci_budget.py", ok_marker="ci budget: OK")
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("plant,command", [
    ("B-1 the whole suite after the allowed path", "run: pip install pytest==9.1.1 && python -m pytest tests/adversarial tests/ -q"),
    ("B-2 a path that climbs out", "run: pip install pytest==9.1.1 && python -m pytest tests/adversarial/.. -q"),
    ("B-3 a second pytest on the line", "run: python -m pytest tests/adversarial -q; python -m pytest -q"),
    ("B-4 an extra test file", "run: python -m pytest tests/adversarial tests/test_pipeline_smoke.py -q"),
    ("B-7 a line continuation", "run: |\n          pip install pytest==9.1.1 && python -m pytest tests/adversarial \\\n          tests/"),
    ("B-8 config overrides and an extra file", "run: pip install pytest==9.1.1 && python -m pytest tests/adversarial -q --rootdir=. "
                                              "--override-ini=testpaths=tests -c pyproject.toml tests/test_pipeline_smoke.py"),
    ("B-9 pyargs", "run: python -m pytest tests/adversarial --pyargs pipeline"),
    ("B-9 a plugin", "run: python -m pytest tests/adversarial -p no:cacheprovider"),
    ("B-9 an and-chain", "run: python -m pytest tests/adversarial && python -m pytest tests"),
])
def test_ci_budget_an_allowance_that_is_broader_than_the_adversarial_suite(budget_repo: Path, plant: str, command: str) -> None:
    _step(budget_repo, command)
    r = guard(budget_repo, "check_ci_budget.py")
    assert r.returncode == 1 and "tests run locally" in r.stdout, r.stdout


def test_ci_budget_a_pytest_install_on_its_own_line_is_not_a_test_run(budget_repo: Path) -> None:
    _step(budget_repo, "run: |\n          pip install pytest==9.1.1\n          python -m pytest tests/adversarial -q")
    r = guard(budget_repo, "check_ci_budget.py", ok_marker="ci budget: OK")
    assert r.returncode == 0, r.stdout


def _replace_line(repo: Path, rel: str, prefix: str, new: str) -> None:
    """Replace the whole line that starts with ``prefix``; fails when there is none (a plant that plants nothing)."""
    path = repo / rel
    lines = path.read_bytes().decode("utf-8").split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{rel}: {len(hits)} lines start with {prefix!r}"
    lines[hits[0]] = new
    path.write_bytes("\n".join(lines).encode("utf-8"))


def _brief_span(text: str) -> tuple[int, int]:
    """The brief section: from its heading to the next level-2 heading."""
    return section(text, "Executive brief")


def test_sdd_rereview_m3b_a_brief_after_resources_when_the_headings_are_numbered(sdd_repo: Path) -> None:
    text = sdd_text(sdd_repo)
    a, b = _brief_span(text)
    brief = text[a:b]
    text = text[:a] + text[b:]
    at = text.index("## Lanes\n")
    text = text[:at] + brief + text[at:]
    text = text.replace("## Problem and non-goals", "## 1. Problem and non-goals", 1)
    (sdd_repo / SDD).write_bytes(text.encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "right after" in r.stdout, r.stdout


def test_sdd_rereview_xs2_numbered_headings_in_place_pass(sdd_repo: Path) -> None:
    text = sdd_text(sdd_repo)
    text = text.replace("## Problem and non-goals", "## 1. Problem and non-goals", 1).replace("## Executive brief", "## 2. Executive brief", 1)
    (sdd_repo / SDD).write_bytes(text.encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 0, r.stdout


def test_sdd_rereview_m3d_the_brief_inside_a_tilde_fence_with_a_backtick_line(sdd_repo: Path) -> None:
    text = sdd_text(sdd_repo)
    a, b = _brief_span(text)
    (sdd_repo / SDD).write_bytes((text[:a] + "~~~\n```\n" + text[a:b] + "```\n~~~\n\n" + text[b:]).encode("utf-8"))
    r = sdd(sdd_repo)
    assert r.returncode == 1, r.stdout


def test_sdd_rereview_the_data_line_inside_a_code_block_is_not_the_data_line(sdd_repo: Path) -> None:
    _replace_line(sdd_repo, SDD, "Data file: content/executive.json", "```\nData file: content/executive.json\n```")
    r = sdd(sdd_repo)
    assert r.returncode == 1 and "Data file: content/executive.json" in r.stdout, r.stdout


@pytest.mark.parametrize("plant,command", [
    ("M10a a plain scalar continued on the next line", "run: python -m pytest tests/adversarial\n          tests/"),
    ("M10b a folded block", "run: >\n          python -m pytest tests/adversarial\n          tests/"),
    ("M10c a literal block indented by nine spaces", "run: |\n         pip install pytest==9.1.1\n         python -m pytest -q"),
    ("M10d PYTEST_ADDOPTS on the step", "env:\n          PYTEST_ADDOPTS: \"tests --override-ini=addopts=\"\n        run: " + ALLOWED),
    ("M10d PYTEST_ADDOPTS exported in the command", "run: export PYTEST_ADDOPTS=tests && python -m pytest tests/adversarial"),
])
def test_ci_budget_rereview_an_allowance_broader_than_the_yaml_shows(budget_repo: Path, plant: str, command: str) -> None:
    _step(budget_repo, command)
    r = guard(budget_repo, "check_ci_budget.py")
    assert r.returncode == 1 and ("tests run locally" in r.stdout or "PYTEST_" in r.stdout), r.stdout


def test_ci_budget_rereview_pytest_addopts_at_the_top_of_the_workflow(budget_repo: Path) -> None:
    edit(budget_repo, ".github/workflows/ci.yml", "\nconcurrency:\n", "\nenv:\n  PYTEST_ADDOPTS: tests\nconcurrency:\n")
    r = guard(budget_repo, "check_ci_budget.py")
    assert r.returncode == 1 and "PYTEST_ADDOPTS" in r.stdout, r.stdout


def test_ci_budget_rereview_m10f_the_allowance_as_a_folded_block_passes(budget_repo: Path) -> None:
    _step(budget_repo, "run: >\n          pip install pytest==9.1.1 &&\n          python -m pytest tests/adversarial -q")
    r = guard(budget_repo, "check_ci_budget.py", ok_marker="ci budget: OK")
    assert r.returncode == 0, r.stdout
