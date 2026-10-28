"""The benchmark geometries G1 to G7 (algorithms D4.3 item 2) as params records, so the benchmark scores through exactly the
code the bake uses (``core/score.py``) and runs methods through ``stages/infer.py``.

Lengths are in Fourier units ``u = lambda f / (n_pix p)`` (one unit is ``pad`` focal bins). The benchmark optics keep ``u``
and the focal bin fixed across grids (``f`` scales with ``n_pix``), so a geometry means the same thing at 64, 128, 256 and
512 pixels. Grids: 256 for G1 to G5, 512 for G6, 128 for G7 (SDD). ``reduced`` shrinks counts and grids for the tests only.

- G1 square 10 x 10 at 8 u; G2 ring of 36 traps; G3 random 100 traps with at least 3 u between them; G4 quasi-periodic 119
  (cut-and-project of Z^5 to a five-fold set, scaled 7 u: the quasi-periodic set of Polin et al. is not published as
  coordinates, so this set is DinHot's own); G5 3D lattice 5 x 5 x 3 at 8 u in the plane and 8 um between planes;
  G6 large arrays, two targets pooled (the benchmark schema holds one geometry id per row, as for G7): seed ``s`` runs the
  32 x 32 = 1024 lattice at 6 u when ``s`` is even and the disordered 819 set of Kim et al. 2019 (traps on integer bins at
  least 5 bins apart, ``cases.library.disordered_set``, DinHot's own draw: the coordinates are not published) when odd; G7 shaped fields, four targets pooled (seed ``s`` runs shape ``s mod 4``): ring, disc,
  line, Laguerre-Gaussian ring.
"""
from __future__ import annotations

import math

import numpy as np

from ..cases.library import DISORDERED_819, disordered_set
from ..model.holo.core import traps as T
from ..model.holo.core.rng import Rng

SHAPES = ("ring", "disc", "line", "lg_ring")
GEOMETRY_SEED = 20261028
GEOMETRIES = {
    "G1": ({"en": "Square 10 x 10", "es": "Cuadrada 10 x 10"}, 100, 2),
    "G2": ({"en": "Ring of 36 traps", "es": "Anillo de 36 trampas"}, 36, 2),
    "G3": ({"en": "Random 100 traps", "es": "100 trampas aleatorias"}, 100, 2),
    "G4": ({"en": "Quasi-periodic 119", "es": "Cuasiperiódica 119"}, 119, 2),
    "G5": ({"en": "3D lattice 5 x 5 x 3", "es": "Red 3D 5 x 5 x 3"}, 75, 3),
    "G6": ({"en": "Large: 32 x 32 and disordered 819", "es": "Grande: 32 x 32 y desordenada de 819"}, 1024, 2),
    "G7": ({"en": "Shaped fields (ring, disc, line, LG ring)", "es": "Campos con forma (anillo, disco, línea, anillo LG)"}, 0, 2),
}
FULL_GRID = {"G1": 256, "G2": 256, "G3": 256, "G4": 256, "G5": 256, "G6": 512, "G7": 128}
DEVICE = {"bit_depth": 4, "crosstalk": {"sigma_per_px": 1.24, "q": 1.8}, "upsample": 3, "fill_factor": 0.85,
          "flicker_rad": 0.05, "lut_gamma": 1.0}   # the C08 device


def setup_record(n_pix: int) -> dict:
    """The benchmark optics: 850 nm, pitch 20 um, ``f`` scaled with ``n_pix`` so that ``u`` is 0.996 um at every grid."""
    return {"wavelength_nm": 850, "focal_mm": 6 * n_pix / 256, "na": 0.5, "n_imm": 1.0, "n_pix": n_pix, "pitch_um": 20,
            "pad": 2, "beam": {"kind": "gaussian", "waist_frac": 1.0}}


def unit_um(n_pix: int) -> float:
    s = setup_record(n_pix)
    return s["wavelength_nm"] * 1e-9 * s["focal_mm"] * 1e-3 / (n_pix * s["pitch_um"] * 1e-6) * 1e6


def _records(ts: T.TrapSet) -> list[dict]:
    return [{"id": int(t.id), "x_um": round(t.x_m * 1e6, 4) + 0.0, "y_um": round(t.y_m * 1e6, 4) + 0.0,
             "z_um": round(t.z_m * 1e6, 4) + 0.0, "weight": 1.0, "charge": 0} for t in ts]


