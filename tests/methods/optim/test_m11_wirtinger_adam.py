"""M11 Wirtinger gradient descent with Adam (Chakravarthula et al. 2019).

Acceptance: lower trap-intensity error than M04 (Gerchberg-Saxton) at equal iterations on the 10x10 task. The trap
intensity error is the relative standard deviation of I_m / w_m in percent. Seeds: 3 (benchmark: 20).
"""
from __future__ import annotations

import numpy as np
from e3_helpers import check_finite_difference, make_setup, task_10x10, trap_stats

from pipeline.model.holo.core.forward import point_trap_fields
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.optim import _common as C
from pipeline.model.holo.methods.optim import _gs_family as G
from pipeline.model.holo.methods.optim import m11_wirtinger_adam as M11


def test_spec_and_documented_defaults():
    assert M11.SPEC.id == "M11" and set(M11.SPEC.targets) == {"traps", "field"}
    assert M11.PAPER_LR == 0.001          # Chakravarthula 2019 for the learned-loss case
    assert M11.DEFAULT_LR > 0             # tuned for the quadratic loss, see the docstring table


def test_wirtinger_gradient_matches_finite_differences_with_axial_and_vortex_traps():
    s = make_setup(16)
    traps = TrapSet([Trap(0, 3e-5, 1e-5, 0.0), Trap(1, -2e-5, 4e-5, 2e-5, weight=2.0),
                     Trap(2, 1e-5, -3e-5, 0.0, charge=1), Trap(3, -4e-5, -1e-5, -1e-5)])
    cost = C.TrapCost(s, traps, t=2, efficiency=0.7)
    phi = Rng(1).phases(256).reshape(16, 16)
    assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(3), n_dirs=6) <= 1e-5


def test_adam_decreases_the_loss_and_records_history():
    s = make_setup(64)
    traps = task_10x10(make_setup(256))
    # a 6x6 sub-lattice that fits the 64 pixel grid
    from pipeline.model.holo.core.geometry import focal_bin_m
    from pipeline.model.holo.core.traps import square_grid
    traps = square_grid(4, 4, 8 * focal_bin_m(s) * 1e6)
    res = M11.run(s, Target.from_traps(traps), budget=Budget(40), rng=Rng(1))
    assert len(res.history) == 40 and res.history[-1]["loss"] < res.history[0]["loss"]
    assert np.allclose(point_trap_fields(res.phi, s, traps), res.fields, atol=1e-10)


def test_field_target_runs_and_reduces_the_loss():
    from e3_helpers import disc_target
    s = make_setup(32)
    amp, mask = disc_target(s, 14.0, guard=3.0)
    res = M11.run(s, Target.from_field(amp, mask), budget=Budget(50), rng=Rng(1))
    assert res.history[-1]["loss"] < res.history[0]["loss"]


def test_deterministic_for_a_seed():
    s = make_setup(32)
    from pipeline.model.holo.core.traps import snap_to_bins, square_grid
    traps = snap_to_bins(s, square_grid(3, 3, 8 * 8.32 * 2))
    a = M11.run(s, Target.from_traps(traps), budget=Budget(5), rng=Rng(7))
    b = M11.run(s, Target.from_traps(traps), budget=Budget(5), rng=Rng(7))
    assert np.array_equal(a.phi, b.phi)


def test_acceptance_lower_trap_intensity_error_than_gs_at_equal_iterations():
    s = make_setup(256)
    traps = task_10x10(s)
    iters = 30
    adam, gs = [], []
    for seed in (1, 2, 3):
        res = M11.run(s, Target.from_traps(traps), budget=Budget(iters), rng=Rng(seed))
        adam.append(trap_stats(res.phi, s, traps)[2])
        phi, _ = G.weighted_gs(s, traps, iters, Rng(seed), variant="gs")
        gs.append(trap_stats(phi, s, traps)[2])
    assert float(np.median(adam)) < float(np.median(gs)), (adam, gs)
    assert all(a < g for a, g in zip(adam, gs)), (adam, gs)
