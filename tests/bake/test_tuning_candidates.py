"""Every tuning candidate of the benchmark is a valid call of its method: it runs on a small task and returns finite metrics."""
import math
import sys

import numpy as np
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.benchmark import protocol  # noqa: E402
from pipeline.model.holo import methods  # noqa: E402
from pipeline.model.holo.core.geometry import Setup  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import square_grid, snap_to_bins  # noqa: E402
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402

CANDIDATES = [(mid, kw) for mid, grid in sorted(protocol.FALLBACK_TUNING.items()) for kw in grid]


@pytest.mark.parametrize("mid,kw", CANDIDATES, ids=[f"{m}-{i}" for i, (m, _) in enumerate(CANDIDATES)])
def test_every_fallback_tuning_candidate_runs(mid, kw):
    setup = Setup(wavelength_m=1.064e-6, focal_m=0.2, na=0.5, n_imm=1.0, n_pix=64, pitch_m=12.5e-6, pad=2,
                  beam="flat", waist_frac=1.0)
    method = methods.get(mid)
    if "traps" in method.spec.targets:
        traps = snap_to_bins(setup, square_grid(3, 3, spacing_um=8 * 1.064e-6 * 0.2 / (128 * 12.5e-6) * 1e6))
        target = Target(traps=traps)
    else:  # a shaped field: a disc of radius 10 bins on the 128 x 128 FFT grid
        y, x = np.mgrid[-64:64, -64:64]
        disc = (x ** 2 + y ** 2 <= 100).astype(float)
        target = Target(amplitude=disc, mask=(x ** 2 + y ** 2 <= 196))
    result = method.run(setup, target, budget=Budget(iterations=4, time_s=None), rng=Rng(7), **kw)
    last = result.history[-1]
    assert all(math.isfinite(v) for k, v in last.items() if isinstance(v, float))
