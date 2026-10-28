"""M17 acceptance (SDD ladder row M17): on held-out targets, accuracy above GS at the same wall-clock budget.

Needs the released cgh-net graph in ``models/``, onnxruntime and the held-out file of the data root (written before training);
skipped where any is absent (the baseline answers then, readiness says training). The numbers of the committed
``data/derived/models/metrics.json`` are checked against the criterion, and a re-run on a sample of the held-out set is checked
against the same criterion (the full run is ``python -m pipeline.stages.evaluate``).
"""
from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("onnxruntime")

from pipeline.io.contract import REPO_ROOT  # noqa: E402
from pipeline.io.model_card import is_valid_slot  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget  # noqa: E402
from pipeline.model.holo.learned import evaluation, heldout  # noqa: E402
from pipeline.model.holo.methods.baseline import m04_gs  # noqa: E402
from pipeline.model.holo.methods.learned import m17_cgh_net  # noqa: E402


def _held(name):
    import os
    from pathlib import Path
    d = os.environ.get("DINHOT_LEARNED_DIR")
    return Path(d) / name if d else Path("absent") / name


MODELS = REPO_ROOT / "models"
HELD = _held("cgh-heldout.npz")

pytestmark = pytest.mark.skipif(not is_valid_slot(MODELS, "cgh-net"), reason="cgh-net is not released: the GS baseline answers")


def test_committed_metrics_meet_the_criterion():
    doc = json.loads((REPO_ROOT / "data" / "derived" / "models" / "metrics.json").read_text(encoding="utf-8"))
    e = doc["slots"]["cgh-net"]
    assert e["baseline"] == "M04" and e["held_out_n"] >= 200
    assert e["accuracy_vs_gs"]["median"] > 1.0, e["accuracy_vs_gs"]


@pytest.mark.skipif(not HELD.is_file(), reason="the held-out file lives in the data root of the training device")
def test_sampled_held_out_targets_beat_gs_at_the_same_wall_clock():
    gen, _kinds, bench, _names = heldout.load_cgh(HELD)
    targets = list(gen[::10]) + list(bench)
    t_net, ratios = [], []
    for a in targets:
        r = m17_cgh_net.run(evaluation.SETUP128, evaluation._target(a), budget=Budget(1), rng=Rng(1))
        assert r.meta["provenance"] == "real"
        t_net.append(r.history[0]["time_s"])
    budget_s = float(np.median(t_net))
    for a in targets:
        t = evaluation._target(a)
        net = m17_cgh_net.run(evaluation.SETUP128, t, budget=Budget(1), rng=Rng(1))
        gs = m04_gs.run(evaluation.SETUP128, t, budget=Budget(10**6, budget_s), rng=Rng(1))
        ratios.append(evaluation.accuracy(a, net.phi) / evaluation.accuracy(a, gs.phi))
    assert float(np.median(ratios)) > 1.0, np.round(np.percentile(ratios, [25, 50, 75]), 4)