def quasi_periodic(n: int, spacing_um: float) -> T.TrapSet:
    """The ``n`` points nearest the centre of a five-fold cut-and-project set (Z^5 projected to the plane, accepted when the
    perpendicular-space image lies in a disc of radius 1.3), scaled so the typical spacing is ``spacing_um``."""
    e = [(math.cos(2 * math.pi * k / 5), math.sin(2 * math.pi * k / 5)) for k in range(5)]
    ep = [(math.cos(4 * math.pi * k / 5), math.sin(4 * math.pi * k / 5)) for k in range(5)]
    pts: dict[tuple[int, int], tuple[float, float]] = {}
    rng = range(-5, 6)
    for n0 in rng:
        for n1 in rng:
            for n2 in rng:
                for n3 in rng:
                    for n4 in (-2, -1, 0, 1, 2):
                        ns = (n0, n1, n2, n3, n4)
                        px, py = sum(a * b[0] for a, b in zip(ns, ep)), sum(a * b[1] for a, b in zip(ns, ep))
                        if px * px + py * py <= 1.3**2:
                            x, y = sum(a * b[0] for a, b in zip(ns, e)), sum(a * b[1] for a, b in zip(ns, e))
                            pts[(round(x * 1e4), round(y * 1e4))] = (x, y)
    ordered = sorted(pts.values(), key=lambda p: (round(math.hypot(*p), 6), round(math.atan2(p[1], p[0]) % (2 * math.pi), 6)))
    ordered = ordered[:n]
    if len(ordered) < n:
        raise ValueError(f"the cut-and-project window gave {len(ordered)} points, {n} needed")
    d = min(math.dist(a, b) for i, a in enumerate(ordered) for b in ordered[:i])
    s = spacing_um / d
    return T.TrapSet(T.Trap(i, p[0] * s * 1e-6, p[1] * s * 1e-6) for i, p in enumerate(ordered))


def _shape_target(shape: str, n_pix: int) -> dict:
    s = n_pix / 128
    u = unit_um(n_pix)
    if shape == "ring":
        return {"kind": "shaped", "shape": "ring", "radius_um": round(24 * u * s, 4), "width_um": round(6 * u * s, 4),
                "signal_margin_bins": 3}
    if shape == "disc":
        return {"kind": "shaped", "shape": "disc", "radius_um": round(14 * u * s, 4), "signal_margin_bins": 3}
    if shape == "line":
        return {"kind": "shaped", "shape": "line", "length_um": round(60 * u * s, 4), "width_um": round(4 * u * s, 4),
                "signal_margin_bins": 3}
    return {"kind": "shaped", "shape": "lg_ring", "radius_um": round(20 * u * s, 4), "width_um": round(6 * u * s, 4),
            "signal_margin_bins": 3}


def grid_of(geometry: str, reduced: bool) -> int:
    return 64 if reduced else FULL_GRID[geometry]


def record(geometry: str, *, device: bool, seed: int, reduced: bool = False, shape: str | None = None) -> dict:
    """The params record of one benchmark cell input (the budget is overwritten by the runner per run)."""
    n_pix = grid_of(geometry, reduced)
    u = unit_um(n_pix)
    small = reduced
    if geometry == "G1":
        n, sp = (4, 4) if small else (10, 8)
        traps = _records(T.square_grid(n, n, sp * u))
    elif geometry == "G2":
        traps = _records(T.ring(12 if small else 36, (4 if small else 34) * u))
    elif geometry == "G3":
        n, ext, mn = (12, 24, 3) if small else (100, 90, 3)
        traps = _records(T.random_min_spacing(n, ext * u, mn * u, Rng(GEOMETRY_SEED + 3)))
    elif geometry == "G4":
        traps = _records(quasi_periodic(19 if small else 119, (3 if small else 7) * u))
    elif geometry == "G5":
        n, sp = (2, 4) if small else (5, 8)
        traps = _records(T.lattice_3d(n, n, 3, sp * u, 8.0))
    elif geometry == "G6":
        n, sp = (6, 3) if small else (32, 6)
        if seed % 2 == 1:     # the disordered set (the lattice is the even seeds)
            kw = dict(n=20, half_bins=12, min_bins=3, seed=GEOMETRY_SEED + 819) if small else dict(DISORDERED_819)
            traps = disordered_set(s=setup_record(n_pix), **kw)
        else:
            traps = _records(T.square_grid(n, n, sp * u))
    elif geometry == "G7":
        target = _shape_target(shape or SHAPES[seed % 4], n_pix)
        traps = None
    else:
        raise KeyError(f"unknown geometry {geometry!r}")
    if traps is not None:
        target = {"kind": "traps", "traps": traps}
    return {"case_id": f"BM_{geometry}", "setup": setup_record(n_pix), "device": DEVICE if device else None, "target": target,
            "aberration": None, "methods": ["M04"], "reference_method": "M04", "budget": {"iterations": 30, "time_s": None},
            "seed": seed, "feedback": None, "dynamics": None, "rearrangement": None, "expect": {"efficiency": [0.0, 1.0]}}


def n_traps(geometry: str, reduced: bool) -> int:
    rec = record(geometry, device=False, seed=0, reduced=reduced)
    return len(rec["target"]["traps"]) if rec["target"]["kind"] == "traps" else 0


def is_3d(geometry: str) -> bool:
    return GEOMETRIES[geometry][2] == 3


__all__ = ["GEOMETRIES", "SHAPES", "DEVICE", "record", "quasi_periodic", "setup_record", "unit_um", "np"]
