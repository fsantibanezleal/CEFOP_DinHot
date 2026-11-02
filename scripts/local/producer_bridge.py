#!/usr/bin/env python3
"""Narrow calls into existing producer APIs that lack a matching CLI destination."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path


def module(path):
    spec = importlib.util.spec_from_file_location("local_producer", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    mode, target = sys.argv[1:]
    root = Path(__file__).resolve().parents[2]
    stage = Path(target).resolve()
    read_own_inventory = mode == "template-validate" and stage == root
    if (stage.is_relative_to(root) and not read_own_inventory) or not (stage / "data/derived").is_dir():
        raise ValueError("Producer bridge requires an external prepared stage.")
    sys.path.insert(0, str(root / "data-pipeline"))
    if mode == "geomet":
        producer = module(root / "data-pipeline/run_geomet.py")
        producer.build(output_path=stage / "data/derived/source/geomet_lct_benchmark.json")
        producer.fit_checkpoint(checkpoint_path=stage / "checkpoints/oreflow/geomet_lct.joblib")
        return
    if mode == "template-finalize":
        nested = stage / "data/derived/models"
        if nested.is_dir():
            for source in nested.iterdir():
                if source.is_symlink() or not source.resolve().is_relative_to(stage):
                    raise ValueError("Model escaped the external stage.")
                destination = stage / "models" / source.name
                if destination.exists():
                    raise ValueError("Duplicate staged model destination.")
                shutil.move(str(source), destination)
            nested.rmdir()
    if mode in ("template-finalize", "oreflow-finalize"):
        from pipeline.core import readiness

        document = readiness.compute(
            repo_root=stage, derived_root=stage / "data/derived", models_dir=stage / "models"
        )
        readiness.write(stage / "data/derived", document)
        return
    if mode == "template-validate":
        from pipeline import registry

        index = json.loads((stage / "data/derived/manifests/index.json").read_text(encoding="utf-8"))
        expected = {case.id for case in registry.list_cases()}
        actual = [row["case_id"] for row in index["cases"]]
        if set(actual) != expected or len(actual) != len(set(actual)):
            raise ValueError("Partial case inventory cannot be released.")
        return
    raise ValueError("Unknown producer bridge operation.")


if __name__ == "__main__":
    main()
