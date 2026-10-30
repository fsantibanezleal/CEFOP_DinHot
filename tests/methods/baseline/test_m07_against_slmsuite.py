"""M07 against slmsuite's WGS-Kim from the same start (ADR-0069: the state of the art replicated, never weaker than its source).

Needs ``slmsuite`` (0.5.0), which only the notebook venv has: run it there,

    E:/_venvs/CEFOP_DinHot-notebooks/Scripts/python.exe -m pytest tests/methods/baseline/test_m07_against_slmsuite.py

In the pipeline venv the module is skipped. The comparison is made under one definition:

- same start: both codes get the same SLM phase (``init=`` for M07, ``reset_phase(custom_phase=)`` for slmsuite);
- same target (case C03, 1024 traps on bins), grid, padding and Gaussian beam, 30 iterations, phase fixed after 12;
- same metric: DinHot's ``core.metrics`` applied to both final phases through the same FFT read-out;
- same weighting exponent: Kim et al. use the ratio of the mean to the amplitude (exponent 1), M07's rule. slmsuite's
  default ``feedback_exponent`` is 0.8 (its Leonardo form), so the reference is run with ``feedback_exponent=1``.

The defect this test pins (found 2026-10-28, review A of notebook 03-03): M07 applied a weight update to the very first
field, while Kim's $g_0 = 1$ (and slmsuite's iteration 0) leaves the first projection unweighted.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

slmsuite = pytest.importorskip("slmsuite", reason="slmsuite lives in the notebook venv only")

from pipeline.cases.build import setup_of, target_of  # noqa: E402
from pipeline.io.contract import read_cases  # noqa: E402
from pipeline.model.holo.core import forward, geometry, metrics  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.types import Budget  # noqa: E402
from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs as m07  # noqa: E402
from slmsuite.holography.algorithms import SpotHologram  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]

ITERATIONS, N_FIX, SEEDS = 30, 12, 4


@pytest.fixture(scope="module")
def case():
    rec = {r["case_id"]: r for r in read_cases(ROOT / "data" / "examples" / "cases.json")}["C03_large_array"]
    return rec, setup_of(rec), target_of(rec).traps


def _numbers(phi, setup, traps):
    v = forward.trap_fields_from_fft(forward.fft_focal_field(phi, setup), setup, traps)
    i = metrics.trap_intensities(v)
    return metrics.efficiency(i), metrics.uniformity(i), metrics.rel_std(i)


def _slmsuite(start, setup, traps, exponent):
    slmsuite.configure_logging(None)
    iy, ix = forward.trap_bins(setup, traps)
    holo = SpotHologram(shape=(setup.n_fft, setup.n_fft), spot_vectors=np.vstack([ix, iy]), basis="knm",
                        spot_amp=np.ones(len(traps)), cameraslm=None, slm_shape=(setup.n_pix, setup.n_pix),
                        amp=geometry.input_amplitude(setup))
    holo.reset_phase(custom_phase=start)
    holo.optimize(method="WGS-Kim", maxiter=ITERATIONS, verbose=False, fix_phase_iteration=N_FIX,
                  feedback_exponent=exponent)
    return _numbers(np.array(holo.get_phase(), dtype=float), setup, traps)


def _dinhot(start, setup, traps, seed):
    from pipeline.model.holo.core.types import Target
    res = m07.run(setup, Target.from_traps(traps), budget=Budget(ITERATIONS), rng=Rng(seed), init=start, n_fix=N_FIX)
    return _numbers(res.phi, setup, traps)


def test_m07_matches_slmsuite_wgs_kim_from_the_same_start(case):
    """4 seeds: M07's final efficiency, uniformity and relative spread agree with WGS-Kim's (exponent 1) to rounding of the
    two FFT paths, far inside the spread between seeds."""
    rec, setup, traps = case
    pairs = []
    for seed in range(rec["seed"], rec["seed"] + SEEDS):
        start = np.random.default_rng(seed).uniform(-np.pi, np.pi, (setup.n_pix, setup.n_pix))
        pairs.append((_dinhot(start, setup, traps, seed), _slmsuite(start, setup, traps, 1.0)))
    ours = np.array([p[0] for p in pairs])
    ref = np.array([p[1] for p in pairs])
    seed_spread = float(np.ptp(ref[:, 2]))
    assert seed_spread > 0.05, "the seeds must differ for the comparison to mean anything"
    assert np.abs(ours[:, 2] - ref[:, 2]).max() < 0.01, (ours[:, 2], ref[:, 2])        # percent, on a spread of 0.2 to 0.4
    assert np.abs(ours[:, 0] - ref[:, 0]).max() < 1e-3, (ours[:, 0], ref[:, 0])
    assert np.abs(ours[:, 1] - ref[:, 1]).max() < 1e-2, (ours[:, 1], ref[:, 1])
    # the review's criterion: M07 does not end above slmsuite beyond the seed spread, in any pair
    assert np.all(ours[:, 2] <= ref[:, 2] + seed_spread / 10)


def test_slmsuite_default_exponent_is_not_m07_s(case):
    """The other half of the definition: at slmsuite's default exponent 0.8 the reference is a different method, so a
    comparison at the defaults would not test the replication (the runs differ in at least one pair by over 0.01)."""
    rec, setup, traps = case
    seed = rec["seed"]
    start = np.random.default_rng(seed).uniform(-np.pi, np.pi, (setup.n_pix, setup.n_pix))
    a, b = _slmsuite(start, setup, traps, 0.8), _slmsuite(start, setup, traps, 1.0)
    assert abs(a[2] - b[2]) > 0.01
