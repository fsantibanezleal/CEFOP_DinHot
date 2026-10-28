"""D1: the torch forward model agrees with the numpy engine. Needs torch: runs in .venv-gpu (skipped in .venv-pipeline)."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from pipeline.model.holo.core.forward import fft_focal_field, point_trap_backproject, point_trap_fields  # noqa: E402
from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import Trap, TrapSet  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.learned import convert, generators  # noqa: E402
from pipeline.model.holo.learned import torch_forward as tf  # noqa: E402
from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs  # noqa: E402


@pytest.fixture(scope="module")
def setup():
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2)


@pytest.fixture(scope="module")
def traps(setup):
    rng = np.random.default_rng(3)
    arr = generators.sample_traps(rng, half_field=setup.n_fft / 2, family="random3d")[:40]
    arr[:, 3] = rng.uniform(0.5, 2.0, len(arr))
    ts = convert.input_to_traps(setup, *[a for a in generators.pad_batch([arr], 64)])
    return ts, arr


def _t(x):
    return torch.as_tensor(np.asarray(x))


def test_input_amplitude_matches_numpy(setup):
    for beam, wf in (("gaussian", 1.0), ("gaussian", 0.6), ("flat", 1.0)):
        s = Setup(**{**setup.__dict__, "beam": beam, "waist_frac": wf})
        np.testing.assert_allclose(tf.input_amplitude(s.n_pix, beam, wf).numpy(), input_amplitude(s), atol=1e-6)


def test_unit_conversion_roundtrip(setup, traps):
    ts, arr = traps
    a, m = convert.traps_to_input(setup, ts)
    np.testing.assert_allclose(a[0, : len(arr), :3], arr[:, :3], atol=2e-4, rtol=1e-5)
    back = convert.input_to_traps(setup, a, m)
    np.testing.assert_allclose(back.x_m, ts.x_m, rtol=1e-6, atol=1e-12)
    assert focal_bin_m(setup) > 0 and convert.rayleigh_range_m(setup) > 0


def test_defocus_phase_is_Z_radians_at_the_aperture_edge(setup):
    zr = convert.rayleigh_range_m(setup)
    ts = TrapSet([Trap(0, 0.0, 0.0, zr)])
    a, _ = convert.traps_to_input(setup, ts)
    gx, _gy = tf.trap_factors(torch.as_tensor(a[:, :1]), setup.n_pix, setup.pad)
    phase = torch.angle(gx[0, 0]).numpy()
    c = (np.arange(setup.n_pix) - (setup.n_pix - 1) / 2) / (setup.n_pix / 2)
    np.testing.assert_allclose(phase, -(c**2), atol=2e-5)


def test_projection_and_backprojection_match_numpy(setup, traps):
    ts, arr = traps
    rng = np.random.default_rng(5)
    phi = rng.uniform(-np.pi, np.pi, (setup.n_pix, setup.n_pix))
    t = _t(arr[None]).float()
    gx, gy = tf.trap_factors(t, setup.n_pix, setup.pad)
    amp = tf.input_amplitude(setup.n_pix)
    v = tf.project(amp * torch.polar(torch.ones(1, setup.n_pix, setup.n_pix), _t(phi[None]).float()), gx, gy, setup.n_pix)
    np.testing.assert_allclose(v[0].numpy(), point_trap_fields(phi, setup, ts), atol=2e-5, rtol=1e-4)
    c = rng.normal(size=len(ts)) + 1j * rng.normal(size=len(ts))
    f = tf.backproject(_t(c[None]).to(torch.complex64), gx, gy)[0].numpy()
    np.testing.assert_allclose(f, point_trap_backproject(c, setup, ts), atol=1e-3, rtol=1e-4)


def test_unrolled_wgs_matches_m07(setup, traps):
    ts, arr = traps
    theta = np.random.default_rng(8).uniform(-np.pi, np.pi, len(ts))
    t = _t(arr[None]).float()
    mask = torch.ones(1, len(ts))
    gx, gy = tf.trap_factors(t, setup.n_pix, setup.pad)
    a = torch.sqrt(t[..., 3])
    init = tf.sr_hologram(_t(theta[None]).float(), a, gx, gy)[0].numpy()
    ref = m07_phase_fixed_wgs.run(setup, Target.from_traps(ts), budget=Budget(10), rng=Rng(1), init=init, n_fix=4, form="point")
    out = tf.unrolled_wgs(_t(theta[None]).float(), t, mask, setup.n_pix, setup.pad, steps=10, n_fix=4)
    sig = [o[0].item() for o in out][1:]
    np.testing.assert_allclose(sig, [h["rel_std"] for h in ref.history], rtol=2e-3, atol=2e-4)  # float32 noise below 0.001 percent
    np.testing.assert_allclose([o[1].item() for o in out][1:], [h["efficiency"] for h in ref.history], rtol=2e-3)


def test_padding_does_not_change_the_loss(setup, traps):
    ts, arr = traps
    t, m = generators.pad_batch([arr], 100)
    theta = torch.zeros(1, 100)
    a = tf.unrolled_wgs(theta, torch.as_tensor(t), torch.as_tensor(m), setup.n_pix, setup.pad, 3)
    t2, m2 = generators.pad_batch([arr], len(arr))
    b = tf.unrolled_wgs(torch.zeros(1, len(arr)), torch.as_tensor(t2), torch.as_tensor(m2), setup.n_pix, setup.pad, 3)
    np.testing.assert_allclose(a[-1][0].item(), b[-1][0].item(), rtol=1e-4)


def test_focal_intensity_matches_fft_focal_field():
    s = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
    phi = np.random.default_rng(2).uniform(-np.pi, np.pi, (128, 128))
    e = fft_focal_field(phi, s)
    ref = np.abs(e) ** 2
    ref /= ref.sum()
    got = tf.focal_intensity(_t(phi[None]).float(), tf.input_amplitude(128))[0].numpy()
    np.testing.assert_allclose(got, ref, atol=1e-9, rtol=2e-4)


def test_accuracy_is_one_for_equal_and_below_for_different():
    a = torch.as_tensor(generators.sample_target(np.random.default_rng(1), "ring"))[None]
    t = a**2 / (a**2).sum()
    assert abs(tf.accuracy(a, t).item() - 1.0) < 1e-6
    b = torch.as_tensor(generators.sample_target(np.random.default_rng(2), "line"))[None]
    assert tf.accuracy(a, b**2 / (b**2).sum()).item() < 0.5


def test_plane_intensity_matches_the_engine_point_trap_model_at_depth():
    """A plane at depth Z of the torch model is the engine's trap field at a trap of that depth (Z in Rayleigh ranges)."""
    s = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=1)
    phi = np.random.default_rng(3).uniform(-np.pi, np.pi, (128, 128))
    inten = tf.plane_intensities(_t(phi[None]).float(), tf.input_amplitude(128), tf.Z_PLANES)[0].numpy()
    assert inten.shape == (3, 128, 128) and np.allclose(inten.sum((1, 2)), 1.0, atol=1e-5)
    bin_m, zr = focal_bin_m(s), convert.rayleigh_range_m(s)
    for p, z in enumerate(tf.Z_PLANES):
        for kx, ky in ((0, 0), (5, -9), (-20, 13)):
            v = point_trap_fields(phi, s, TrapSet([Trap(0, kx * bin_m, ky * bin_m, z * zr)]))[0]
            # unit-sum intensity times N^2 is the trap intensity |V|^2 N^2 / N^2 ... : I_bin = |E|^2 / N^2, |V|^2 = |E|^2 / N^2 at pad 1
            np.testing.assert_allclose(inten[p, ky + 64, kx + 64], abs(v) ** 2, rtol=2e-3, atol=1e-9)


def test_volume_accuracy_is_one_for_the_exact_planes():
    a = torch.as_tensor(np.stack([generators.sample_volume(np.random.default_rng(1), "random")[0]]))
    t = a**2 / (a**2).sum((-2, -1), keepdim=True)
    assert abs(tf.volume_accuracy(a, t).item() - 1.0) < 1e-6
