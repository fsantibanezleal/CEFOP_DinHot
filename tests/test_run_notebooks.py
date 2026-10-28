"""The runner's temp root and method-package guard (scripts/run_notebooks.py, template 0.11.000, NB-041 to NB-046).

These tests run the runner in process with a stand-in for the execution, so they need no notebook environment: what they hold
is where the ``--check`` copies are written, and what the runner refuses before it executes anything."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load("run_notebooks")
MESSAGE = "run_notebooks: --check needs a temp root: pass --tmp DIR or set CAOS_TEMP_ROOT (the device's temp root)"
REL = Path("notebooks") / "en" / "01-basics" / "01-note.ipynb"


def notebook(code: str = "# a cell\nprint(1)") -> dict:
    return {"cells": [{"cell_type": "markdown", "id": "a", "metadata": {}, "source": "# T"},
                      {"cell_type": "code", "id": "b", "metadata": {}, "source": code, "execution_count": None, "outputs": []}],
            "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


@pytest.fixture
def product(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tiny product, the runner pointed at it, with no notebook venv to re-run in."""
    base = tmp_path / "product"
    (base / REL).parent.mkdir(parents=True)
    (base / REL).write_text(json.dumps(notebook()), encoding="utf-8")
    (base / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    (base / "data").mkdir()
    (base / "data" / "x.json").write_text("{}", encoding="utf-8")
    (base / "scripts").mkdir()
    (base / "scripts" / "check_notebooks.py").write_bytes((ROOT / "scripts" / "check_notebooks.py").read_bytes())
    monkeypatch.setattr(RUNNER, "ROOT", base)
    monkeypatch.setattr(RUNNER, "NOTEBOOKS", base / "notebooks")
    monkeypatch.setattr(RUNNER, "VENV", tmp_path / "no-venv")
    monkeypatch.setattr(RUNNER, "__file__", str(base / "scripts" / "run_notebooks.py"))
    monkeypatch.setattr(RUNNER, "warm_matplotlib", lambda: None)
    for name in ("nbclient", "nbformat"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.delenv("CAOS_TEMP_ROOT", raising=False)
    return base


def stand_in(monkeypatch: pytest.MonkeyPatch, base: Path) -> list[Path]:
    """An execution that writes a byte-identical copy to ``dest``; the list records every path it was given."""
    paths: list[Path] = []

    def execute(src: Path, dest: Path) -> str | None:
        paths.extend([src, dest])
        dest.write_bytes((base / REL).read_bytes())
        return None
    monkeypatch.setattr(RUNNER, "execute", execute)
    return paths


def run(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["run_notebooks.py", *args])
    return RUNNER.main()


def under(root: Path, paths: list[Path]) -> bool:
    return bool(paths) and all(root.resolve() in p.resolve().parents for p in paths)


def test_adversarial_check_without_a_temp_root_stops_with_exit_2(product: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    paths = stand_in(monkeypatch, product)
    assert run(monkeypatch, "--check") == 2
    assert MESSAGE in capsys.readouterr().out
    assert paths == [], "nothing runs without a temp root"
    monkeypatch.setenv("CAOS_TEMP_ROOT", "")  # an empty variable names no root
    assert run(monkeypatch, "--check") == 2
    assert MESSAGE in capsys.readouterr().out


def test_adversarial_check_writes_only_under_the_temp_root_and_removes_it(product: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = stand_in(monkeypatch, product)
    system_before = set(Path(tempfile.gettempdir()).glob("run-notebooks-*"))
    committed = {p: p.read_bytes() for p in product.rglob("*") if p.is_file()}
    tmp = tmp_path / "temp-root"
    tmp.mkdir()
    assert run(monkeypatch, "--check", "--tmp", str(tmp)) == 0
    assert under(tmp, paths), paths
    assert list(tmp.iterdir()) == [], "the fresh folder is removed after the run"
    assert {p: p.read_bytes() for p in product.rglob("*") if p.is_file()} == committed, "--check writes nothing in the product"
    assert set(Path(tempfile.gettempdir()).glob("run-notebooks-*")) == system_before, "never the system temp folder"


def test_adversarial_the_environment_variable_names_the_temp_root(product: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = stand_in(monkeypatch, product)
    env_root, cli_root = tmp_path / "env-root", tmp_path / "cli-root"
    env_root.mkdir()
    cli_root.mkdir()
    monkeypatch.setenv("CAOS_TEMP_ROOT", str(env_root))
    assert run(monkeypatch, "--check") == 0
    assert under(env_root, paths) and list(env_root.iterdir()) == []
    paths.clear()
    assert run(monkeypatch, "--check", "--tmp", str(cli_root)) == 0  # the argument wins over the variable
    assert under(cli_root, paths) and list(env_root.iterdir()) == []


def test_adversarial_a_missing_temp_root_is_created_and_a_file_is_refused(product: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                         capsys: pytest.CaptureFixture) -> None:
    paths = stand_in(monkeypatch, product)
    assert run(monkeypatch, "--check", "--tmp", str(tmp_path / "new" / "root")) == 0 and paths
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")
    assert run(monkeypatch, "--check", "--tmp", str(afile)) == 2
    assert "not a folder" in capsys.readouterr().out


def declare(base: Path, packages, pin: str | None) -> None:
    (base / "product.json").write_text(json.dumps({"method_packages": packages}), encoding="utf-8")
    (base / "notebooks" / "requirements.txt").write_text((pin + "\n") if pin else "", encoding="utf-8")


def test_adversarial_a_method_package_that_is_not_installed_fails_the_runner(product: Path, monkeypatch: pytest.MonkeyPatch,
                                                                            capsys: pytest.CaptureFixture) -> None:
    paths = stand_in(monkeypatch, product)
    declare(product, ["not-installed-anywhere"], "not-installed-anywhere==0.1.0")
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "not-installed-anywhere" in out and "not installed" in out
    assert paths == [], "no notebook runs when the environment lacks a method package"


def test_adversarial_the_runner_names_a_missing_pin_and_a_copied_method(product: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                                       capsys: pytest.CaptureFixture) -> None:
    site = tmp_path / "site"
    (site / "fakepkg").mkdir(parents=True)
    (site / "fakepkg" / "__init__.py").write_text("def fit_model(x):\n    return x\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(site))
    paths = stand_in(monkeypatch, product)
    declare(product, ["fakepkg"], None)
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "fakepkg" in out and "no exact pin" in out and paths == []
    declare(product, ["fakepkg"], "fakepkg==1.0.0")
    (product / REL).write_text(json.dumps(notebook("# a copy\ndef fit_model(x):\n    return x")), encoding="utf-8")
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "01-note.ipynb" in out and "defines 'fit_model'" in out and "fakepkg" in out and paths == []
    (product / REL).write_text(json.dumps(notebook()), encoding="utf-8")
    assert run(monkeypatch) == 0, "a declared, installed, pinned package with no copy lets the run start"
    assert paths


def test_adversarial_without_method_packages_the_runner_is_unchanged(product: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = stand_in(monkeypatch, product)
    assert run(monkeypatch) == 0 and paths
    paths.clear()
    (product / "product.json").write_text(json.dumps({"method_packages": []}), encoding="utf-8")
    assert run(monkeypatch) == 0 and paths
