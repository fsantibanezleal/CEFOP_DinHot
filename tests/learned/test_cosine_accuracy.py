"""M17: the accuracy in the definition of DeepCGH (Eybposh et al. 2020, Opt. Express 28, 26636, Eq. 3): the cosine similarity of the
target and reconstructed intensity volumes over all voxels, reported next to DinHot's per-plane Dice-type accuracy."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.forward import fft_focal_field
from pipeline.model.holo.core.geometry import Setup
from pipeline.model.holo.methods.learned import _planes

SETUP = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=32, pitch_m=12.5e-6, pad=1)


def _phi(seed=0):
    return np.random.default_rng(seed).uniform(-np.pi, np.pi, (32, 32))


def _reconstruction_amps(phi):
    """Target amplitudes equal to the amplitude the mask itself produces on every plane."""
    c = np.arange(32) - 15.5
    q = (c[None, :] ** 2 + c[:, None] ** 2) / 16.0**2
    return np.stack([np.abs(fft_focal_field(phi - z * q, SETUP)) for z in _planes.Z_PLANES])


def test_cosine_of_proportional_volumes_is_one_and_ignores_scale():
    t = np.random.default_rng(1).random((3, 8, 8))
    assert _planes.cosine_similarity(t, 7.5 * t) == pytest.approx(1.0, abs=1e-12)


def test_cosine_of_orthogonal_volumes_is_zero():
    t = np.zeros((2, 4, 4))
    i = np.zeros((2, 4, 4))
    t[0, 0, 0] = 3.0
    i[1, 3, 3] = 2.0
    assert _planes.cosine_similarity(t, i) == 0.0


def test_cosine_of_a_zero_reconstruction_is_zero_not_a_division_error():
    t = np.ones((3, 4, 4))
    assert _planes.cosine_similarity(t, np.zeros_like(t)) == 0.0
    assert _planes.cosine_similarity(np.zeros_like(t), t) == 0.0


def test_cosine_against_a_hand_computation():
    """I = [[1, 2], [0, 0]] and J = [[1, 0], [1, 1]] over two planes jointly: dot = 1, |I|^2 = 5, |J|^2 = 3, cosine = 1 / sqrt(15)."""
    t = np.array([[[1.0, 2.0]], [[0.0, 0.0]]])
    i = np.array([[[1.0, 0.0]], [[1.0, 1.0]]])
    assert _planes.cosine_similarity(t, i) == pytest.approx(1.0 / np.sqrt(15.0), abs=1e-15)


def test_volume_cosine_is_one_when_the_target_is_the_reconstruction():
    phi = _phi(2)
    assert _planes.cosine_volume_accuracy(_reconstruction_amps(phi), phi, SETUP) == pytest.approx(1.0, abs=1e-9)


def test_volume_cosine_is_below_one_for_another_mask_and_in_range():
    amps = _reconstruction_amps(_phi(2))
    v = _planes.cosine_volume_accuracy(amps, _phi(3), SETUP)
    assert 0.0 <= v < 0.999


def test_volume_cosine_joins_the_planes_in_one_vector():
    """The joint cosine is not the mean of the per-plane cosines: a plane with a larger intensity weighs more."""
    phi = _phi(4)
    amps = _reconstruction_amps(phi)
    amps[1] = np.roll(amps[1], 5, axis=0)       # one plane displaced, the other two exact
    joint = _planes.cosine_volume_accuracy(amps, phi, SETUP)
    c = np.arange(32) - 15.5
    q = (c[None, :] ** 2 + c[:, None] ** 2) / 16.0**2
    ts, is_ = [], []
    for a, z in zip(amps, _planes.Z_PLANES):
        i = np.abs(fft_focal_field(phi - z * q, SETUP)) ** 2
        ts.append((a**2 / (a**2).sum()).ravel())
        is_.append((i / i.sum()).ravel())
    t, i = np.concatenate(ts), np.concatenate(is_)
    assert joint == pytest.approx(float(t @ i / np.sqrt((t @ t) * (i @ i))), abs=1e-12)


def test_the_evaluation_reports_the_cosine_next_to_the_plane_accuracy():
    from pipeline.model.holo.learned import evaluation
    phi = _phi(5)
    amps = _reconstruction_amps(phi)
    assert evaluation.cosine_accuracy(amps, phi, SETUP) == pytest.approx(1.0, abs=1e-9)
    row = evaluation.accuracy_pair(amps, phi, SETUP)
    assert set(row) == {"ac", "ac_cosine"} and row["ac_cosine"] == pytest.approx(1.0, abs=1e-9)
    assert row["ac"] == pytest.approx(evaluation.plane_accuracy(amps, phi, SETUP))
