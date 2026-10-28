"""B3 acceptance (SDD ladder row B3): median iterations to 1 percent at least two times below a random start on held-out
geometries, final metrics equal within 1 percent, model at most 1 MB.

Needs the released warmstart-model graph in ``models/``, onnxruntime and the held-out file of the data root; skipped where any is
absent. The committed ``metrics.json`` and ``evaluation-detail.json`` are checked against the criterion and a sample is re-run.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("onnxruntime")

from pipeline.io.contract import REPO_ROOT  # noqa: E402
from pipeline.io.model_card import is_valid_slot  # noqa: E402
from pipeline.model.holo.learned import evaluation, heldout  # noqa: E402

MODELS = REPO_ROOT / "models"
HELD = heldout.LEARNED_ROOT / "warmstart-heldout.npz"

pytestmark = pytest.mark.skipif(not is_valid_slot(MODELS, "warmstart-model"), reason="warmstart-model is not released: the random start answers")


def test_model_is_at_most_1_mb():
    assert (MODELS / "warmstart.onnx").stat().st_size <= 1024 * 1024


def test_committed_metrics_meet_the_criterion():
    out = REPO_ROOT / "data" / "derived" / "models"
    e = json.loads((out / "metrics.json").read_text(encoding="utf-8"))["slots"]["warmstart-model"]
    d = json.loads((out / "evaluation-detail.json").read_text(encoding="utf-8"))["warmstart-model"]
    it = e["iterations_to_1pct"]
    assert it["model"]["median"] * 2 <= it["random"]["median"], it
    diff = d["final_metrics_relative_difference_of_medians"]
    assert diff["efficiency"] <= 0.01 and diff["uniformity"] <= 0.01, diff


@pytest.mark.skipif(not HELD.is_file(), reason="the held-out file lives in the data root of the training device")
def test_sampled_held_out_geometries_need_half_the_iterations(tmp_path):
    entry, detail = evaluation.evaluate_warm(MODELS, HELD, seeds=(401,), budget=40, every=4)   # a seed the committed run did not use
    it = entry["iterations_to_1pct"]
    assert it["model"]["median"] * 2 <= it["random"]["median"], it
    assert max(detail["final_metrics_relative_difference_of_medians"].values()) <= 0.01
