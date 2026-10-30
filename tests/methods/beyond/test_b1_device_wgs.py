"""B1 device-aware weighted GS.

Acceptance (SDD): on the crosstalk device, relative standard deviation at least two times below M07 (phase-fixed WGS),
efficiency at most 10 percent lower. M07 is unit E2's module; until the merge the baseline is this unit's
``_gs_family.weighted_gs(variant="pfwgs")`` (same equations, dossier D1.3), run on the ideal model as M07 would be and
scored on the device. The baseline is given 30 and 100 iterations and the better of the two is the reference (more
iterations cannot remove a crosstalk it does not model). Seeds: 1 (the run is about 50 s; the benchmark runs 20).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "optim"))
from e3_helpers import bin_grid, make_setup, task_10x10  # noqa: E402

from pipeline.model.holo.core.device import Device, device_focal_field  # noqa: E402
from pipeline.model.holo.core.forward import trap_fields_from_fft  # noqa: E402
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.beyond import b1_device_wgs as B1  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402

DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)


def on_device(phi, setup, traps, device=DEVICE):
    v = trap_fields_from_fft(device_focal_field(phi, setup, device, None), setup, traps)
    return efficiency(trap_intensities(v)), rel_std(trap_intensities(v, traps.weight))


def test_spec():
    assert B1.SPEC.id == "B1" and B1.SPEC.targets == ("traps",)


def test_field_target_is_refused():
    s = make_setup(16)
    with pytest.raises(ValueError, match="traps"):
        B1.run(s, Target.from_field(np.ones((32, 32)), np.ones((32, 32), dtype=bool)), budget=Budget(1), rng=Rng(1))


def test_small_grid_flattens_traps_through_quantizer_and_crosstalk():
    s = make_setup(64)
    traps = bin_grid(s, 4, 4, 8)
    dev = Device(crosstalk=(1.24, 1.8), bit_depth=5)
    base, _ = G.weighted_gs(s, traps, 30, Rng(2), variant="pfwgs")
    res = B1.run(s, Target.from_traps(traps), device=dev, budget=Budget(4), rng=Rng(2))
    assert on_device(res.phi, s, traps, dev)[1] < on_device(base, s, traps, dev)[1]
    assert np.allclose(res.fields, trap_fields_from_fft(device_focal_field(res.phi, s, dev, None), s, traps),
                       atol=1e-9)
    assert all(w > 0 and np.isfinite(w) for w in res.meta["weights"])
    assert len(res.history) == 4


def test_without_a_device_the_loop_uses_the_ideal_model():
    s = make_setup(64)
    traps = bin_grid(s, 3, 3, 8)
    res = B1.run(s, Target.from_traps(traps), budget=Budget(3), rng=Rng(3))
    assert res.history[-1]["rel_std"] < 5.0 and not res.meta["device_aware"]


def test_deterministic_for_a_seed():
    s = make_setup(32)
    traps = bin_grid(s, 2, 2, 16)
    a = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(2), rng=Rng(7))
    b = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(2), rng=Rng(7))
    assert np.array_equal(a.phi, b.phi)


def test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device():
    s = make_setup(256)
    traps = task_10x10(s)
    base = {n: on_device(G.weighted_gs(s, traps, n, Rng(1), variant="pfwgs")[0], s, traps) for n in (30, 100)}
    e_ref = max(e for e, _ in base.values())
    sig_ref = min(sg for _, sg in base.values())
    res = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(B1.DEFAULT_OUTER), rng=Rng(1))
    e, sig = on_device(res.phi, s, traps)
    assert sig <= sig_ref / 2.0, (sig, base)
    assert e >= 0.9 * e_ref, (e, base)


def test_adversarial_a_run_that_winds_up_returns_its_best_admissible_iterate():
    """Must refute: B1 returning a runaway. On the benchmark's square lattice on the C08 device, seed 1 winds up (its own
    history shows the loss rising and the efficiency falling to a few percent, measured 2026-10-30); the safeguard returns the
    best iterate that keeps EFFICIENCY_FLOOR of the warm start's efficiency, so the result is never worse than the start."""
    from pipeline.benchmark import protocol
    from pipeline.stages import infer

    rec = protocol._record("G1", True, 1, False)
    rec = {**rec, "device": {**rec["device"], "flicker_rad": 0.0}}
    out = infer.run_method(rec, "B1", budget=Budget(10))
    effs = [h["efficiency"] for h in out.history]
    assert min(effs) < 0.25 * out.meta["start_efficiency"]           # the run did wind up: the planted condition holds
    assert out.meta["efficiency_floor"] == pytest.approx(B1.EFFICIENCY_FLOOR * out.meta["start_efficiency"])
    assert out.score["efficiency"] >= 0.95 * out.meta["efficiency_floor"]
    assert out.score["rel_std_pct"] <= 1.05 * out.meta["start_rel_std"]
    k = out.meta["best_iteration"]
    assert k == 0 or out.history[k - 1]["efficiency"] >= out.meta["efficiency_floor"]


def test_a_converging_run_returns_an_iterate_of_its_tail():
    s = make_setup(256)
    traps = task_10x10(s)
    res = B1.run(s, Target.from_traps(traps), device=DEVICE, budget=Budget(8), rng=Rng(1))
    assert res.meta["best_iteration"] >= 6 and res.meta["efficiency_floor"] > 0
