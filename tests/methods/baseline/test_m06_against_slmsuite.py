"""M06 against slmsuite's WGS-Leonardo from the same start (ADR-0069: the state of the art replicated, never weaker than its source).

Needs ``slmsuite`` (0.5.0), which only the notebook venv has: run it there,

    E:/_venvs/CEFOP_DinHot-notebooks/Scripts/python.exe -m pytest tests/methods/baseline/test_m06_against_slmsuite.py

In the pipeline venv the module is skipped. The comparison is made under the definition of ``test_m07_against_slmsuite.py``:
same start (``init=`` for M06, ``reset_phase(custom_phase=)`` for slmsuite), case C03 (1024 traps on bins), the same grid,
padding and Gaussian beam, 30 iterations, DinHot's ``core.metrics`` on both final phases, and the weighting exponent 1 of
Di Leonardo et al. 2007 (slmsuite's default ``feedback_exponent`` is 0.8).

The defect this test pins (found 2026-10-29, after the same one in M07): M06 updated the weights with the field of the start
hologram, while slmsuite's WGS-Leonardo projects that field with the initial weights. Measured before the fix, from the same
start: M06 ended at a relative spread of 1.4487, 1.7529, 1.3376 and 1.3494 percent against slmsuite's 1.4228, 1.4357, 1.4256
and 1.3724 on the four seeds; after it, the two agree to four digits.
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
from pipeline.model.holo.core.types import Budget, Target  # noqa: E402
from pipeline.model.holo.methods.baseline import m06_gsw as m06  # noqa: E402
from slmsuite.holography.algorithms import SpotHologram  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]

ITERATIONS, SEEDS = 30, 4


@pytest.fixture(scope="module")
def case():
    rec = {r["case_id"]: r for r in read_cases(ROOT / "data" / "examples" / "cases.json")}["C03_large_array"]
    return rec, setup_of(rec), target_of(rec).traps


def _numbers(phi, setup, traps):
    v = forward.trap_fields_from_fft(forward.fft_focal_field(phi, setup), setup, traps)
    i = metrics.trap_intensities(v)
    return metrics.efficiency(i), metrics.uniformity(i), metrics.rel_std(i)


def _slmsuite(start, setup, traps):
    slmsuite.configure_logging(None)
    iy, ix = forward.trap_bins(setup, traps)
    holo = SpotHologram(shape=(setup.n_fft, setup.n_fft), spot_vectors=np.vstack([ix, iy]), basis="knm",
                        spot_amp=np.ones(len(traps)), cameraslm=None, slm_shape=(setup.n_pix, setup.n_pix),
                        amp=geometry.input_amplitude(setup))
    holo.reset_phase(custom_phase=start)
    holo.optimize(method="WGS-Leonardo", maxiter=ITERATIONS, verbose=False, feedback_exponent=1.0)
    return _numbers(np.array(holo.get_phase(), dtype=float), setup, traps)


def test_m06_matches_slmsuite_wgs_leonardo_from_the_same_start(case):
    rec, setup, traps = case
    ours, ref = [], []
    for seed in range(rec["seed"], rec["seed"] + SEEDS):
        start = np.random.default_rng(seed).uniform(-np.pi, np.pi, (setup.n_pix, setup.n_pix))
        res = m06.run(setup, Target.from_traps(traps), budget=Budget(ITERATIONS), rng=Rng(seed), init=start, form="fft")
        ours.append(_numbers(res.phi, setup, traps))
        ref.append(_slmsuite(start, setup, traps))
    ours, ref = np.array(ours), np.array(ref)
    assert float(np.ptp(ref[:, 2])) > 0.03, "the seeds must differ for the comparison to mean anything"
    assert np.abs(ours[:, 2] - ref[:, 2]).max() < 0.005, (ours[:, 2], ref[:, 2])     # percent, on a spread near 1.4
    assert np.abs(ours[:, 0] - ref[:, 0]).max() < 1e-3, (ours[:, 0], ref[:, 0])
    assert np.abs(ours[:, 1] - ref[:, 1]).max() < 1e-2, (ours[:, 1], ref[:, 1])
