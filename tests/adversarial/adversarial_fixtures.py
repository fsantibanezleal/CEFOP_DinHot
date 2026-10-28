"""Fixtures of the adversarial tests (0.05.000): a throwaway copy of the repository's relevant files, one planted
defect, the real guard run as a subprocess. The two conftest.py files (tests/adversarial/ and tests/template/adversarial/)
import them from here, so the fixtures exist once (BD-3).

The copy holds every file the guards read and none of the heavy or generated trees (node_modules, dist, venvs). The
tests need only the standard library and pytest, so CI can run them in the checks job; the root conftest's autouse
fixture imports the pipeline (numpy), so it is replaced here by a no-op."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from planting import add_schema, make_tree

ROOT = Path(__file__).resolve().parents[2]
SKIP = shutil.ignore_patterns("node_modules", "dist", "gate-output", "__pycache__", ".venv*", ".git", ".pytest_cache",
                              ".ruff_cache", "*.pyc", "build")
COPIED = ("scripts", "docs", "data", "data-pipeline", "models", "frontend", "tests", ".github", "deploy", "app", "notebooks")
FILES = ("VERSION", "product.json", "CHANGELOG.md", "requirements-precompute.txt", "requirements-dev.txt",
         "requirements-gpu.txt", "requirements-api.txt", ".template-source", "pyproject.toml")


@pytest.fixture(autouse=True)
def _sandboxed_pipeline() -> None:
    """Overrides tests/conftest.py: these tests import nothing of the pipeline."""
    return None


@pytest.fixture(scope="session")
def base_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("repo-base")
    for name in COPIED:
        if (ROOT / name).exists():
            shutil.copytree(ROOT / name, base / name, ignore=SKIP)
    for name in FILES:
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, base / name)
    shutil.copytree(ROOT / "content", base / "content")
    return add_schema(base)


@pytest.fixture
def repo(base_copy: Path, tmp_path: Path) -> Path:
    """A fresh copy of the repository's relevant files, to plant one defect in."""
    dest = tmp_path / "repo"
    shutil.copytree(base_copy, dest)
    return dest


SDD_INPUTS = ("scripts/*.py", "docs/design", "tests", "data", "frontend/src/**/*.test.ts", "frontend/src/**/*.test.tsx", "frontend/scripts",
              "requirements*.txt", "data-pipeline/requirements.txt", "content", "frontend/public/executive")


@pytest.fixture
def sdd_repo(tmp_path: Path) -> Path:
    """The inputs the spec guard reads (check_sdd.py), copied into a slim tree to plant one defect in."""
    return add_schema(make_tree(tmp_path / "repo", *SDD_INPUTS))


DOC_INPUTS = ("scripts/check_documents.py", "scripts/check_contracts.py", "tests/contracts/contract_schemas.py", "docs/contracts", "data", "models")


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    """The inputs the document guard reads (check_documents.py), copied into a slim tree to plant one defect in."""
    return make_tree(tmp_path / "repo", *DOC_INPUTS)
