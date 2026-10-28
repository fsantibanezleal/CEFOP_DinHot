"""The held-out sets of the two slots, written once BEFORE any final training run and identified by the sha256 of their bytes
(the hash goes into the model card). Numpy only. A training run never reads these files; the training streams use other seeds.

cgh-net (``cgh-heldout.npz``): ``gen`` targets from a fresh seed, stratified over the seven target kinds, and ``bench`` targets
rendered from the benchmark geometries G1, G2, G3, G4, G6 (point traps, one unit ``u`` is one bin at pad 1; a geometry wider
than the crop is scaled to fit it) and the four shapes of G7 (sizes of ``benchmark.geometries._shape_target`` at 128 pixels).
G5 is a 3D lattice and has no meaning on one focal plane: it is not in this set.

warmstart-model (``warmstart-heldout.npz``): ``gen`` trap sets from a fresh seed that are DEMANDING: at least 40 traps and a
selection run of the random-start M07 (its own seed, not the evaluation seeds) needing more than 3 iterations to reach a
relative standard deviation of 1 percent. A sparse array reaches 1 percent at the first iteration from any start, so it cannot
show a warm start; the filter looks at the baseline only, never at a model. ``bench`` are G1 to G6 at the benchmark grids.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np

from ....benchmark import geometries as bg
from ..core.geometry import Setup, focal_bin_m
from ..core.rng import Rng
from ..core.types import Budget, Target
from . import convert, generators

CGH_SEED = 20269001
WARM_SEED = 20269002
WARM_SELECT_SEED = 20269003
CGH_GEN_PER_KIND = 30
WARM_GEN_N = 60
LEARNED_ENV = "DINHOT_LEARNED_DIR"   # <data root>/dinhot/learned on the training device; never a path written in the repo


def learned_root() -> Path:
    """The directory of the held-out files (datasets live in the data root, never in the repository)."""
    v = os.environ.get(LEARNED_ENV)
    if not v:
        raise RuntimeError(f"set {LEARNED_ENV} to the held-out directory (<data root>/dinhot/learned)")
    return Path(v)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _bench_setup(n_pix: int) -> Setup:
    r = bg.setup_record(n_pix)
    return Setup(wavelength_m=r["wavelength_nm"] * 1e-9, focal_m=r["focal_mm"] * 1e-3, na=r["na"], n_imm=r["n_imm"], n_pix=n_pix,
                 pitch_m=r["pitch_um"] * 1e-6, pad=r["pad"])


def bench_trap_sets() -> dict[str, tuple[np.ndarray, int]]:
    """``{G1..G6: (traps (M, 4) in bins and Rayleigh ranges, native n_pix)}`` from the benchmark geometry records."""
    out = {}
    for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
        rec = bg.record(g, device=False, seed=0)
        n = bg.grid_of(g, False)
        s = _bench_setup(n)
        b, zr = focal_bin_m(s), convert.rayleigh_range_m(s)
        arr = np.array([[t["x_um"] * 1e-6 / b, t["y_um"] * 1e-6 / b, t["z_um"] * 1e-6 / zr, t["weight"]] for t in rec["target"]["traps"]])
        out[g] = (arr, n)
    return out


def bench_targets() -> dict[str, np.ndarray]:
    """Unit-energy amplitudes of the benchmark geometries on the 128 x 128 crop (see the module docstring)."""
    out = {}
    for g in ("G1", "G2", "G3", "G4", "G6"):
        rec = bg.record(g, device=False, seed=0)
        n = bg.grid_of(g, False)
        u = bg.unit_um(n)
        xy = np.array([[t["x_um"] / u, t["y_um"] / u] for t in rec["target"]["traps"]])
        ext = np.abs(xy).max()
        if ext > 52.0:
            xy = xy * (52.0 / ext)
        out[g] = np.sqrt(generators.render_spots(xy, np.ones(len(xy)))).astype(np.float32)
    for shape in bg.SHAPES:
        rec = bg.record("G7", device=False, seed=0, shape=shape)["target"]
        p = {"radius": rec.get("radius_um", 0.0) / bg.unit_um(128), "width": rec.get("width_um", 0.0) / bg.unit_um(128),
             "length": rec.get("length_um", 0.0) / bg.unit_um(128)}
        out[f"G7_{shape}"] = np.sqrt(generators.shaped_intensity(shape, p)).astype(np.float32)
    return out


def build_cgh(path: Path) -> str:
    rng = np.random.default_rng(CGH_SEED)
    gen, kinds = [], []
    for kind in generators.SHAPE_KINDS:
        for _ in range(CGH_GEN_PER_KIND):
            gen.append(generators.sample_target(rng, kind))
            kinds.append(kind)
    bench = bench_targets()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, gen=np.stack(gen), gen_kind=np.array(kinds), bench=np.stack(list(bench.values())), bench_name=np.array(list(bench)),
             seed=np.array(CGH_SEED))
    return sha256_file(path)


def first_below(sig, thr: float = 1.0) -> int | None:
    for k, v in enumerate(sig):
        if v <= thr:
            return k + 1
    return None


def build_warm(path: Path, setup: Setup, select_budget: int = 40) -> str:
    from ..methods.baseline import m07_phase_fixed_wgs as m07
    rng = np.random.default_rng(WARM_SEED)
    keep, tried, n_sel = [], 0, 0
    while len(keep) < WARM_GEN_N and tried < 800:
        tried += 1
        arr = generators.sample_traps(rng, half_field=setup.n_fft / 2)
        if len(arr) < 40:
            continue
        n_sel += 1
        t, mk = generators.pad_batch([arr], convert.MAX_TRAPS)
        ts = convert.input_to_traps(setup, t, mk)
        r = m07.run(setup, Target.from_traps(ts), budget=Budget(select_budget), rng=Rng(WARM_SELECT_SEED + tried), form="point")
        it = first_below([h["rel_std"] for h in r.history])
        if it is None or it > 3:
            keep.append(arr)
    if len(keep) < WARM_GEN_N:
        raise RuntimeError(f"only {len(keep)} demanding geometries in {tried} draws")
    bench = bench_trap_sets()
    flat = np.zeros((WARM_GEN_N, convert.MAX_TRAPS, 4), dtype=np.float64)
    cnt = np.zeros(WARM_GEN_N, dtype=np.int64)
    for i, a in enumerate(keep):
        flat[i, : len(a)] = a
        cnt[i] = len(a)
    bflat = np.zeros((len(bench), convert.MAX_TRAPS, 4), dtype=np.float64)
    bcnt = np.zeros(len(bench), dtype=np.int64)
    for i, (arr, _n) in enumerate(bench.values()):
        bflat[i, : len(arr)] = arr
        bcnt[i] = len(arr)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, gen=flat, gen_count=cnt, bench=bflat, bench_count=bcnt, bench_name=np.array(list(bench)),
             bench_n_pix=np.array([n for _a, n in bench.values()]), seed=np.array(WARM_SEED), select_seed=np.array(WARM_SELECT_SEED),
             drawn=np.array(tried))
    return sha256_file(path)


def load_cgh(path: Path):
    z = np.load(path)
    return z["gen"], [str(k) for k in z["gen_kind"]], z["bench"], [str(k) for k in z["bench_name"]]


def load_warm(path: Path):
    """``(gen list of (M, 4) arrays, bench list of (name, (M, 4) array, n_pix))``."""
    z = np.load(path)
    gen = [z["gen"][i, : z["gen_count"][i]] for i in range(len(z["gen_count"]))]
    bench = [(str(z["bench_name"][i]), z["bench"][i, : z["bench_count"][i]], int(z["bench_n_pix"][i])) for i in range(len(z["bench_count"]))]
    return gen, bench


# ---------------------------------------------------------------------------------- cgh-net, three planes (volumes)
CGHVOL_SEED = 20269004
CGHVOL_GEN_PER_KIND = 40
MAX_VOLUME_TRAPS = 128


def _lattice_volume(k: int, spacing: float, shifts) -> tuple[np.ndarray, np.ndarray]:
    g = (np.arange(k) - (k - 1) / 2) * spacing
    base = np.stack(np.meshgrid(g, g), -1).reshape(-1, 2)
    planes = [np.rint(base + np.array(s)).astype(int) for s in shifts]
    amps = np.stack([np.sqrt(generators.render_spots(p.astype(np.float64), np.ones(len(p)))) for p in planes]).astype(np.float32)
    traps = np.concatenate([np.column_stack([p, np.full(len(p), generators.PLANE_INDEX[i]), np.ones(len(p))]) for i, p in enumerate(planes)])
    return amps, traps


def bench_volumes() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """The benchmark's 3D lattice G5 (5 x 5 x 3 at 8 units, planes without lateral shift) and the 5 x 5 three-plane layout of the
    M19 acceptance test (spacing 6 voxels, planes shifted laterally by (0, 0), (3, 3), (-3, 3))."""
    return {"G5_lattice": _lattice_volume(5, 8.0, [(0, 0)] * 3), "M19_three_plane": _lattice_volume(5, 6.0, [(0, 0), (3, 3), (-3, 3)])}


def build_cgh_vol(path: Path) -> str:
    rng = np.random.default_rng(CGHVOL_SEED)
    amps, traps, kinds = [], [], []
    for kind in generators.VOLUME_KINDS:
        for _ in range(CGHVOL_GEN_PER_KIND):
            a, t = generators.sample_volume(rng, kind)
            amps.append(a), traps.append(t), kinds.append(kind)
    bench = bench_volumes()
    for name, (a, t) in bench.items():
        amps.append(a), traps.append(t), kinds.append("bench/" + name)
    tr = np.zeros((len(traps), MAX_VOLUME_TRAPS, 4))
    cnt = np.zeros(len(traps), dtype=np.int64)
    for i, t in enumerate(traps):
        tr[i, : len(t)], cnt[i] = t, len(t)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, amps=np.stack(amps), traps=tr, count=cnt, kind=np.array(kinds), seed=np.array(CGHVOL_SEED))
    return sha256_file(path)


def load_cgh_vol(path: Path):
    """``(amps (n, 3, 128, 128), traps list of (m, 4) arrays, kinds list)``."""
    z = np.load(path)
    return z["amps"], [z["traps"][i, : z["count"][i]] for i in range(len(z["count"]))], [str(k) for k in z["kind"]]
