"""Tests of the shared optimization machinery: line search, Adam, forward models with exact adjoints, GS family."""
from __future__ import annotations

import numpy as np
import pytest
from e3_helpers import check_finite_difference, make_setup, task_10x10

from pipeline.model.holo.core.device import Device, device_focal_field
from pipeline.model.holo.core.forward import fft_focal_field, point_trap_fields, trap_fields_from_fft
from pipeline.model.holo.core.metrics import trap_intensities, uniformity
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet, snap_to_bins, square_grid
from pipeline.model.holo.methods.optim import _common as C
from pipeline.model.holo.methods.optim import _gs_family as G


# ---- optimizers -----------------------------------------------------------------------------------------------

def test_cg_minimizes_a_quadratic_in_n_iterations():
    rng = np.random.default_rng(1)
    a = rng.standard_normal((12, 12))
    q = a @ a.T + 12 * np.eye(12)
    b = rng.standard_normal(12)

    def fun(x):
        return 0.5 * x @ q @ x - b @ x, q @ x - b, None

    res = C.cg_minimize(fun, np.zeros(12), 60)
    assert np.linalg.norm(res.x - np.linalg.solve(q, b)) < 1e-6
    assert res.f < fun(np.zeros(12))[0]


def test_cg_solves_rosenbrock_with_strong_wolfe_line_search():
    def fun(x):
        f = 100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2
        g = np.array([-400 * x[0] * (x[1] - x[0] ** 2) - 2 * (1 - x[0]), 200 * (x[1] - x[0] ** 2)])
        return f, g, None

    res = C.cg_minimize(fun, np.array([-1.2, 1.0]), 400)
    assert np.allclose(res.x, [1.0, 1.0], atol=1e-4)


def test_cg_cost_never_increases_and_callback_can_stop():
    def fun(x):
        f = 100 * (x[1] - x[0] ** 2) ** 2 + (1 - x[0]) ** 2
        g = np.array([-400 * x[0] * (x[1] - x[0] ** 2) - 2 * (1 - x[0]), 200 * (x[1] - x[0] ** 2)])
        return f, g, None

    seen = []

    def cb(i, x, f, aux):
        seen.append(f)
        return i >= 5

    res = C.cg_minimize(fun, np.array([-1.2, 1.0]), 100, callback=cb)
    assert res.iterations == 5 and len(seen) == 5
    assert all(b <= a + 1e-15 for a, b in zip(seen, seen[1:]))


def test_adam_matches_hand_computed_first_steps():
    # f = x^2 / 2 at x0 = 1: g = 1, m1 = 0.1, v1 = 0.001 -> mhat = 1, vhat = 1, step lr * 1 / (1 + eps)
    def fun(x):
        return float(0.5 * np.sum(x**2)), x.copy(), None

    res = C.adam_minimize(fun, np.array([1.0]), 1, lr=0.1)
    assert res.x[0] == pytest.approx(1.0 - 0.1 / (1.0 + 1e-8), abs=1e-12)
    res = C.adam_minimize(fun, np.array([3.0, -2.0]), 400, lr=0.05)
    assert np.abs(res.x).max() < 0.05


def test_permutation_is_a_seeded_permutation():
    p = C.permutation(Rng(5), 1000)
    assert sorted(p.tolist()) == list(range(1000))
    assert np.array_equal(p, C.permutation(Rng(5), 1000))
    assert not np.array_equal(p, C.permutation(Rng(6), 1000))


# ---- forward models and adjoints ------------------------------------------------------------------------------

def test_focal_forward_ideal_matches_core_and_gradient_is_exact():
    s = make_setup(16)
    rng = Rng(1)
    phi = rng.phases(256).reshape(16, 16)
    fwd = C.FocalForward(s)
    e, _ = fwd.forward(phi)
    assert np.allclose(e, fft_focal_field(phi, s), atol=1e-13)
    w = np.random.default_rng(0).standard_normal(e.shape)

    def fun(x):
        ee, cache = fwd.forward(x)
        g = fwd.adjoint(w * ee, cache)           # L = sum w |E|^2, so dL/dE* = w E
        return float(np.sum(w * np.abs(ee) ** 2)), g, None

    assert check_finite_difference(fun, phi, np.random.default_rng(2)) < 1e-6


@pytest.mark.parametrize("device", [
    Device(crosstalk=(1.24, 1.80), upsample=3),
    Device(crosstalk=(0.8, 1.5), upsample=2, fill_factor=0.8),
    Device(fill_factor=0.9),
])
def test_focal_forward_device_matches_core_and_gradient_is_exact(device):
    s = make_setup(12)
    phi = Rng(3).phases(144).reshape(12, 12)
    fwd = C.FocalForward(s, device)
    e, _ = fwd.forward(phi)
    assert np.allclose(e, device_focal_field(phi, s, device, None), atol=1e-12)
    w = np.random.default_rng(1).standard_normal(e.shape)

    def fun(x):
        ee, cache = fwd.forward(x)
        return float(np.sum(w * np.abs(ee) ** 2)), fwd.adjoint(w * ee, cache), None

    assert check_finite_difference(fun, phi, np.random.default_rng(4)) < 1e-6


