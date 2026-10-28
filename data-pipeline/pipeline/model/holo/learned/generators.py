"""Seeded generators of the training and held-out data of the two slots (numpy; offline). Every function takes a
``numpy.random.Generator`` built from a recorded seed, so a dataset is its (seed, count) and reproduces bit for bit.

Trap sets (warmstart-model), coordinates in focal bins and Rayleigh ranges (``torch_forward``): square lattices, hexagonal
lattices, rings, random sets with a minimum spacing, 3D stacks of planes and random 3D sets, with optional position jitter
and random weights. The quasi-periodic family is NOT generated for training: the benchmark geometry G4 is then a family the
model never saw.

Targets (cgh-net): unit-energy amplitudes on the 128 x 128 focal crop (pad 1, so one bin is one resolution cell): Gaussian
spot sets, rings, discs, lines, Laguerre-Gaussian rings, wide random blobs and thick strokes.
"""
from __future__ import annotations

import math

import numpy as np

CROP = 128
SPOT_SIGMA = 1.0

# ----------------------------------------------------------------- trap sets (warmstart-model)


def _grid(rng, half_field: float):
    span = 2 * (half_field - 8)
    sp = float(rng.uniform(3.0, 26.0))
    cap = int(span // sp) + 1
    nx = max(2, min(int(rng.integers(2, 33)), cap))
    ny = max(2, min(int(rng.integers(2, 33)), cap))
    gx, gy = np.meshgrid((np.arange(nx) - (nx - 1) / 2) * sp, (np.arange(ny) - (ny - 1) / 2) * sp)
    return np.stack([gx.ravel(), gy.ravel()], 1)


def _hex(rng, half_field: float):
    sp = float(rng.uniform(3.5, 24.0))
    n = int(rng.integers(3, 600))
    r = int(math.ceil(math.sqrt(n))) + 2
    pts = []
    for a in range(-r, r + 1):
        for b in range(-r, r + 1):
            x, y = sp * (a + 0.5 * b), sp * (math.sqrt(3) / 2) * b
            pts.append((math.hypot(x, y), x, y))
    pts.sort()
    arr = np.array([(p[1], p[2]) for p in pts[:n]])
    return arr[(np.abs(arr) <= half_field - 8).all(1)]


def _ring(rng, half_field: float):
    n = int(rng.integers(3, 200))
    rad = float(rng.uniform(max(4.0, n * 1.6 / (2 * math.pi)), half_field - 8))
    th = 2 * np.pi * np.arange(n) / n + rng.uniform(0, 2 * np.pi)
    out = np.stack([rad * np.cos(th), rad * np.sin(th)], 1)
    if rng.random() < 0.3:   # concentric second ring
        r2 = rad * float(rng.uniform(0.3, 0.8))
        n2 = max(3, int(n * r2 / rad))
        th2 = 2 * np.pi * np.arange(n2) / n2
        out = np.concatenate([out, np.stack([r2 * np.cos(th2), r2 * np.sin(th2)], 1)])
    return out


def _random(rng, half_field: float):
    n = int(rng.choice([4, 8, 16, 32, 64, 100, 150, 250, 400, 700, 1000]) * rng.uniform(0.7, 1.0))
    ext = float(rng.uniform(20.0, 2 * (half_field - 8)))
    mn = float(rng.uniform(2.5, 8.0))
    n = max(2, min(n, int(0.6 * (ext / mn) ** 2)))
    pts = np.empty((0, 2))
    tries = 0
    while len(pts) < n and tries < 40:   # batched dart throwing against the accepted set
        tries += 1
        for c in (rng.random((max(64, 4 * (n - len(pts))), 2)) - 0.5) * ext:
            if len(pts) >= n:
                break
            if len(pts) == 0 or np.min(np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1])) >= mn:
                pts = np.vstack([pts, c])
    return pts


