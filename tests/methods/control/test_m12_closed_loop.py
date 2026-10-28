"""M12: closed-loop weighted GS on an emulated camera (SDD ladder; Nogrette et al. 2014: 19 percent rms to 1.4 percent in 20
iterations at gain 0.7; Kim et al. 2019: 22 percent to 1.59 percent in three phase-fixed steps)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.camera import EmulatedCamera
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.control import m12_closed_loop as m

SEEDS = (1, 2)


@pytest.mark.parametrize("seed", SEEDS)
def test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations(setup256, grid10, seed):
    cam = EmulatedCamera(seed=seed, gain_rms=0.19, noise_rms=0.0, blur_bins=0.0, rolloff=False)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(20), rng=Rng(seed), camera=cam, gain=0.7)
    assert 14.0 <= r.meta["open_loop_rel_std"] <= 25.0, r.meta["open_loop_rel_std"]     # the 19 percent rms start
    assert len(r.history) == 20
    assert r.history[-1]["rel_std"] <= 2.1, [round(h["rel_std"], 2) for h in r.history]
    assert r.history[-1]["rel_std"] < r.meta["open_loop_rel_std"] / 8


def test_nogrette_from_plain_gs_start_removes_algorithm_and_camera_error(setup256, grid10):
    cam = EmulatedCamera(seed=3, gain_rms=0.19, rolloff=False)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(20), rng=Rng(3), camera=cam, gain=0.7, start="gs")
    assert r.meta["open_loop_rel_std"] > 20.0
    assert r.history[-1]["rel_std"] <= 2.1


@pytest.mark.parametrize("seed", SEEDS)
def test_kim_square_root_update_with_phase_fixing_three_steps(setup256, grid10, seed):
    """Kim: from 22 percent, three phase-fixed steps give 1.59 +- 0.18 percent; asserted: at most 1.8 percent."""
    cam = EmulatedCamera(seed=seed, gain_rms=0.22, rolloff=False)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(3), rng=Rng(seed), camera=cam, variant="kim")
    assert r.meta["open_loop_rel_std"] > 15.0
    assert r.history[-1]["rel_std"] <= 1.8, [round(h["rel_std"], 2) for h in r.history]


def test_gain_one_converges_faster_than_gain_point_three(setup256, grid10):
    cam = EmulatedCamera(seed=4, gain_rms=0.19, rolloff=False)
    slow = m.run(setup256, Target.from_traps(grid10), budget=Budget(4), rng=Rng(4), camera=cam, gain=0.3)
    fast = m.run(setup256, Target.from_traps(grid10), budget=Budget(4), rng=Rng(4), camera=cam, gain=1.0)
    assert fast.history[-1]["rel_std"] < slow.history[-1]["rel_std"]


def test_noisy_blurred_camera_still_converges(setup256, grid10):
    """Noise 5e-5 (about 0.6 percent of a trap intensity), blur and roll-off: the loop reaches a few percent."""
    cam = EmulatedCamera(seed=5, gain_rms=0.19, noise_rms=5e-5, blur_bins=0.7, rolloff=True)
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(15), rng=Rng(5), camera=cam, gain=0.7)
    assert r.history[-1]["rel_std"] < 4.0, [round(h["rel_std"], 2) for h in r.history]


def test_default_camera_is_seeded_from_the_rng_and_deterministic(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(3), rng=Rng(7))
    b = m.run(setup256, t, budget=Budget(3), rng=Rng(7))
    assert np.array_equal(a.phi, b.phi)
    assert not np.array_equal(a.phi, m.run(setup256, t, budget=Budget(3), rng=Rng(8)).phi)
    assert set(a.history[0]) >= {"iteration", "efficiency", "uniformity", "rel_std", "time_s", "rel_std_true"}


def test_validation(setup256, grid10):
    t = Target.from_traps(grid10)
    with pytest.raises(ValueError, match="variant"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), variant="x")
    with pytest.raises(ValueError, match="gain"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), gain=0.0)
    off = TrapSet([Trap(0, 3.3e-6, 0.0)])
    with pytest.raises(ValueError, match="bins"):
        m.run(setup256, Target.from_traps(off), budget=Budget(1), rng=Rng(1))
    n = setup256.n_fft
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(np.ones((n, n)), np.ones((n, n), bool)), budget=Budget(1), rng=Rng(1))
