"""Plants of template 0.15.007 (#120): a ``stage_inputs`` entry that is a version-stamped document is refused before the
generation starts, because the generation produces such a document and the bake refuses a stale one only at its end.

Product-agnostic: each test plants a throwaway product tree with its own ``workflow.json`` and runs the real ``workflow.py``
(``generate``, ``validate_stage`` and the ``generate`` command line). The generation command of every plant writes a marker, so a
test proves that the generation never ran, not only that an error was printed."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MARKER = "generation-ran.marker"
STAMPED = "data/derived/model-metrics.json"


@pytest.fixture
def workflow():
    spec = importlib.util.spec_from_file_location("stamped_inputs_workflow", ROOT / "scripts/local/workflow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def plant(tmp_path: Path, monkeypatch, workflow, inputs: dict[str, str]):
    """A minimal product whose generation command writes MARKER; ``inputs`` maps each authored stage input to its text."""
    root = tmp_path / "product tree"
    put(root / "VERSION", (ROOT / "VERSION").read_text(encoding="utf-8"))
    put(root / "docs/contracts/catalog.md", "# Catalog\n")
    put(root / "producer.py", f"from pathlib import Path\nPath({str(tmp_path / MARKER)!r}).write_text('ran')\n")
    for name, text in inputs.items():
        put(root / name, text)
    config = {
        "primary_environment": ".venv",
        "generation_environments": [".venv"],
        "environments": [{"path": ".venv", "requirements": []}],
        "stage_inputs": list(inputs),
        "promote": ["data/derived", "models"],
        "required": [],
        "generation": [{"script": "producer.py", "args": []}],
        "validators": [],
    }
    put(root / "scripts/local/workflow.json", json.dumps(config))
    monkeypatch.setattr(workflow, "venv_python", lambda *_: Path(sys.executable))
    env = {**os.environ, "CAOS_TEMP_ROOT": str(tmp_path / "scratch"), "PYTHONDONTWRITEBYTECODE": "1"}
    return root, config, env


def test_adversarial_a_stamped_stage_input_is_refused_before_the_generation(workflow, tmp_path, monkeypatch):
    stamped = json.dumps({"engine_version": "an-older-release", "metrics": {"r2": 0.9}})
    root, config, env = plant(tmp_path, monkeypatch, workflow, {"data/examples/params.csv": "a,b\n1,2\n", STAMPED: stamped})
    with pytest.raises(workflow.Failure) as refusal:
        workflow.generate(root, config, env)
    message = str(refusal.value)
    assert STAMPED in message, message
    assert "produced by the generation" in message and "never carried" in message, message
    assert not (tmp_path / MARKER).exists(), "the generation command ran although a stamped input was declared"
    assert not list((tmp_path / "scratch").glob("caos-local-*")), "a stage was created before the refusal"


def test_adversarial_a_product_version_stamp_is_refused_too(workflow, tmp_path, monkeypatch):
    root, config, env = plant(tmp_path, monkeypatch, workflow, {"models/readiness.json": json.dumps({"product_version": "an-older-release"})})
    with pytest.raises(workflow.Failure, match="models/readiness.json"):
        workflow.generate(root, config, env)
    assert not (tmp_path / MARKER).exists()


def test_adversarial_json_suffix_is_case_insensitive(workflow, tmp_path, monkeypatch):
    """Windows treats .JSON and .json as the same file type; the authored-input guard must do so on every platform."""
    name = "data/derived/model-metrics.JSON"
    root, config, env = plant(tmp_path, monkeypatch, workflow, {name: json.dumps({"engine_version": "an-older-release"})})
    with pytest.raises(workflow.Failure, match="model-metrics.JSON"):
        workflow.generate(root, config, env)
    assert not (tmp_path / MARKER).exists(), "a version-stamped .JSON input reached the generation command"


def test_adversarial_the_command_line_refuses_with_the_file_name_and_runs_nothing(workflow, tmp_path, monkeypatch, capsys):
    root, _, env = plant(tmp_path, monkeypatch, workflow, {STAMPED: json.dumps({"engine_version": "an-older-release"})})
    for key in ("CAOS_TEMP_ROOT",):
        monkeypatch.setenv(key, env[key])
    code = workflow.main(["generate", "--root", str(root)])
    assert code != 0
    assert STAMPED in capsys.readouterr().err
    assert not (tmp_path / MARKER).exists()


def test_adversarial_the_admission_path_refuses_the_same_input(workflow, tmp_path, monkeypatch):
    """``--from-stage`` admission reads ``stage_inputs`` too (validate_stage), so both entry points agree."""
    root, config, env = plant(tmp_path, monkeypatch, workflow, {STAMPED: json.dumps({"engine_version": (ROOT / "VERSION").read_text().strip()})})
    stage = tmp_path / "stage"
    (stage / "data/derived").mkdir(parents=True)
    (stage / "models").mkdir()
    with pytest.raises(workflow.Failure, match="model-metrics.json"):
        workflow.validate_stage(root, config, stage, Path(sys.executable), env)


@pytest.mark.parametrize("name,text", [
    ("data/examples/params.csv", "a,b\n1,2\n"),
    ("config/settings.json", json.dumps({"seed": 7, "engine": "x"})),
    ("config/list.json", json.dumps([{"engine_version": "an-older-release"}])),
    ("config/broken.json", "{not json"),
])
def test_adversarial_plain_authored_inputs_are_never_refused(workflow, tmp_path, monkeypatch, name, text):
    root, config, env = plant(tmp_path, monkeypatch, workflow, {name: text})
    try:
        workflow.generate(root, config, env)
    except (workflow.Failure, OSError):
        pass  # the plant produces no payload, so the admission after the generation may refuse; only the start matters here
    assert (tmp_path / MARKER).is_file(), "a plain authored input was refused before the generation"
    stages = list((tmp_path / "scratch").glob("caos-local-*"))
    assert stages and (stages[0] / name).read_bytes() == (root / name).read_bytes()


def test_adversarial_an_absent_stage_input_keeps_its_refusal(workflow, tmp_path, monkeypatch):
    root, config, env = plant(tmp_path, monkeypatch, workflow, {"data/examples/params.csv": "a\n"})
    (root / "data/examples/params.csv").unlink()
    with pytest.raises(workflow.Failure, match="Missing authored stage input: data/examples/params.csv"):
        workflow.generate(root, config, env)


def test_the_template_workflow_config_passes(workflow):
    inputs = workflow.authored_inputs(ROOT, workflow.settings(ROOT))
    assert list(inputs) == ["data/examples/params.csv"]