def sample_traps(rng: np.random.Generator, half_field: float = 248.0, max_traps: int = 1024, family: str | None = None):
    """One trap set: float64 array ``(M, 4)`` of ``(kx, ky, Z, weight)``, 1 <= M <= ``max_traps``, all within the field."""
    fam = family or str(rng.choice(["grid", "hex", "ring", "random", "stack", "random3d"], p=[.25, .15, .15, .2, .15, .1]))
    z = None
    if fam == "stack":
        pts2 = [_grid, _hex, _random][int(rng.integers(0, 3))](rng, half_field)[: max(1, max_traps // 4)]
        nz = int(rng.integers(2, 5))
        dz = float(rng.uniform(1.5, 8.0))
        pts = np.concatenate([pts2] * nz)
        z = np.repeat((np.arange(nz) - (nz - 1) / 2) * dz, len(pts2))
    else:
        pts = {"grid": _grid, "hex": _hex, "ring": _ring, "random": _random, "random3d": _random}[fam](rng, half_field)
        if fam == "random3d":
            z = rng.uniform(-6.0, 6.0, len(pts))
    if len(pts) == 0:
        pts = np.zeros((1, 2))
    if rng.random() < 0.4:
        pts = pts + rng.normal(0, rng.uniform(0.05, 0.6), pts.shape)
    elif rng.random() < 0.5:
        pts = np.rint(pts)
    z = np.zeros(len(pts)) if z is None else np.asarray(z)
    if len(pts) > max_traps:
        sel = rng.permutation(len(pts))[:max_traps]
        pts, z = pts[sel], z[sel]
    keep = (np.abs(pts) < half_field - 2).all(1)
    pts, z = pts[keep], z[keep]
    if len(pts) == 0:
        pts, z = np.zeros((1, 2)), np.zeros(1)
    w = rng.uniform(0.5, 2.0, len(pts)) if rng.random() < 0.3 else np.ones(len(pts))
    perm = rng.permutation(len(pts))
    return np.concatenate([pts, z[:, None], w[:, None]], 1)[perm]


def pad_batch(sets: list[np.ndarray], m: int | None = None):
    """``(traps float32 (B, m, 4), mask float32 (B, m))`` zero-padded; ``m`` defaults to the largest set."""
    m = m or max(len(s) for s in sets)
    t = np.zeros((len(sets), m, 4), dtype=np.float32)
    k = np.zeros((len(sets), m), dtype=np.float32)
    for i, s in enumerate(sets):
        t[i, : len(s)] = s
        k[i, : len(s)] = 1.0
    return t, k


# ----------------------------------------------------------------- targets (cgh-net)

def _axes():
    c = np.arange(CROP) - CROP // 2
    return np.meshgrid(c, c)   # x, y; the centre bin (0, 0) at index 64, as the engine's focal grid


def render_spots(xy: np.ndarray, w: np.ndarray, sigma: float = SPOT_SIGMA) -> np.ndarray:
    """Unit-sum intensity of Gaussian spots at ``xy`` (bins, ``(M, 2)``) with weights ``w``."""
    c = np.arange(CROP) - CROP // 2
    gx = np.exp(-((c[None, :] - xy[:, :1]) ** 2) / (2 * sigma**2))
    gy = np.exp(-((c[None, :] - xy[:, 1:2]) ** 2) / (2 * sigma**2))
    t = (gy * w[:, None]).T @ gx
    return t / t.sum()


def shaped_intensity(shape: str, p: dict) -> np.ndarray:
    x, y = _axes()
    cx, cy = p.get("cx", 0.0), p.get("cy", 0.0)
    r = np.hypot(x - cx, y - cy)
    if shape == "ring":
        t = np.exp(-((r - p["radius"]) ** 2) / (2 * (p["width"] / 2.355) ** 2))
    elif shape == "disc":
        t = 1.0 / (1.0 + np.exp((r - p["radius"]) / 0.8))
    elif shape == "line":
        ca, sa = math.cos(p.get("angle", 0.0)), math.sin(p.get("angle", 0.0))
        u = (x - cx) * ca + (y - cy) * sa
        v = -(x - cx) * sa + (y - cy) * ca
        t = np.exp(-(v**2) / (2 * (p["width"] / 2.355) ** 2)) / (1.0 + np.exp((np.abs(u) - p["length"] / 2) / 0.8))
    elif shape == "lg_ring":
        th = np.arctan2(y - cy, x - cx)
        t = np.exp(-((r - p["radius"]) ** 2) / (2 * (p["width"] / 2.355) ** 2)) * np.cos(p.get("l", 3) * th / 2) ** 2
    elif shape == "blobs":
        t = np.zeros((CROP, CROP))
        for bx, by, s, a in p["blobs"]:
            t += a * np.exp(-((x - bx) ** 2 + (y - by) ** 2) / (2 * s**2))
    elif shape == "strokes":
        t = np.zeros((CROP, CROP))
        for x0, y0, x1, y1, wd in p["strokes"]:
            dx, dy = x1 - x0, y1 - y0
            s = np.clip(((x - x0) * dx + (y - y0) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
            d = np.hypot(x - (x0 + s * dx), y - (y0 + s * dy))
            t = np.maximum(t, np.exp(-(d**2) / (2 * (wd / 2.355) ** 2)))
    else:
        raise ValueError(shape)
    t = np.maximum(t, 0.0) + 1e-9
    return t / t.sum()


SHAPE_KINDS = ("spots", "ring", "disc", "line", "lg_ring", "blobs", "strokes")


def sample_target(rng: np.random.Generator, kind: str | None = None) -> np.ndarray:
    """One unit-energy amplitude ``(128, 128)`` float32 (``sum a^2 = 1``)."""
    kind = kind or str(rng.choice(SHAPE_KINDS, p=[.35, .1, .1, .1, .1, .12, .13]))
    lim = 50.0
    u = rng.uniform
    if kind == "spots":
        n = max(1, int(rng.choice([1, 2, 4, 9, 16, 25, 36, 64, 100, 150]) * u(0.7, 1.0)))
        fam = str(rng.choice(["grid", "ring", "random"]))
        if fam == "grid":
            k = max(1, int(round(math.sqrt(n))))
            sp = float(u(3.0, max(3.5, min(14.0, 2 * lim / max(k - 1, 1)))))
            gx, gy = np.meshgrid((np.arange(k) - (k - 1) / 2) * sp, (np.arange(k) - (k - 1) / 2) * sp)
            xy = np.stack([gx.ravel(), gy.ravel()], 1)
        elif fam == "ring":
            n = max(3, min(n, int(2 * math.pi * lim / 3.0)))
            rad = float(u(max(5.0, n * 3.0 / (2 * math.pi)), lim))
            th = 2 * np.pi * np.arange(n) / n
            xy = np.stack([rad * np.cos(th), rad * np.sin(th)], 1)
        else:
            xy = (rng.random((n, 2)) - 0.5) * 2 * lim
        xy = xy + rng.normal(0, 0.3, xy.shape)
        w = u(0.6, 1.6, len(xy)) if rng.random() < 0.3 else np.ones(len(xy))
        t = render_spots(xy, w)
    elif kind == "ring":
        t = shaped_intensity("ring", {"radius": u(8, 45), "width": u(3, 10), "cx": u(-8, 8), "cy": u(-8, 8)})
    elif kind == "disc":
        t = shaped_intensity("disc", {"radius": u(5, 30), "cx": u(-15, 15), "cy": u(-15, 15)})
    elif kind == "line":
        t = shaped_intensity("line", {"length": u(20, 90), "width": u(2.5, 7), "angle": u(0, np.pi), "cx": u(-10, 10), "cy": u(-10, 10)})
    elif kind == "lg_ring":
        t = shaped_intensity("lg_ring", {"radius": u(10, 40), "width": u(3, 10), "l": int(rng.integers(1, 7))})
    elif kind == "blobs":
        t = shaped_intensity("blobs", {"blobs": [(u(-40, 40), u(-40, 40), u(2.0, 9.0), u(0.4, 1.0)) for _ in range(int(rng.integers(1, 7)))]})
    else:
        t = shaped_intensity("strokes", {"strokes": [(u(-45, 45), u(-45, 45), u(-45, 45), u(-45, 45), u(2.5, 6)) for _ in range(int(rng.integers(1, 5)))]})
    return np.sqrt(t).astype(np.float32)
