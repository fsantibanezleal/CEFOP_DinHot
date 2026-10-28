"""Shared helpers of the E3 optimization-method tests: setups, the 10x10 task, shaped targets, error measures.

Not a test module (no ``test_`` prefix). The grids follow the brief: traps on 256 x 256 pixels padded 2; shaped targets
on 128 x 128 (live size, 64 pixel SLM padded 2) and 256 x 256 (baked size, 128 pixel SLM padded 2) focal grids.
"""
from __future__ import annotations

import numpy as np

from pipeline.model.holo.core.forward import point_trap_fields
from pipeline.model.holo.core.geometry import Setup, focal_bin_m
from pipeline.model.holo.core.metrics import efficiency, rel_std, trap_intensities, uniformity
from pipeline.model.holo.core.traps import Trap, TrapSet, square_grid


def make_setup(n_pix: int = 256, pad: int = 2, beam: str = "gaussian") -> Setup:
    """The Hamamatsu-like setup of the SDD 10x10 task: 12.5 um pitch, f = 250 mm, 850 nm, Gaussian beam of waist 1."""
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=n_pix, pitch_m=12.5e-6, pad=pad,
                 beam=beam)


def task_10x10(setup: Setup) -> TrapSet:
    """10 x 10 square grid on FFT bins at 8 bins spacing, z = 0 (the SDD task)."""
    return square_grid(10, 10, 8 * focal_bin_m(setup) * 1e6)


def quasi_periodic_119(setup: Setup, bins_long: int = 9, bins_short: int = 6) -> TrapSet:
    """119 traps of a quasi-periodic set: the product of two Fibonacci chains (11 x 11 sites, two removed), on bins.

    A Fibonacci chain has two gap lengths in the golden-ratio sequence (substitution A -> AB, B -> A), so the set has
    no translation symmetry along either axis (like Polin et al. 2005's 119 quasi-periodic traps, whose exact
    geometry is not in the dossier).
    """
    word = "A"
    while len(word) < 10:
        word = "".join("AB" if c == "A" else "A" for c in word)
    gaps = [bins_long if c == "A" else bins_short for c in word[:10]]
    chain = np.concatenate([[0.0], np.cumsum(gaps)])
    chain -= chain.mean()
    b = focal_bin_m(setup)
    pts = [(x, y) for y in chain for x in chain]
    pts = pts[: len(pts) - 2]
    return TrapSet(Trap(i, float(x) * b, float(y) * b) for i, (x, y) in enumerate(pts))


def bin_grid(setup: Setup, nx: int, ny: int, spacing_bins: float) -> TrapSet:
    """``nx x ny`` square lattice with the given spacing in FFT bins of ``setup`` (traps on bins for integer spacing)."""
    return square_grid(nx, ny, spacing_bins * focal_bin_m(setup) * 1e6)


def trap_stats(phi: np.ndarray, setup: Setup, traps: TrapSet) -> tuple[float, float, float]:
    """Efficiency, uniformity (with the leading 1 minus) and relative standard deviation in percent, ideal device."""
    v = point_trap_fields(phi, setup, traps)
    return (efficiency(trap_intensities(v)), uniformity(trap_intensities(v, traps.weight)),
            rel_std(trap_intensities(v, traps.weight)))


# ---- shaped targets on the focal grid ------------------------------------------------------------------------

def _grid(setup: Setup):
    m = setup.n_fft
    k = np.arange(m) - m // 2
    return np.meshgrid(k, k)


def disc_target(setup: Setup, radius: float, guard: float = 3.0):
    """Flat-top disc of the given radius (bins); the signal region is the disc shrunk by ``guard`` bins."""
    x, y = _grid(setup)
    r = np.hypot(x, y)
    mask = r <= radius - guard
    return np.where(mask, 1.0, 0.0), mask


def ring_target(setup: Setup, radius: float, width: float, guard: float = 2.0):
    """Flat-top annulus of mean radius ``radius`` and full width ``width`` (bins), shrunk by ``guard`` at both edges."""
    x, y = _grid(setup)
    r = np.hypot(x, y)
    mask = np.abs(r - radius) <= width / 2 - guard
    return np.where(mask, 1.0, 0.0), mask


def line_target(setup: Setup, length: float, width: float, guard: float = 2.0):
    """Flat-top horizontal bar of ``length`` x ``width`` bins, shrunk by ``guard`` on every side."""
    x, y = _grid(setup)
    mask = (np.abs(x) <= length / 2 - guard) & (np.abs(y) <= width / 2 - guard)
    return np.where(mask, 1.0, 0.0), mask


def lattice_target(setup: Setup, n: int, spacing: float, radius: float):
    """``n x n`` flat-top spots of the given radius (bins) on a square lattice of the given spacing."""
    x, y = _grid(setup)
    mask = np.zeros_like(x, dtype=bool)
    c = (np.arange(n) - (n - 1) / 2) * spacing
    for cy in c:
        for cx in c:
            mask |= np.hypot(x - np.rint(cx), y - np.rint(cy)) <= radius
    return np.where(mask, 1.0, 0.0), mask


def signal_error(e: np.ndarray, amplitude: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    """Relative RMS error over the signal region (shape only: intensity and target each normalised to unit sum in
    the region; Schroff et al. 2023 epsilon, Pasienski and DeMarco 2008 eta) and the power fraction in the region
    (efficiency, with ``sum |E|^2 = n_pix^2`` by Parseval)."""
    inten = np.abs(e) ** 2
    reg = mask & (amplitude > 0)
    t = amplitude[reg] ** 2
    i = inten[reg]
    err = float(np.sqrt(np.mean(((i / i.sum() - t / t.sum()) / (t / t.sum())) ** 2)))
    n_pix2 = inten.sum()
    return err, float(i.sum() / n_pix2)


def check_finite_difference(fun_grad, x: np.ndarray, rng: np.random.Generator, n_dirs: int = 4, h: float = 1e-6):
    """Largest relative error between the analytic directional derivative and central finite differences."""
    worst = 0.0
    f0, g, *_ = fun_grad(x)
    for _ in range(n_dirs):
        d = rng.standard_normal(x.shape)
        d /= np.linalg.norm(d)
        num = (fun_grad(x + h * d)[0] - fun_grad(x - h * d)[0]) / (2 * h)
        ana = float(np.sum(g * d))
        worst = max(worst, abs(num - ana) / max(abs(num), abs(ana), 1e-300))
    return worst

