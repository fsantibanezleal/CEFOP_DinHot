"""M17 acceptance (SDD ladder row M17): on held-out targets, accuracy above GS at the same wall-clock budget.

M17 is the hybrid: the released network's phase starts GS (M04), which refines it in what is left of the wall-clock budget. The
budget is the median time of the catalog baseline (GS at 30 iterations). Needs the released cgh-net graph in ``models/``,
onnxruntime and the held-out file (``$DINHOT_LEARNED_DIR``); skipped where any is absent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

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

MODELS = REPO_ROOT / "models"
_d = os.environ.get("DINHOT_LEARNED_DIR")
HELD = (Path(_d) if _d else Path("absent")) / "cgh-heldout.npz"

pytestmark = pytest.mark.skipif(not is_valid_slot(MODELS, "cgh-net"), reason="cgh-net is not released: the GS baseline answers")


def test_committed_metrics_meet_the_criterion():
    doc = json.loads((REPO_ROOT / "data" / "derived" / "models" / "metrics.json").read_text(encoding="utf-8"))
    e = doc["slots"]["cgh-net"]
    assert e["baseline"] == "M04" and e["held_out_n"] >= 200
    assert e["accuracy_vs_gs"]["median"] > 1.0, e["accuracy_vs_gs"]


def test_the_hybrid_runs_the_network_then_gs_inside_the_budget():
    from pipeline.model.holo.learned import generators
    a = generators.sample_target(np.random.default_rng(1), "ring")
    t = evaluation._target(a)
    r = m17_cgh_net.run(evaluation.SETUP128, t, budget=Budget(10**6, 0.15), rng=Rng(1))
    assert r.meta["provenance"] == "real" and r.meta["refine_iterations"] >= 1 and r.meta["network_s"] > 0
    alone = m17_cgh_net.run(evaluation.SETUP128, t, budget=Budget(1), rng=Rng(1), refine=False)
    assert alone.meta["refine_iterations"] == 0 and len(alone.history) == 1


@pytest.mark.skipif(not HELD.is_file(), reason="the held-out file lives in the data root of the training device")
def test_sampled_held_out_targets_beat_gs_at_the_same_wall_clock():
    gen, _kinds, bench, _names = heldout.load_cgh(HELD)
    targets = list(gen[::10]) + list(bench)
    budget_s = float(np.median([_t(m04_gs.run, evaluation.SETUP128, evaluation._target(a), Budget(30)) for a in targets]))
    ratios = []
    for a in targets:
        t = evaluation._target(a)
        hyb = m17_cgh_net.run(evaluation.SETUP128, t, budget=Budget(10**6, budget_s), rng=Rng(1))
        gs = m04_gs.run(evaluation.SETUP128, t, budget=Budget(10**6, budget_s), rng=Rng(1))
        ratios.append(evaluation.accuracy(a, hyb.phi) / evaluation.accuracy(a, gs.phi))
    assert float(np.median(ratios)) > 1.0, np.round(np.percentile(ratios, [25, 50, 75]), 4)


def _t(fn, setup, target, budget):
    import time
    t0 = time.perf_counter()
    fn(setup, target, budget=budget, rng=Rng(1))
    return time.perf_counter() - t0
