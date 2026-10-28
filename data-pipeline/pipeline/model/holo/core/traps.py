"""Trap descriptions, generators and the field-of-view check.

A trap is a point in the focal volume: position (x, y, z) in metres, a target weight and an optical vortex charge
(algorithms D1.0: orbital angular momentum is an extra term ``l atan2(y_j, x_j)`` in the delay).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .geometry import Setup, focal_bin_m, half_field_m
from .rng import Rng


class OutOfFieldError(ValueError):
    """A trap lies outside the unaliased field of view ``+-lambda f / (2 p)`` (case C11)."""

    def __init__(self, trap_id: int, bound_m: float, value_m: float, axis: str):
        self.trap_id, self.bound_m, self.value_m, self.axis = trap_id, bound_m, value_m, axis
        super().__init__(
            f"trap {trap_id} has {axis} = {value_m:.3e} m, outside the unaliased field of view "
            f"(bound = {bound_m:.3e} m = lambda f / (2 p))"
        )


@dataclass(frozen=True)
class Trap:
    id: int
    x_m: float
    y_m: float
    z_m: float = 0.0
    weight: float = 1.0
    charge: int = 0


class TrapSet:
    """A validated tuple of traps with array views (``ids, x_m, y_m, z_m, weight, charge``)."""

    def __init__(self, traps):
        traps = tuple(traps)
        if not traps:
            raise ValueError("a trap set needs at least one trap")
        ids = [t.id for t in traps]
        if len(set(ids)) != len(ids):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate trap ids: {dup}")
        for t in traps:
            if not all(math.isfinite(v) for v in (t.x_m, t.y_m, t.z_m, t.weight)):
                raise ValueError(f"trap {t.id}: position and weight must be finite")
            if t.weight <= 0:
                raise ValueError(f"trap {t.id}: weight must be positive, got {t.weight}")
            if int(t.charge) != t.charge:
                raise ValueError(f"trap {t.id}: charge must be an integer")
        self.traps = traps
        self.ids = np.array(ids, dtype=np.int64)
        self.x_m = np.array([t.x_m for t in traps], dtype=np.float64)
        self.y_m = np.array([t.y_m for t in traps], dtype=np.float64)
        self.z_m = np.array([t.z_m for t in traps], dtype=np.float64)
        self.weight = np.array([t.weight for t in traps], dtype=np.float64)
        self.charge = np.array([int(t.charge) for t in traps], dtype=np.int64)

    def __len__(self) -> int:
        return len(self.traps)

    def __iter__(self):
        return iter(self.traps)


def _centred(xs: np.ndarray, ys: np.ndarray, zs=None) -> TrapSet:
    zs = np.zeros_like(xs) if zs is None else zs
    return TrapSet(Trap(i, float(x), float(y), float(z)) for i, (x, y, z) in enumerate(zip(xs, ys, zs)))


def _count(name: str, n) -> int:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError(f"{name} must be a positive integer, got {n!r}")
    return int(n)


def _pos(name: str, v: float) -> float:
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} must be finite and positive, got {v!r}")
    return float(v)


def square_grid(nx: int, ny: int, spacing_um: float) -> TrapSet:
    """``nx * ny`` traps on a square lattice centred on the axis, row-major ids."""
    nx, ny, s = _count("nx", nx), _count("ny", ny), _pos("spacing_um", spacing_um) * 1e-6
    gx, gy = np.meshgrid((np.arange(nx) - (nx - 1) / 2) * s, (np.arange(ny) - (ny - 1) / 2) * s)
    return _centred(gx.ravel(), gy.ravel())


def hex_lattice(n: int, spacing_um: float) -> TrapSet:
    """The ``n`` hexagonal-lattice sites nearest to the centre (centre first, then rings by angle)."""
    n, s = _count("n", n), _pos("spacing_um", spacing_um) * 1e-6
    r = int(math.ceil(math.sqrt(n))) + 2
    pts = []
    for a in range(-r, r + 1):
        for b in range(-r, r + 1):
            x, y = s * (a + 0.5 * b), s * (math.sqrt(3) / 2) * b
            pts.append((round(math.hypot(x, y) / s, 6), round(math.atan2(y, x) % (2 * math.pi), 6), x, y))
    pts.sort()
    pts = pts[:n]
    return _centred(np.array([p[2] for p in pts]), np.array([p[3] for p in pts]))


def ring(n: int, radius_um: float) -> TrapSet:
    """``n`` traps equally spaced on a circle of the given radius."""
    n, rad = _count("n", n), _pos("radius_um", radius_um) * 1e-6
    th = 2 * np.pi * np.arange(n) / n
    return _centred(rad * np.cos(th), rad * np.sin(th))


def random_min_spacing(n: int, extent_um: float, min_spacing_um: float, rng: Rng) -> TrapSet:
    """``n`` traps uniform in a square of side ``extent_um``, each at least ``min_spacing_um`` from the others.

    Rejection sampling through ``rng`` (uniform x then y per attempt); ``ValueError`` after 2000 attempts per trap.
    """
    n = _count("n", n)
    ext, mn = _pos("extent_um", extent_um) * 1e-6, _pos("min_spacing_um", min_spacing_um) * 1e-6
    pts: list[tuple[float, float]] = []
    attempts = 0
    while len(pts) < n:
        if attempts > 2000 * n:
            raise ValueError(f"cannot place {n} traps with spacing {min_spacing_um} um in {extent_um} um")
        attempts += 1
        x, y = (rng.uniform() - 0.5) * ext, (rng.uniform() - 0.5) * ext
        if all(math.hypot(x - px, y - py) >= mn for px, py in pts):
            pts.append((x, y))
    return _centred(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))


def lattice_3d(nx: int, ny: int, nz: int, spacing_um: float, dz_um: float) -> TrapSet:
    """A cubic-like lattice: square in x, y with ``spacing_um`` and ``nz`` planes ``dz_um`` apart, centred."""
    nx, ny, nz = _count("nx", nx), _count("ny", ny), _count("nz", nz)
    s, dz = _pos("spacing_um", spacing_um) * 1e-6, _pos("dz_um", dz_um) * 1e-6
    gz, gy, gx = np.meshgrid(
        (np.arange(nz) - (nz - 1) / 2) * dz, (np.arange(ny) - (ny - 1) / 2) * s, (np.arange(nx) - (nx - 1) / 2) * s,
        indexing="ij",
    )
    return _centred(gx.ravel(), gy.ravel(), gz.ravel())


def snap_to_bins(setup: Setup, traps: TrapSet) -> TrapSet:
    """Move each trap in x, y to the nearest FFT bin (z, weight and charge unchanged)."""
    b = focal_bin_m(setup)
    return TrapSet(replace(t, x_m=round(t.x_m / b) * b, y_m=round(t.y_m / b) * b) for t in traps)


def check_in_field(setup: Setup, traps: TrapSet) -> None:
    """Raise ``OutOfFieldError`` (naming the first offending trap id and the bound) if any |x| or |y| >= bound.

    The bound is ``half_field_m(setup)``; the bin at the bound itself is outside the centred FFT grid.
    """
    bound = half_field_m(setup)
    for t in traps:
        for axis, v in (("x", t.x_m), ("y", t.y_m)):
            if abs(v) >= bound:
                raise OutOfFieldError(t.id, bound, v, axis)
