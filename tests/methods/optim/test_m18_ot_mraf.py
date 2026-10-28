"""M18 optimal-transport initialized MRAF (Swan et al. 2024; Torchylo et al. 2025).

Acceptance: lower error than MRAF from a random start on the shaped targets (ring, disc, line), on the live-size
(128 x 128 focal grid) and baked-size (256 x 256) grids, at the same number of MRAF iterations and the same mixing
parameter. Seeds: 2 random starts at the live size, 1 at the baked size (benchmark: 20).
"""
from __future__ import annotations

import numpy as np
import pytest
from e3_helpers import disc_target, line_target, make_setup, ring_target, signal_error

from pipeline.model.holo.core.forward import fft_focal_field
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.optim import m18_ot_mraf as M18

ITERATIONS = 100


def targets(setup):
    sc = setup.n_pix / 64
    return {"disc": disc_target(setup, 24 * sc, 3 * sc), "ring": ring_target(setup, 22 * sc, 8 * sc, 2 * sc),
            "line": line_target(setup, 50 * sc, 8 * sc, 2 * sc)}


def test_spec():
    assert M18.SPEC.id == "M18" and M18.SPEC.targets == ("field",) and M18.SPEC.lane in ("baked", "both")


def test_unsupported_and_misshaped_targets_raise():
    from pipeline.model.holo.core.traps import square_grid
    s = make_setup(16)
    with pytest.raises(ValueError, match="field"):
        M18.run(s, Target.from_traps(square_grid(2, 2, 80.0)), budget=Budget(1), rng=Rng(1))
    with pytest.raises(ValueError, match="32"):
        M18.run(s, Target.from_field(np.ones((16, 16)), np.ones((16, 16), dtype=bool)), budget=Budget(1), rng=Rng(1))


def test_sinkhorn_matches_both_marginals_on_a_smooth_problem():
    n = 32
    xs = np.arange(n) - (n - 1) / 2
    gx, gy = np.meshgrid(xs, xs)
    a = np.exp(-(gx**2 + gy**2) / (2 * 6.0**2))
    b = np.exp(-((gx - 3) ** 2 + (gy + 2) ** 2) / (2 * 4.0**2))
    a, b = a / a.sum(), b / b.sum()
    sol = M18.sinkhorn_separable(a, b, xs, xs, 4.0**2, 300)
    kv = sol["kv"]
    assert np.abs(sol["u"] * kv - a).sum() < 1e-6                  # source marginal
    kx = sol["kx"]
    tm = sol["v"] * (sol["ky"].T @ sol["u"] @ kx)                  # target marginal v (K^T u)
    assert np.abs(tm - b).sum() < 1e-9
    assert sol["residual"] < 1e-6


def test_barycentric_map_of_a_pure_shift_is_a_shift():
    n = 48
    xs = np.arange(n) - (n - 1) / 2
    gx, gy = np.meshgrid(xs, xs)
    a = np.exp(-(gx**2 + gy**2) / (2 * 6.0**2))
    b = np.exp(-((gx - 4) ** 2 + (gy + 3) ** 2) / (2 * 6.0**2))
    a, b = a / a.sum(), b / b.sum()
    sol = M18.sinkhorn_separable(a, b, xs, xs, 2.0**2, 400)
    tx, ty = M18.barycentric_map(sol, xs, xs)
    core = (np.abs(gx) < 6) & (np.abs(gy) < 6)
    assert np.abs(tx[core] - (gx[core] + 4)).max() < 0.6
    assert np.abs(ty[core] - (gy[core] - 3)).max() < 0.6


def test_gradient_integration_recovers_a_known_potential():
    n = 64
    xs = np.arange(n) - (n - 1) / 2
    gx, gy = np.meshgrid(xs, xs)
    psi = 3.0 * np.exp(-(gx**2 + gy**2) / (2 * 12.0**2)) + 0.002 * (gx**2 + 0.5 * gy**2)
    tx, ty = np.gradient(psi, axis=1), np.gradient(psi, axis=0)
    got = M18.integrate_gradient(tx, ty)
    ref = psi - psi.mean()
    assert np.abs(got - ref).max() < 0.02 * np.abs(ref).max()


def test_ot_seed_moves_the_beam_onto_a_displaced_blob():
    s = make_setup(32)
    m = s.n_fft
    k = np.arange(m) - m // 2
    kx, ky = np.meshgrid(k, k)
    amp = np.exp(-((kx - 10) ** 2 + (ky + 6) ** 2) / (2 * 5.0**2))
    mask = amp > 0.2
    phi, info = M18.ot_phase(s, amp, mask)
    i = np.abs(fft_focal_field(phi, s)) ** 2
    cx, cy = (i * kx).sum() / i.sum(), (i * ky).sum() / i.sum()
    assert abs(cx - 10) < 1.0 and abs(cy + 6) < 1.0
    assert info["residual"] < 1e-3


def test_deterministic_and_pure_function_of_inputs():
    s = make_setup(16)
    amp, mask = disc_target(s, 10.0, 2.0)
    a = M18.run(s, Target.from_field(amp, mask), budget=Budget(5), rng=Rng(1))
    b = M18.run(s, Target.from_field(amp, mask), budget=Budget(5), rng=Rng(99))   # the OT seed uses no randomness
    assert np.array_equal(a.phi, b.phi) and a.meta["ot_init"]
    c = M18.run(s, Target.from_field(amp, mask), budget=Budget(5), rng=Rng(1), init=Rng(3).phases(256).reshape(16, 16))
    assert not c.meta["ot_init"]


def run_pair(setup, name, seeds):
    amp, mask = targets(setup)[name]
    ot = M18.run(setup, Target.from_field(amp, mask), budget=Budget(ITERATIONS), rng=Rng(1))
    e_ot, eff_ot = signal_error(ot.fields, amp, mask)
    rand = []
    for sd in seeds:
        init = Rng(sd).phases(setup.n_pix**2).reshape(setup.n_pix, setup.n_pix)
        r = M18.run(setup, Target.from_field(amp, mask), budget=Budget(ITERATIONS), rng=Rng(1), init=init)
        rand.append(signal_error(r.fields, amp, mask)[0])
    return e_ot, eff_ot, rand


@pytest.mark.parametrize("name", ["disc", "ring", "line"])
def test_acceptance_live_size_lower_error_than_random_start(name):
    s = make_setup(64)
    e_ot, eff_ot, rand = run_pair(s, name, (5, 6))
    assert e_ot < min(rand), (e_ot, rand)
    assert eff_ot > 0.3                              # same efficiency class as MRAF (Swan: 0.18 to 0.45 and 0.53 to 0.85)


@pytest.mark.parametrize("name", ["disc", "ring"])
def test_acceptance_baked_size_lower_error_than_random_start(name):
    s = make_setup(128)
    e_ot, eff_ot, rand = run_pair(s, name, (5,))
    assert e_ot < min(rand), (e_ot, rand)
