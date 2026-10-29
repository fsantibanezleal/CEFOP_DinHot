"""M17 (SDD ladder row M17), multi-plane form: on held-out volumes, accuracy above the baseline (M19, volumetric 3D GS) at the same
wall-clock budget. M17 is the hybrid: the released network's phase starts M19, which refines it in what is left of the budget.

The module tests (planes from traps, geometry errors, the baseline answering while unreleased) run everywhere with onnxruntime or not.
The acceptance tests need the released cgh-net graph in ``models/``, onnxruntime and the held-out file (``$DINHOT_LEARNED_DIR``) and
skip otherwise.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pytest

from pipeline.io.contract import REPO_ROOT
from pipeline.io.model_card import is_valid_slot
from pipeline.model.holo.core.geometry import Setup, focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.learned import convert, generators
from pipeline.model.holo.methods.baseline import m19_multiplane
from pipeline.model.holo.methods.learned import m17_cgh_net

SETUP = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
MODELS = REPO_ROOT / "models"
_d = os.environ.get("DINHOT_LEARNED_DIR")
HELD = (Path(_d) if _d else Path("absent")) / "cgh-vol-heldout.npz"
HAS_ORT = importlib.util.find_spec("onnxruntime") is not None
RELEASED = is_valid_slot(MODELS, "cgh-net") and HAS_ORT   # the released graph can answer only with onnxruntime


def _target(trap_rows):
    b, zr = focal_bin_m(SETUP), convert.rayleigh_range_m(SETUP)
    return Target.from_traps(TrapSet(Trap(i, r[0] * b, r[1] * b, r[2] * 8.0 * zr) for i, r in enumerate(trap_rows)))


def test_planes_from_traps_renders_three_unit_energy_planes():
    _a, rows = generators.sample_volume(np.random.default_rng(4), "random")
    amps = m17_cgh_net.planes_from_traps(SETUP, _target(rows).traps)
    ref, _ = generators.sample_volume(np.random.default_rng(4), "random")
    assert amps.shape == (1, 3, 128, 128) and amps.dtype == np.float32
    np.testing.assert_allclose(amps[0], ref, atol=1e-6)
    np.testing.assert_allclose((amps[0].astype(np.float64) ** 2).sum((1, 2)), 1.0, atol=1e-5)


def test_geometry_and_target_errors_name_the_requirement():
    rows = generators.sample_volume(np.random.default_rng(1), "random")[1]
    big = Setup(**{**SETUP.__dict__, "n_pix": 256, "pad": 2})
    with pytest.raises(ValueError, match="128 x 128 SLM with padding 1"):
        m17_cgh_net.run(big, _target(rows), budget=Budget(1), rng=Rng(1))
    off = rows.copy()
    off[0, 2] = 0.5
    with pytest.raises(ValueError, match="planes z = "):
        m17_cgh_net.run(SETUP, _target(off), budget=Budget(1), rng=Rng(1))
    far = rows.copy()
    far[0, 0] = 70
    with pytest.raises(ValueError, match="within 60 bins"):
        m17_cgh_net.run(SETUP, _target(far), budget=Budget(1), rng=Rng(1))
    with pytest.raises(ValueError, match="target kinds"):
        m17_cgh_net.run(SETUP, Target.from_field(np.ones((128, 128)), np.ones((128, 128), bool)), budget=Budget(1), rng=Rng(1))


def test_the_baseline_answers_while_unreleased(tmp_path):
    rows = generators.sample_volume(np.random.default_rng(2), "lattice")[1]
    t = _target(rows)
    r = m17_cgh_net.run(SETUP, t, budget=Budget(1), rng=Rng(1), models_dir=tmp_path)
    ref = m19_multiplane.run(SETUP, t, budget=Budget(30), rng=Rng(1), dz_m=m17_cgh_net.plane_dz_m(SETUP))
    assert r.meta["provenance"] == "baseline"
    np.testing.assert_array_equal(r.phi, ref.phi)


def test_committed_metrics_meet_the_criterion():
    if not is_valid_slot(MODELS, "cgh-net"):
        pytest.skip("cgh-net is not released: the M19 baseline answers")
    doc = json.loads((REPO_ROOT / "data" / "derived" / "models" / "metrics.json").read_text(encoding="utf-8"))
    e = doc["slots"]["cgh-net"]
    assert e["held_out_n"] >= 150
    assert e["accuracy_vs_gs"]["median"] > 1.0, e["accuracy_vs_gs"]


@pytest.mark.skipif(not RELEASED, reason="cgh-net is not released")
def test_the_hybrid_runs_the_network_then_m19_inside_the_budget():
    rows = generators.sample_volume(np.random.default_rng(3), "random")[1]
    t = _target(rows)
    r = m17_cgh_net.run(SETUP, t, budget=Budget(10**6, 0.6), rng=Rng(1))
    assert r.meta["provenance"] == "real" and r.meta["refine_iterations"] >= 1 and r.meta["network_s"] > 0
    alone = m17_cgh_net.run(SETUP, t, budget=Budget(1), rng=Rng(1), refine=False)
    assert alone.meta["refine_iterations"] == 0 and len(alone.history) == 1


@pytest.mark.skipif(not (RELEASED and HELD.is_file()), reason="needs the released graph and the held-out file")
def test_sampled_held_out_volumes_beat_m19_at_the_same_wall_clock():
    import time

    from pipeline.model.holo.learned import evaluation, heldout
    amps, trap_sets, _k = heldout.load_cgh_vol(HELD)
    idx = list(range(0, len(amps), 8))
    dz = m17_cgh_net.plane_dz_m(SETUP)
    ts = []
    for i in idx:
        t0 = time.perf_counter()
        m19_multiplane.run(SETUP, evaluation.volume_target(trap_sets[i]), budget=Budget(30), rng=Rng(1), dz_m=dz)
        ts.append(time.perf_counter() - t0)
    budget_s = float(np.median(ts))
    ratios = []
    for i in idx:
        t = evaluation.volume_target(trap_sets[i])
        h = m17_cgh_net.run(SETUP, t, budget=Budget(10**6, budget_s), rng=Rng(1))
        g = m19_multiplane.run(SETUP, t, budget=Budget(10**6, budget_s), rng=Rng(1), dz_m=dz)
        ratios.append(evaluation.plane_accuracy(amps[i], h.phi) / evaluation.plane_accuracy(amps[i], g.phi))
    assert float(np.median(ratios)) > 1.0, np.round(np.percentile(ratios, [25, 50, 75]), 4)


def test_a_released_model_without_onnxruntime_refuses(monkeypatch):
    """A released slot with no onnxruntime is a broken environment: the run raises instead of answering with the baseline."""
    if not is_valid_slot(MODELS, "cgh-net"):
        pytest.skip("no released cgh-net graph in models/")
    import builtins
    from pipeline.model.holo.methods.learned import _slot
    real_import = builtins.__import__
    def no_ort(name, *a, **k):
        if name == "onnxruntime" or name.startswith("onnxruntime."):
            raise ImportError("planted: onnxruntime absent")
        return real_import(name, *a, **k)
    monkeypatch.setattr(_slot, "_CACHE", {})
    monkeypatch.setattr(builtins, "__import__", no_ort)
    rows = generators.sample_volume(np.random.default_rng(2), "lattice")[1]
    with pytest.raises(RuntimeError, match="onnxruntime is not installed"):
        m17_cgh_net.run(SETUP, _target(rows), budget=Budget(1), rng=Rng(1))
