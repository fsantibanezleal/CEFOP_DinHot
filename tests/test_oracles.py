"""The physics oracles (data-pipeline/pipeline/oracles.py): closed relations the engine is checked against, shared by tests and
notebooks. The oracle shares no code with the engine; the tests pin it to the relations themselves and then hold the engine to it."""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline import oracles  # noqa: E402
from pipeline.model.holo.core import dynamics, trapphys  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402


def test_corner_frequency_and_drag_known_values() -> None:
    gamma = oracles.stokes_drag_ns_per_m(0.00089, 0.5e-6)
    assert gamma == pytest.approx(8.39e-9, rel=1e-2)
    assert oracles.corner_frequency_hz(1e-5, gamma) == pytest.approx(1e-5 / (2 * math.pi * gamma))
    with pytest.raises(ValueError):
        oracles.corner_frequency_hz(0.0, gamma)


def test_equipartition_variance() -> None:
    assert oracles.equipartition_variance_m2(1e-5, 295.0) == pytest.approx(4.073e-16, rel=1e-3)


def test_random_mask_and_vortex_relations() -> None:
    assert oracles.random_mask_efficiency(100) == 0.01
    assert oracles.vortex_winding_rad(8) == pytest.approx(16 * math.pi)
    with pytest.raises(ValueError):
        oracles.random_mask_efficiency(0)


def test_parseval_oracle_on_a_unitary_transform() -> None:
    x = np.random.default_rng(3).normal(size=64) + 1j * np.random.default_rng(4).normal(size=64)
    assert oracles.parseval_power(np.fft.fft(x, norm="ortho")) == pytest.approx(oracles.parseval_power(x), rel=1e-12)


def test_published_calibration_rows_are_the_quoted_ones() -> None:
    assert oracles.DI_LEONARDO_2007["M04"] == (0.94, 0.60) and oracles.DI_LEONARDO_2007["M06"] == (0.93, 0.99)


def test_the_engine_bead_meets_the_corner_frequency_oracle() -> None:
    kappa = 1e-5
    gamma = oracles.stokes_drag_ns_per_m(0.00089, 0.5e-6)
    n = 41
    ax = (np.arange(n) - n // 2) * 1e-7
    xx, yy = np.meshgrid(ax, ax)
    sigma = 5e-7
    imap = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    depth = kappa * sigma**2
    fc = oracles.corner_frequency_hz(kappa, gamma)
    dt = 1.0 / (2 * math.pi * fc) / 40
    traj = dynamics.bead_trajectory(imap, (ax, ax), dynamics.BeadParams(depth, gamma, 295.0), 2**17, dt, Rng(5))
    f, p = dynamics.psd(traj[:, 0], dt, 64)
    keep = f <= 5 * fc
    fit, _ = dynamics.fit_lorentzian(f[keep], p[keep])
    assert fit == pytest.approx(fc, rel=0.12)
    assert np.var(traj[:, 0]) == pytest.approx(oracles.equipartition_variance_m2(kappa, 295.0), rel=0.15)
    assert trapphys.KB_J_PER_K == oracles.KB_J_PER_K


def test_the_oracle_shares_no_code_with_the_engine() -> None:
    tree = ast.parse((ROOT / "data-pipeline" / "pipeline" / "oracles.py").read_text(encoding="utf-8"))
    imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("model" in m or m.startswith("pipeline") for m in imported), imported
