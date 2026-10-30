"""M19: volumetric 3D GS with the Ewald-sphere constraint (SDD ladder; Whyte and Courtial 2005, New J. Phys. 7, 117).

The SDD row reads "on a three-plane target, every plane within the plane intensity band". The band is not defined in the
SDD; this test defines it: the mean trap intensity of every plane lies within 25 percent of the mean over all traps
(a plane is neither starved nor dominant), and no plane is empty. The within-plane uniformity is reported, not bounded.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from pipeline.model.holo.core.forward import point_trap_fields
from pipeline.model.holo.core.geometry import focal_bin_m
from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.traps import Trap, TrapSet, square_grid
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m19_multiplane as m

DZ = 40e-3          # plane step: above the depth of field 2 lambda / NA^2 (about 40 mm) of the 256-pixel aperture
SEEDS = (1, 2)


def three_plane(setup, per_side=5, spacing_vox=6):
    """Three planes at -DZ, 0, +DZ, each a per_side x per_side grid on lateral voxels, planes shifted laterally."""
    vox = setup.pad * focal_bin_m(setup)
    base = square_grid(per_side, per_side, spacing_vox * vox * 1e6)
    traps = []
    for p, (z, sx, sy) in enumerate([(-DZ, 0, 0), (0.0, 3, 3), (DZ, -3, 3)]):
        for t in base:
            traps.append(Trap(p * len(base) + t.id, t.x_m + sx * vox, t.y_m + sy * vox, z))
    return TrapSet(traps)


def plane_stats(v, traps):
    inten = np.abs(v) ** 2
    out = []
    for z in np.unique(traps.z_m):
        sel = traps.z_m == z
        out.append((inten[sel].mean(), 100 * inten[sel].std() / inten[sel].mean()))
    return np.array(out)


def test_acceptance_three_planes_within_the_band(setup256):
    tr = three_plane(setup256)
    for s in SEEDS:
        r = m.run(setup256, Target.from_traps(tr), budget=Budget(20), rng=Rng(s), dz_m=DZ)
        st = plane_stats(r.fields, r.meta["snapped"])
        mean_all = (np.abs(r.fields) ** 2).mean()
        assert np.all(np.abs(st[:, 0] / mean_all - 1.0) <= 0.25), (s, st, mean_all)
        assert r.history[-1]["efficiency"] > 0.3


def test_fields_are_the_point_trap_model_of_the_snapped_traps(setup256):
    tr = three_plane(setup256, per_side=3)
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(3), rng=Rng(1), dz_m=DZ)
    v = point_trap_fields(r.phi, setup256, r.meta["snapped"])
    assert np.allclose(v, r.fields, rtol=1e-9, atol=1e-12)
    assert r.meta["nz"] >= 16 and r.meta["dz_m"] == DZ


def test_single_off_plane_trap_is_focused(setup256, ceiling):
    tr = TrapSet([Trap(0, 0.0, 0.0, DZ)])
    r = m.run(setup256, Target.from_traps(tr), budget=Budget(15), rng=Rng(2), dz_m=DZ)
    assert r.history[-1]["efficiency"] > 0.7 * ceiling


def test_efficiency_improves_over_iterations(setup256):
    r = m.run(setup256, Target.from_traps(three_plane(setup256, 3)), budget=Budget(12), rng=Rng(1), dz_m=DZ)
    assert r.history[-1]["efficiency"] > r.history[0]["efficiency"]
    assert [h["iteration"] for h in r.history] == list(range(1, 13))


def test_deterministic_and_validation(setup256):
    tr = three_plane(setup256, 2)
    t = Target.from_traps(tr)
    a = m.run(setup256, t, budget=Budget(3), rng=Rng(4), dz_m=DZ).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(3), rng=Rng(4), dz_m=DZ).phi)
    dup = TrapSet([Trap(0, 0.0, 0.0, 0.0), Trap(1, 1e-9, 0.0, 0.0)])
    with pytest.raises(ValueError, match="voxel"):
        m.run(setup256, Target.from_traps(dup), budget=Budget(1), rng=Rng(1), dz_m=DZ)
    flat = TrapSet([replace(t0, z_m=0.0) for t0 in tr])
    with pytest.raises(ValueError, match="dz_m"):
        m.run(setup256, Target.from_traps(flat), budget=Budget(1), rng=Rng(1))
    n = setup256.n_fft
    with pytest.raises(ValueError, match="traps"):
        m.run(setup256, Target.from_field(np.ones((n, n)), np.ones((n, n), bool)), budget=Budget(1), rng=Rng(1))
