"""Shared fixtures of the method acceptance tests: the live grid of the SDD (256 x 256 pixels padded 2) and the 10x10 task."""
from __future__ import annotations

import numpy as np
import pytest

from pipeline.model.holo.core.forward import point_trap_fields
from pipeline.model.holo.core.geometry import Setup, focal_bin_m
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities, uniformity
from pipeline.model.holo.core.traps import square_grid


@pytest.fixture(scope="session")
def setup256() -> Setup:
    """The live grid: 256 x 256 SLM pixels, padding 2 (FFT grid 512 x 512), Gaussian beam of the core default."""
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)


@pytest.fixture(scope="session")
def grid10(setup256):
    """The 10x10 task: a square grid with traps on FFT bins, 8 bins apart, z = 0."""
    return square_grid(10, 10, 8 * focal_bin_m(setup256) * 1e6)


@pytest.fixture(scope="session")
def evaluate(setup256):
    """``evaluate(phi, traps) -> (efficiency, uniformity, rel_std_percent)`` by the point-trap form."""

    def _eval(phi, traps):
        i = trap_intensities(point_trap_fields(np.asarray(phi), setup256, traps))
        return efficiency(i), uniformity(i), rel_std(i)

    return _eval
