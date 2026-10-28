"""M08: mixed-region amplitude freedom (SDD ladder; Pasienski and DeMarco 2008: error 0.015 to 0.039 against 0.21 to 0.36 for GS)."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.rng import Rng
from pipeline.model.holo.core.types import Budget, Target
from pipeline.model.holo.methods.baseline import m04_gs
from pipeline.model.holo.methods.baseline import m08_mraf as m

STARTS = (16.0, 24.0)       # the default start is deterministic (a Fresnel-lens phase), so the starts are varied instead of seeds


def _grid(setup):
    n = setup.n_fft
    yy, xx = np.indices((n, n))
    return yy - n // 2, xx - n // 2


def _dilate(mask, r=3):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def shaped(setup, kind):
    """A target of ``kind`` (disc, ring, line) on the FFT grid: amplitude 1 inside the shape, signal region = shape dilated 8 bins."""
    y, x = _grid(setup)
    r = np.hypot(y, x)
    shape = {"disc": r < 60, "ring": (r > 45) & (r < 75), "line": (np.abs(x) < 120) & (np.abs(y) < 20)}[kind]
    return Target.from_field(shape.astype(float), _dilate(shape, 8))


@pytest.mark.parametrize("kind", ["disc", "ring", "line"])
def test_signal_error_five_times_below_gs_at_the_cost_of_efficiency(setup256, kind):
    t = shaped(setup256, kind)
    ratios, eff_gs, eff_mraf = [], [], []
    for w in STARTS:
        g = m04_gs.run(setup256, t, budget=Budget(45), rng=Rng(1), start_waves=w)
        r = m.run(setup256, t, budget=Budget(45), rng=Rng(1), start_waves=w)
        ratios.append(g.history[-1]["error"] / r.history[-1]["error"])
        eff_gs.append(g.history[-1]["efficiency"])
        eff_mraf.append(r.history[-1]["efficiency"])
    assert min(ratios) >= 5.0, (kind, ratios)
    assert all(a < b for a, b in zip(eff_mraf, eff_gs)), (kind, eff_mraf, eff_gs)   # accuracy is bought with efficiency


def test_thin_line_is_resolution_limited(setup256):
    """A 16-bin wide line (8 resolution cells) reaches only a factor 3 to 4 below GS: its error floor is the edge, not the method."""
    y, x = _grid(setup256)
    shape = (np.abs(x) < 80) & (np.abs(y) < 8)
    t = Target.from_field(shape.astype(float), _dilate(shape, 8))
    g = m04_gs.run(setup256, t, budget=Budget(40), rng=Rng(1), start_waves=16.0).history[-1]["error"]
    q = m.run(setup256, t, budget=Budget(40), rng=Rng(1), start_waves=16.0).history[-1]["error"]
    assert 2.5 <= g / q < 5.0, g / q


def test_mixing_one_is_gs(setup256):
    t = shaped(setup256, "disc")
    a = m.run(setup256, t, budget=Budget(5), rng=Rng(3), mixing=1.0)
    b = m04_gs.run(setup256, t, budget=Budget(5), rng=Rng(3))
    assert np.abs(np.angle(np.exp(1j * (a.phi - b.phi)))).max() < 1e-9


def test_default_mixing_in_paper_range_and_history_keys(setup256):
    import inspect
    assert 0.30 <= inspect.signature(m.run).parameters["mixing"].default <= 0.40
    r = m.run(setup256, shaped(setup256, "ring"), budget=Budget(3), rng=Rng(1))
    assert [h["iteration"] for h in r.history] == [1, 2, 3]
    assert set(r.history[0]) >= {"iteration", "efficiency", "uniformity", "rel_std", "time_s", "error"}


def test_random_start_uses_the_rng_and_is_reproducible(setup256):
    t = shaped(setup256, "disc")
    a = m.run(setup256, t, budget=Budget(2), rng=Rng(5), start_waves=None).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(2), rng=Rng(5), start_waves=None).phi)
    assert not np.array_equal(a, m.run(setup256, t, budget=Budget(2), rng=Rng(6), start_waves=None).phi)


def test_thin_shape_is_rejected(setup256):
    y, x = _grid(setup256)
    line = (np.abs(x) < 30) & (np.abs(y) < 2)
    with pytest.raises(ValueError, match="thinner"):
        m.run(setup256, Target.from_field(line.astype(float), _dilate(line, 3)), budget=Budget(1), rng=Rng(1))


def test_deterministic_and_validation(setup256, grid10):
    t = shaped(setup256, "disc")
    a = m.run(setup256, t, budget=Budget(4), rng=Rng(5)).phi
    assert np.array_equal(a, m.run(setup256, t, budget=Budget(4), rng=Rng(5)).phi)
    with pytest.raises(ValueError, match="mixing"):
        m.run(setup256, t, budget=Budget(1), rng=Rng(1), mixing=0.0)
    with pytest.raises(ValueError, match="field"):
        m.run(setup256, Target.from_traps(grid10), budget=Budget(1), rng=Rng(1))
