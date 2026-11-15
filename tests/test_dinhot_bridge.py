"""The local workflow's DinHot steps (scripts/local/dinhot_bridge.py): the evaluation step re-measures the model metrics of a stage."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dinhot_bridge", ROOT / "scripts" / "local" / "dinhot_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def test_the_evaluation_reads_the_staged_graphs_and_writes_the_stage_metrics(tmp_path: Path) -> None:
    stage = tmp_path / "caos-local-x"
    command, cwd, env = bridge.evaluation_command(stage, {"CAOS_DATA_ROOT": str(tmp_path / "data")})
    models = str(stage / "data" / "derived" / "models")
    assert command[:3] == [sys.executable, "-m", "pipeline.stages.evaluate"]
    assert command[command.index("--models-dir") + 1] == models and command[command.index("--out") + 1] == models
    assert cwd == ROOT / "data-pipeline"
    assert env["DINHOT_LEARNED_DIR"] == str(tmp_path / "data" / "dinhot" / "learned")


def test_a_named_held_out_folder_wins_over_the_data_root(tmp_path: Path) -> None:
    _, _, env = bridge.evaluation_command(tmp_path, {"CAOS_DATA_ROOT": str(tmp_path / "data"), "DINHOT_LEARNED_DIR": str(tmp_path / "held")})
    assert env["DINHOT_LEARNED_DIR"] == str(tmp_path / "held")


def test_adversarial_without_a_data_root_the_evaluation_stops_with_the_reason(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="CAOS_DATA_ROOT"):
        bridge.evaluation_command(tmp_path, {})


def test_the_generation_plan_evaluates_after_the_bake_and_before_finalize() -> None:
    import json
    steps = json.loads((ROOT / "scripts" / "local" / "workflow.json").read_text(encoding="utf-8"))["generation"]
    names = [(s["script"], s["args"][0]) for s in steps]
    assert ("scripts/local/dinhot_bridge.py", "evaluate") in names
    i = names.index(("scripts/local/dinhot_bridge.py", "evaluate"))
    assert names.index(("data-pipeline/run.py", "all")) < i < names.index(("scripts/local/dinhot_bridge.py", "finalize"))
