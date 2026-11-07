"""Notebook execution resolves the runtime setup actually created."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("notebook_runtime", ROOT / "scripts/run_notebooks.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    root = tmp_path / "product"
    (root / "scripts/local").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/local/workflow.py", root / "scripts/local/workflow.py")
    external = tmp_path / "external environments"
    config = {"external_environments_required": True, "environment_namespace": "product",
              "environments": [{"path": ".venv-lessons", "when": "notebooks", "requirements": []}]}
    (root / "scripts/local/workflow.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(external))
    directory = external / "product/.venv-lessons"
    python = directory / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    python.parent.mkdir(parents=True)
    python.write_bytes(b"placeholder interpreter; never executed")
    return runner, root, directory, python


def test_declared_notebook_role_can_use_a_nonlegacy_name(runtime):
    runner, root, directory, python = runtime
    (root / ".venv-notebooks").mkdir()
    assert runner.notebook_environment() == directory
    assert runner.venv_python() == python


def test_adversarial_missing_external_root_does_not_fall_back_to_local(runtime, monkeypatch):
    runner, root, _, _ = runtime
    monkeypatch.delenv("CAOS_VENVS_ROOT")
    (root / ".venv-notebooks").mkdir()
    with pytest.raises(ValueError, match="CAOS_VENVS_ROOT"):
        runner.notebook_environment()


def test_adversarial_ambiguous_notebook_roles_are_refused(runtime):
    runner, root, _, _ = runtime
    path = root / "scripts/local/workflow.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["environments"].append({"path": ".second", "when": "notebooks", "requirements": []})
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        runner.notebook_environment()


def test_adversarial_inner_flag_cannot_select_an_unrelated_interpreter(runtime, monkeypatch):
    runner, _, _, _ = runtime
    monkeypatch.setattr(sys, "argv", ["run_notebooks", "--inner"])
    assert runner.main() == 2
