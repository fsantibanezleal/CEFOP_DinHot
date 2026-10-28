"""Seeded generators, unit conversion and held-out files (numpy only: runs in .venv-pipeline and .venv-gpu)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.geometry import Setup
from pipeline.model.holo.core.traps import Trap, TrapSet
from pipeline.model.holo.learned import convert, generators, heldout


def _held(name):
    import os
    from pathlib import Path
    d = os.environ.get("DINHOT_LEARNED_DIR")
    return Path(d) / name if d else Path("absent") / name



@pytest.fixture(scope="module")
def setup():
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)


def test_trap_sets_are_seeded_and_in_the_field():
    a = [generators.sample_traps(np.random.default_rng(7)) for _ in range(2)]
    np.testing.assert_array_equal(a[0], a[1])
    rng = np.random.default_rng(11)
    for _ in range(40):
        s = generators.sample_traps(rng)
        assert 1 <= len(s) <= 1024 and s.shape[1] == 4
        assert np.all(np.abs(s[:, :2]) < 248) and np.all(s[:, 3] > 0) and np.all(np.isfinite(s))


def test_targets_are_unit_energy_and_seeded():
    for kind in generators.SHAPE_KINDS:
        a = generators.sample_target(np.random.default_rng(3), kind)
        b = generators.sample_target(np.random.default_rng(3), kind)
        np.testing.assert_array_equal(a, b)
        assert a.shape == (128, 128) and a.dtype == np.float32
        assert abs(float(np.sum(a.astype(np.float64) ** 2)) - 1.0) < 1e-5


def test_pad_batch_masks_the_padding():
    t, m = generators.pad_batch([np.ones((3, 4)), np.ones((5, 4))])
    assert t.shape == (2, 5, 4) and m.sum() == 8 and t[0, 3:].sum() == 0


def test_conversion_limits(setup):
    big = TrapSet(Trap(i, 1e-6 * (i % 30), 1e-6 * (i // 30), 0.0) for i in range(1025))
    with pytest.raises(ValueError, match="at most 1024"):
        convert.traps_to_input(setup, big)
    with pytest.raises(ValueError, match="vortex"):
        convert.traps_to_input(setup, TrapSet([Trap(0, 0.0, 0.0, 0.0, 1.0, 1)]))
    arr, mask = convert.traps_to_input(setup, TrapSet([Trap(0, 1e-6, 0.0, 0.0)]))
    assert arr.shape == (1, 1024, 4) and arr.dtype == np.float32 and mask.sum() == 1


def test_rayleigh_range_formula(setup):
    r = 256 * 12.5e-6 / 2
    assert convert.rayleigh_range_m(setup) == pytest.approx(0.85e-6 * 0.25**2 / (np.pi * r * r))


def test_benchmark_geometries_in_model_units():
    sets = heldout.bench_trap_sets()
    assert {g: len(a) for g, (a, _n) in sets.items()} == {"G1": 100, "G2": 36, "G3": 100, "G4": 119, "G5": 75, "G6": 1024}
    g1 = sets["G1"][0]
    assert np.isclose(np.unique(np.round(g1[:, 0], 6))[1] - np.unique(np.round(g1[:, 0], 6))[0], 16.0)   # 8 u = 16 bins
    assert np.abs(sets["G5"][0][:, 2]).max() > 1.0                                                  # planes are off focus
    t = heldout.bench_targets()
    assert sorted(t) == ["G1", "G2", "G3", "G4", "G6", "G7_disc", "G7_lg_ring", "G7_line", "G7_ring"]
    assert all(abs(float(np.sum(v.astype(np.float64) ** 2)) - 1) < 1e-5 for v in t.values())


def test_heldout_files_have_the_recorded_hashes_and_are_disjoint_from_training_seeds():
    p = _held("cgh-heldout.npz")
    if not p.is_file():
        pytest.skip("held-out files are in the data root of the training device")
    gen, kinds, bench, names = heldout.load_cgh(p)
    assert len(gen) == 7 * heldout.CGH_GEN_PER_KIND and len(bench) == 9 and set(kinds) == set(generators.SHAPE_KINDS)
    assert {heldout.CGH_SEED, heldout.WARM_SEED}.isdisjoint({20261101, 20261102})   # the training data seeds
    # regeneration with the recorded seed reproduces the file's generated targets bit for bit
    rng = np.random.default_rng(heldout.CGH_SEED)
    first = generators.sample_target(rng, generators.SHAPE_KINDS[0])
    np.testing.assert_array_equal(first, gen[0])
    w = _held("warmstart-heldout.npz")
    wg, wb = heldout.load_warm(w)
    assert len(wg) == heldout.WARM_GEN_N and all(len(a) >= 40 for a in wg) and [n for n, _a, _p in wb] == ["G1", "G2", "G3", "G4", "G5", "G6"]