def test_focal_forward_quantizer_is_straight_through():
    s = make_setup(12)
    dev = Device(bit_depth=3, crosstalk=(1.24, 1.8))
    phi = Rng(3).phases(144).reshape(12, 12)
    fwd = C.FocalForward(s, dev)
    e, _ = fwd.forward(phi)
    assert np.allclose(e, device_focal_field(phi, s, dev, None), atol=1e-12)     # the forward IS quantized
    # flicker is not part of an optimization model: it is dropped
    assert C.FocalForward(s, Device(flicker_rad=0.3)).device.flicker_rad == 0.0


def test_trap_forward_ideal_with_z_and_vortex_matches_core_and_gradient_is_exact():
    s = make_setup(16)
    traps = TrapSet([Trap(0, 3e-5, 1e-5, 0.0), Trap(1, -2e-5, 4e-5, 2e-5, weight=2.0),
                     Trap(2, 1e-5, -3e-5, 0.0, charge=2), Trap(3, -4e-5, -1e-5, -1e-5)])
    phi = Rng(8).phases(256).reshape(16, 16)
    fwd = C.TrapForward(s, traps)
    v, _ = fwd.fields(phi)
    assert np.allclose(v, point_trap_fields(phi, s, traps), atol=1e-13)
    cost = C.TrapCost(s, traps, t=2, efficiency=0.5)
    assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(0)) < 1e-6


def test_trap_forward_device_reads_the_nearest_bin_and_gradient_is_exact():
    s = make_setup(16)
    traps = snap_to_bins(s, square_grid(3, 3, 8 * 8.32))
    dev = Device(crosstalk=(1.24, 1.8))
    phi = Rng(9).phases(256).reshape(16, 16)
    fwd = C.TrapForward(s, traps, dev)
    v, _ = fwd.fields(phi)
    ref = trap_fields_from_fft(device_focal_field(phi, s, dev, None), s, traps)
    assert np.allclose(v, ref, atol=1e-12)
    for t in (2, 4):
        cost = C.TrapCost(s, traps, dev, t=t, efficiency=0.5)
        assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(t)) < 1e-6


def test_field_cost_gradient_matches_finite_differences_for_t_2_and_4():
    s = make_setup(16)
    amp = np.zeros((32, 32))
    mask = np.zeros((32, 32), dtype=bool)
    mask[12:20, 10:22] = True
    amp[mask] = 1.0 + 0.2 * np.random.default_rng(0).random(mask.sum())
    phi = Rng(2).phases(256).reshape(16, 16)
    for device in (None, Device(crosstalk=(1.24, 1.8))):
        for t in (2, 4):
            cost = C.FieldCost(s, amp, mask, device, t=t, efficiency=0.3)
            assert check_finite_difference(lambda x: cost.value_grad(x), phi, np.random.default_rng(t)) < 1e-6


def test_field_cost_rejects_wrong_shapes():
    s = make_setup(16)
    with pytest.raises(ValueError, match="32"):
        C.FieldCost(s, np.ones((16, 16)), np.ones((16, 16), dtype=bool))


def test_history_entry_has_the_required_keys():
    s = make_setup(16)
    traps = snap_to_bins(s, square_grid(2, 2, 40.0))
    v = point_trap_fields(Rng(1).phases(256).reshape(16, 16), s, traps)
    h = C.trap_history(3, v, traps.weight, 0.0)
    for k in ("iteration", "efficiency", "uniformity", "rel_std", "time_s"):
        assert k in h
    assert h["iteration"] == 3


# ---- Gerchberg-Saxton family used as the in-test baseline ----------------------------------------------------

def test_gs_family_reaches_the_published_trends_on_the_10x10_task():
    s = make_setup(256)
    traps = task_10x10(s)
    out = {}
    for variant in ("gs", "gsw", "pfwgs"):
        phi, _ = G.weighted_gs(s, traps, 30, Rng(1), variant=variant)
        v = point_trap_fields(phi, s, traps)
        out[variant] = (float(np.sum(trap_intensities(v))), uniformity(trap_intensities(v, traps.weight)))
    # Di Leonardo 2007 (flat illumination, 768 pixels): GS e 0.94 u 0.60, GSW e 0.93 u 0.99. The Gaussian beam of the core
    # default puts about 14 percent of the power outside the useful aperture, so the efficiencies are lower here
    # (measured flat-beam values of this loop: GS 0.93 / 0.56, GAA 0.93 / 0.69, GSW 0.92 / 0.95, phase-fixed 0.91 / 1.00).
    assert out["gs"][0] > 0.75 and out["gs"][1] < 0.7
    assert out["gsw"][0] > 0.75 and out["gsw"][1] > 0.95
    assert out["pfwgs"][0] > 0.75 and out["pfwgs"][1] > 0.98
    flat = make_setup(256, beam="flat")
    phi, _ = G.weighted_gs(flat, task_10x10(flat), 30, Rng(1), variant="gs")
    assert 0.9 < float(np.sum(trap_intensities(point_trap_fields(phi, flat, task_10x10(flat))))) < 0.97


def test_gs_family_is_deterministic_and_validates():
    s = make_setup(32)
    traps = snap_to_bins(s, square_grid(3, 3, 8 * 8.32 * 4))
    a, _ = G.weighted_gs(s, traps, 5, Rng(2), variant="gsw")
    b, _ = G.weighted_gs(s, traps, 5, Rng(2), variant="gsw")
    assert np.array_equal(a, b)
    with pytest.raises(ValueError, match="variant"):
        G.weighted_gs(s, traps, 5, Rng(2), variant="nope")
