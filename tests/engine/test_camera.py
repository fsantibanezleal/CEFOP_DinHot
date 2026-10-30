from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.model.holo.core.camera import EmulatedCamera
from pipeline.model.holo.core.device import Device, pixel_envelope
from pipeline.model.holo.core.forward import fft_focal_field, trap_bins, trap_fields_from_fft
from pipeline.model.holo.core.geometry import Setup, focal_bin_m
from pipeline.model.holo.core.metrics import trap_intensities
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet, square_grid

S = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=32, pitch_m=12.5e-6, pad=2, beam="flat")


def field_and_traps():
    phi = Rng(1).phases(32 * 32).reshape(32, 32)
    b = focal_bin_m(S)
    tr = TrapSet(Trap(i, kx * b, ky * b) for i, (kx, ky) in enumerate([(0, 0), (6, 4), (-10, 3), (25, -20)]))
    return fft_focal_field(phi, S), tr


def test_ideal_camera_reads_true_intensities():
    e, tr = field_and_traps()
    cam = EmulatedCamera(seed=1, gain_rms=0.0, noise_rms=0.0, blur_bins=0.0, rolloff=False)
    got = cam.measure(e, S, tr)
    assert np.allclose(got, trap_intensities(trap_fields_from_fft(e, S, tr)), rtol=1e-12)


def test_gains_are_per_trap_seeded_and_order_independent():
    a = EmulatedCamera(seed=5, gain_rms=0.1)
    b = EmulatedCamera(seed=5, gain_rms=0.1)
    assert [a.gain(i) for i in range(10)] == [b.gain(i) for i in reversed(range(10))][::-1]
    assert a.gain(3) == a.gain(3)
    assert EmulatedCamera(seed=6, gain_rms=0.1).gain(3) != a.gain(3)
    g = np.array([a.gain(i) for i in range(4000)])
    assert abs(g.mean() - 1.0) < 0.01
    assert g.std() == pytest.approx(0.1, rel=0.1)
    assert np.all(g > 0)


def test_gain_scales_measurement():
    e, tr = field_and_traps()
    ideal = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False).measure(e, S, tr)
    cam = EmulatedCamera(seed=1, gain_rms=0.2, rolloff=False)
    got = cam.measure(e, S, tr)
    assert np.allclose(got / ideal, [cam.gain(int(i)) for i in tr.ids])


def test_noise_is_additive_stateful_and_seeded():
    e, tr = field_and_traps()
    def mk(seed):
        return EmulatedCamera(seed=seed, gain_rms=0.0, noise_rms=1e-4, rolloff=False)
    c = mk(3)
    f1, f2 = c.measure(e, S, tr), c.measure(e, S, tr)
    assert not np.array_equal(f1, f2)                      # a new frame, new noise
    d = mk(3)
    assert np.array_equal(f1, d.measure(e, S, tr)) and np.array_equal(f2, d.measure(e, S, tr))
    assert not np.array_equal(f1, mk(4).measure(e, S, tr))
    flat = np.ones_like(e)
    base = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False).measure(flat, S, tr)
    many = np.array([c.measure(flat, S, tr) - base for _ in range(400)])
    assert np.std(many) == pytest.approx(1e-4, rel=0.1) and abs(many.mean()) < 2e-5
    assert np.all(f1 >= 0)
    # explicit rng overrides the internal stream
    r1 = c.measure(e, S, tr, rng=Rng(9))
    r2 = mk(99).measure(e, S, tr, rng=Rng(9))
    assert np.array_equal(r1, r2)


def test_rolloff_matches_pixel_envelope():
    e, tr = field_and_traps()
    flat = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False).measure(e, S, tr)
    roll = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=True).measure(e, S, tr)
    env = pixel_envelope(S, Device())
    iy, ix = trap_bins(S, tr)
    assert np.allclose(roll / flat, env[iy, ix])
    assert roll[3] / flat[3] < roll[0] / flat[0]            # far trap rolls off more than the central one


def test_blur_averages_neighbouring_bins():
    e, tr = field_and_traps()
    sharp = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False).measure(e, S, tr)
    blurred = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False, blur_bins=2.0).measure(e, S, tr)
    assert not np.allclose(sharp, blurred)
    uniform = np.ones_like(e)
    cam = EmulatedCamera(seed=1, gain_rms=0.0, rolloff=False, blur_bins=2.0)
    assert np.allclose(cam.measure(uniform, S, tr), 1.0 * S.pad**2 / S.n_pix**2)    # blur preserves a flat map


def test_validation_and_documented_emulation():
    for kw in (dict(gain_rms=-0.1), dict(noise_rms=-1.0), dict(blur_bins=-1.0), dict(fill_factor=0.0)):
        with pytest.raises(ValueError):
            EmulatedCamera(seed=1, **kw)
    with pytest.raises(ValueError):
        EmulatedCamera(seed=-1)
    e, tr = field_and_traps()
    with pytest.raises(ValueError):
        EmulatedCamera(seed=1).measure(e[:4, :4], S, tr)
    assert "emulat" in (EmulatedCamera.__doc__ or "").lower()
    assert math.isfinite(EmulatedCamera(seed=1).gain(0)) and len(square_grid(2, 2, 3.0)) == 4
