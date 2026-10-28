"""M03: random mask encoding (SDD ladder; Di Leonardo 2007 Table 1: e/u = 0.01/0.58; Montes-Usategui et al. 2006)."""
from __future__ import annotations

import numpy as np

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m03_random_mask as m

SEEDS = range(5)


def test_acceptance_10x10_over_seeds(setup256, grid10, evaluate):
    vals = np.array([evaluate(m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(s)).phi, grid10)
                     for s in SEEDS])
    e, u = vals[:, 0], vals[:, 1]
    M = len(grid10)
    assert np.all((e > 0.5 / M) & (e < 2.0 / M)), e      # efficiency about 1/M
    # published u = 0.58 holds at 768 x 768 (next test); at 256 x 256 there are 9 times fewer pixels per trap, so the
    # coherent part of each trap field is relatively weaker and u falls (measured 0.03 to 0.07)
    assert np.all(u > 0.0) and np.all(u < 0.30), u


def test_published_grid_768_reproduces_uniformity():
    """At the paper's 768 x 768 grid the method reproduces e about 0.01 and u about 0.58 (validates the implementation)."""
    from pipeline.model.holo.core.geometry import Setup, focal_bin_m
    from pipeline.model.holo.core.traps import square_grid
    s768 = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=768, pitch_m=12.5e-6, pad=2)
    tr = square_grid(10, 10, 8 * focal_bin_m(s768) * 1e6)
    h = [m.run(s768, Target.from_traps(tr), budget=Budget(1), rng=Rng(s)).history[0] for s in range(2)]
    assert all(abs(x["uniformity"] - 0.58) <= 0.10 for x in h), [x["uniformity"] for x in h]
    assert all(0.005 < x["efficiency"] < 0.02 for x in h)


def test_masks_are_disjoint_and_equal_share(setup256, grid10):
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(3))
    owner = r.meta["owner"]
    counts = np.bincount(owner.ravel(), minlength=len(grid10))
    assert owner.shape == (256, 256) and counts.sum() == 256 * 256
    assert counts.max() - counts.min() <= 1


def test_each_pixel_shows_its_traps_phase(setup256, grid10):
    from pipeline.model.holo.core.modes import grating_phase
    from pipeline.model.holo.core.geometry import wrap_phase
    r = m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(3))
    k = 17
    sel = r.meta["owner"] == k
    ref = wrap_phase(grating_phase(setup256, grid10.x_m[k], grid10.y_m[k]))
    d = np.angle(np.exp(1j * (r.phi[sel] - ref[sel])))
    assert np.max(np.abs(d)) < 1e-9


def test_deterministic(setup256, grid10):
    t = Target.from_traps(grid10)
    a = m.run(setup256, t, budget=Budget(1), rng=Rng(4)).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(1), rng=Rng(4)).phi)


def test_spec():
    assert m.SPEC.id == "M03"
