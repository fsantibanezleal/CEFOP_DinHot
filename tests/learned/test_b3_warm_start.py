"""B3 (SDD ladder row B3): the criterion is median iterations to 1 percent at least two times below a random start on held-out
geometries, final metrics equal within 1 percent, model at most 1 MB. The trained candidate did NOT meet it, so the slot is not
released and the random start answers. This test records the measured negative as a documented assertion (not an xfail): the ratio
of the medians stays in the measured range, below 2, and the control without the network explains the gain.

The numbers are those of ``data/derived/models/warmstart-model-rejected.json`` (held-out file sha256 recorded there). If a model is
ever released for the slot, ``test_released_model_meets_the_criterion`` takes over and holds it to the criterion.
"""
from __future__ import annotations

import json

import pytest

from pipeline.io.contract import REPO_ROOT
from pipeline.io.model_card import is_valid_slot

MODELS = REPO_ROOT / "models"
REJECTED = REPO_ROOT / "data" / "derived" / "models" / "warmstart-model-rejected.json"
RELEASED = is_valid_slot(MODELS, "warmstart-model")


@pytest.mark.skipif(RELEASED, reason="the slot is released: the criterion test below applies")
def test_measured_negative_the_two_times_criterion_is_not_met():
    rec = json.loads(REJECTED.read_text(encoding="utf-8"))
    it = rec["metrics"]["iterations_to_1pct"]
    ratio = it["random"]["median"] / it["model"]["median"]
    assert rec["ratio_random_over_model_median_iterations"] == pytest.approx(ratio)
    assert 1.5 < ratio < 2.0, ratio                                      # measured 1.75: better than 1, short of the 2 required
    diff = rec["final_metrics_relative_difference_of_medians"]
    assert diff["efficiency"] > 0.01, diff                               # final metrics are not within 1 percent either
    ctl = rec["control_without_the_network"]["median_and_q3_iterations"]
    assert ctl["random_nfix3"][0] <= ctl["random_nfix12"][0] / 1.4       # the early phase fix alone gives the gain ...
    assert ctl["model_nfix3"][0] >= ctl["random_nfix3"][0]               # ... and the network adds nothing to it
    assert not (MODELS / "warmstart.onnx").exists() and not (MODELS / "warmstart.json").exists()


@pytest.mark.skipif(not RELEASED, reason="warmstart-model is not released: the random start answers")
def test_released_model_meets_the_criterion():
    out = REPO_ROOT / "data" / "derived" / "models"
    e = json.loads((out / "metrics.json").read_text(encoding="utf-8"))["slots"]["warmstart-model"]
    it = e["iterations_to_1pct"]
    assert it["model"]["median"] * 2 <= it["random"]["median"], it
    assert (MODELS / "warmstart.onnx").stat().st_size <= 1024 * 1024


def test_the_module_answers_with_the_random_start_while_unreleased(tmp_path):
    import numpy as np

    from pipeline.model.holo.core.geometry import Setup, focal_bin_m
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.traps import square_grid
    from pipeline.model.holo.core.types import Budget, Target
    from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs as m07
    from pipeline.model.holo.methods.learned import b3_warm_start
    setup = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)
    t = Target.from_traps(square_grid(4, 4, 8 * focal_bin_m(setup) * 1e6))
    a = b3_warm_start.run(setup, t, budget=Budget(5), rng=Rng(2), models_dir=tmp_path)
    b = m07.run(setup, t, budget=Budget(5), rng=Rng(2), form="point")
    assert a.meta["provenance"] == "baseline"
    np.testing.assert_array_equal(a.phi, b.phi)
