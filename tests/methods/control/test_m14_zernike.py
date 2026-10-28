"""M14: Zernike correction and sensorless modal recovery (SDD ladder: recovers an injected set of Noll modes 4 to 11 within
5 percent of their amplitude)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.camera import EmulatedCamera
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.control import m14_zernike as m

SEEDS = (1, 2, 3)


def injected_set(seed):
    """Noll 4 to 11 with random signs and amplitudes 0.06 to 0.12 waves (rms about 0.26 waves: Strehl about 0.07 uncorrected)."""
    rg = Rng(1000 + seed)
    c = np.zeros(11)
    for j in range(4, 12):
        c[j - 1] = (0.06 + 0.06 * rg.uniform()) * (1.0 if rg.uniform() < 0.5 else -1.0)
    return c


def test_known_aberration_is_subtracted_exactly(setup256, grid10):
    inj = injected_set(1)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(1), mode="correct", injected=inj, known=inj)
    assert abs(r.history[-1]["efficiency"] - r.meta["base_efficiency"]) < 1e-9
    assert r.meta["uncorrected_efficiency"] < 0.5 * r.meta["base_efficiency"]
    assert len(r.history) == 1


def test_partial_knowledge_corrects_partially(setup256, grid10):
    inj = injected_set(1)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(1), mode="correct", injected=inj,
              known=0.5 * inj)
    assert r.meta["uncorrected_efficiency"] < r.history[-1]["efficiency"] < r.meta["base_efficiency"]


@pytest.mark.parametrize("seed", SEEDS)
def test_modal_search_recovers_noll_4_to_11_within_5_percent(setup256, grid10, seed):
    inj = injected_set(seed)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(6), rng=Rng(seed), mode="recover", injected=inj)
    est = r.meta["coefficients"]
    rel = np.abs(est[3:11] - inj[3:11]) / np.abs(inj[3:11])
    assert np.all(rel <= 0.05), (seed, np.round(rel, 3))
    assert np.all(est[:3] == 0) and np.all(est[11:] == 0)
    assert r.history[-1]["efficiency"] >= 0.98 * r.meta["base_efficiency"]
    assert r.history[-1]["efficiency"] >= r.history[0]["efficiency"]


def test_recovery_with_camera_noise(setup256, grid10):
    inj = injected_set(2)
    cam = EmulatedCamera(seed=9, gain_rms=0.05, noise_rms=1e-4, rolloff=False)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(6), rng=Rng(2), injected=inj, camera=cam)
    err = r.meta["coefficients"][3:11] - inj[3:11]
    assert np.sqrt(np.sum(err**2)) <= 0.10 * np.sqrt(np.sum(inj[3:11] ** 2))


def test_deterministic_and_validation(setup256, grid10):
    t = Target.from_traps(grid10)
    inj = injected_set(1)
    a = m.run(setup256, t, budget=Budget(2), rng=Rng(4), injected=inj).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(2), rng=Rng(4), injected=inj).phi)
    with pytest.raises(ValueError, match="known"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), mode="correct", injected=inj)
    with pytest.raises(ValueError, match="mode"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), mode="x")
    with pytest.raises(ValueError, match="modes"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), modes=(0, 4))
    with pytest.raises(ValueError, match="21"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), injected=np.ones(30))
    n = setup256.n_fft
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(np.ones((n, n)), np.ones((n, n), bool)), budget=Budget(1), rng=Rng(1))
