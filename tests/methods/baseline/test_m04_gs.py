"""M04: Gerchberg-Saxton, point-trap and FFT forms (SDD ladder; Di Leonardo 2007 Table 1: GS e/u = 0.94/0.60 at 30 iterations)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m04_gs as m

SEEDS = (1, 2, 3)


def _wrapped_diff(a, b):
    return np.abs(np.angle(np.exp(1j * (a - b))))


def test_two_forms_agree_on_a_2d_on_bin_grid(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(8), rng=Rng(5), form="point")
    b = m.run(setup256, t, budget=Budget(8), rng=Rng(5), form="fft")
    assert _wrapped_diff(a.phi, b.phi).max() < 1e-6
    for ha, hb in zip(a.history, b.history):
        assert abs(ha["efficiency"] - hb["efficiency"]) < 1e-9
        assert abs(ha["uniformity"] - hb["uniformity"]) < 1e-9


def test_acceptance_10x10_30_iterations_flat_beam(setup256_flat, grid10, evaluate):
    """SDD: efficiency at least 0.9 with uniformity near 0.6 (published 0.94 and 0.60), on the beam of the published task."""
    vals = []
    for s in SEEDS:
        r = m.run(setup256_flat, Target.from_traps(grid10), budget=Budget(30), rng=Rng(s))
        assert len(r.history) == 30
        vals.append(evaluate(r.phi, grid10, setup256_flat))
    e, u = np.array(vals)[:, 0], np.array(vals)[:, 1]
    assert np.all(e >= 0.9), e
    assert np.all((u > 0.4) & (u < 0.8)), u


def test_acceptance_10x10_30_iterations_gaussian_beam(setup256, ceiling, grid10, evaluate):
    """Default Gaussian beam: no method exceeds the ceiling (mean A)^2 = 0.87 in this metric, so e is compared to it."""
    vals = np.array([evaluate(m.run(setup256, Target.from_traps(grid10), budget=Budget(30), rng=Rng(s)).phi, grid10)
                     for s in SEEDS])
    assert np.all(vals[:, 0] >= 0.9 * ceiling), (vals[:, 0], ceiling)
    assert np.all((vals[:, 1] > 0.4) & (vals[:, 1] < 0.8)), vals[:, 1]


def test_history_matches_evaluation(setup256, grid10, evaluate):
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(10), rng=Rng(2))
    e, u, s = evaluate(r.phi, grid10)
    h = r.history[-1]
    assert abs(h["efficiency"] - e) < 1e-9 and abs(h["uniformity"] - u) < 1e-9 and abs(h["rel_std"] - s) < 1e-7
    assert [x["iteration"] for x in r.history] == list(range(1, 11))
    assert r.history[-1]["efficiency"] > r.history[0]["efficiency"]


def test_time_budget_stops_early(setup256, grid10):
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(10000, time_s=0.5), rng=Rng(2))
    assert 1 <= len(r.history) < 10000


def test_deterministic_and_init(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(5), rng=Rng(9)).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(5), rng=Rng(9)).phi)
    r0 = m.run(setup256, t, budget=Budget(1), rng=Rng(9))
    r1 = m.run(setup256, t, budget=Budget(1), rng=Rng(123), init=r0.phi)
    r2 = m.run(setup256, t, budget=Budget(1), rng=Rng(456), init=r0.phi)
    assert np.array_equal(r1.phi, r2.phi)          # init given: the rng is not used


def test_field_target_gs_on_shaped_region(setup256):
    n = setup256.n_fft
    yy, xx = np.indices((n, n))
    mask = (yy - n // 2) ** 2 + (xx - n // 2) ** 2 < 14**2
    t = Target.from_field(mask.astype(float), mask)
    r = m.run(setup256, t, budget=Budget(10), rng=Rng(1), form="fft")
    assert r.fields.shape == (n, n) and r.history[-1]["efficiency"] > 0.8


def test_point_form_rejects_field_target_and_bad_form(setup256, grid10):
    n = setup256.n_fft
    t = Target.from_field(np.ones((n, n)), np.ones((n, n), bool))
    with pytest.raises(ValueError, match="fft"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), form="point")
    with pytest.raises(ValueError, match="form"):
        m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(1), form="x")
