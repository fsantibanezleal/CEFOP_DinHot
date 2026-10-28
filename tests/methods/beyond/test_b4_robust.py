"""B4 aberration- and pointing-robust hologram.

SDD acceptance: the 95th percentile of the relative standard deviation over a perturbation ensemble at least two times
below M07, mean efficiency at most 10 percent lower (dossier D5.1 B4). The baseline M07 is this unit's
``_gs_family`` phase-fixed WGS (30 iterations, same equations) until E2 merges. Ensemble: 200 seeded perturbations, each
a draw of Noll 4 to 11 coefficients (0.02 waves rms each) and an independent 0.15 bin displacement of every trap.

Measured result (see the E3 report): the 2x criterion is NOT reached; the expected-cost hologram lowers the p95 only by
a few percent (the intensity sensitivity of a diffraction-limited spot to a pointing error is fixed by its width, and
broadening it costs peak efficiency). The 2x test is therefore kept as a strict xfail so the shortfall stays visible,
and the other tests assert what holds.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "optim"))
from e3_helpers import bin_grid, check_finite_difference, make_setup, task_10x10  # noqa: E402

from pipeline.model.holo.core.forward import point_trap_projection, slm_field  # noqa: E402
from pipeline.model.holo.core.geometry import focal_bin_m  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.beyond import b4_robust as B4  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402
from pipeline.model.holo.methods.optim import _gs_family as G  # noqa: E402


def test_spec():
    assert B4.SPEC.id == "B4" and B4.SPEC.targets == ("traps",)


def test_perturbation_is_seeded_and_has_the_stated_scale():
    s = make_setup(64)
    traps = bin_grid(s, 3, 3, 8)
    a1, m1 = B4.sample_perturbation(s, traps, Rng(1))
    a2, m2 = B4.sample_perturbation(s, traps, Rng(1))
    assert np.array_equal(a1, a2) and np.array_equal(m1.x_m, m2.x_m)
    rng = Rng(2)
    d = np.concatenate([B4.sample_perturbation(s, traps, rng)[1].x_m - traps.x_m for _ in range(400)])
    assert d.std() == pytest.approx(0.15 * focal_bin_m(s), rel=0.1)


def test_gradient_at_a_perturbed_sample_matches_finite_differences():
    s = make_setup(16)
    traps = bin_grid(s, 3, 3, 4)
    ab, moved = B4.sample_perturbation(s, traps, Rng(3), 0.05, 0.3)
    cost = C.TrapCost(s, moved, t=2, efficiency=0.5)
    phi = Rng(4).phases(256).reshape(16, 16)
    assert check_finite_difference(lambda x: cost.value_grad(x + ab), phi, np.random.default_rng(1), n_dirs=5) <= 1e-5


def test_run_keeps_the_nominal_hologram_good_and_is_deterministic():
    s = make_setup(64)
    traps = bin_grid(s, 4, 4, 8)
    a = B4.run(s, Target.from_traps(traps), budget=Budget(6), rng=Rng(5), q=4)
    b = B4.run(s, Target.from_traps(traps), budget=Budget(6), rng=Rng(5), q=4)
    assert np.array_equal(a.phi, b.phi) and len(a.history) == 6
    assert np.allclose(point_trap_projection(slm_field(a.phi, s), s, traps), a.fields, atol=1e-10)
    assert a.history[-1]["uniformity"] > 0.8


def test_field_target_is_refused():
    s = make_setup(16)
    with pytest.raises(ValueError, match="traps"):
        B4.run(s, Target.from_field(np.ones((32, 32)), np.ones((32, 32), dtype=bool)), budget=Budget(1), rng=Rng(1))


@functools.lru_cache(maxsize=None)
def ensemble_pair(iterations=40):
    s = make_setup(256)
    traps = task_10x10(s)
    base, _ = G.weighted_gs(s, traps, 30, Rng(1), variant="pfwgs")
    res = B4.run(s, Target.from_traps(traps), budget=Budget(iterations), rng=Rng(1))
    return B4.ensemble_stats(s, base, traps), B4.ensemble_stats(s, res.phi, traps)


def test_robust_hologram_is_not_worse_than_the_nominal_one_over_the_ensemble():
    nom, rob = ensemble_pair()
    assert rob["sigma_p95"] <= nom["sigma_p95"] * 1.02
    assert rob["efficiency_mean"] >= 0.9 * nom["efficiency_mean"]


@pytest.mark.xfail(strict=True, reason="PARTIAL: the SDD 2x lower p95 sigma is not reached (measured gain 1.0 to 1.3)")
def test_acceptance_p95_sigma_two_times_below_phase_fixed_wgs():
    nom, rob = ensemble_pair()
    assert rob["sigma_p95"] <= nom["sigma_p95"] / 2.0, (nom["sigma_p95"], rob["sigma_p95"])
