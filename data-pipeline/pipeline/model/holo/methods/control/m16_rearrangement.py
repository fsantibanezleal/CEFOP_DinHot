r"""M16: rearrangement of trapped atoms: Hungarian assignment and linear phase interpolation (LPI).

Assignment (dossier D3.2, Lee, Kim and Ahn, Phys. Rev. A 95, 053424, https://doi.org/10.1103/PhysRevA.95.053424,
https://arxiv.org/abs/1704.07074): match each target site $t_i$ to a distinct loaded atom $a_{f(i)}$ minimising
$$C(f) = \sum_i d_{i,f(i)}^{\alpha},\qquad d_{i,j} = |t_i - a_j|$$
with $\alpha > 1$ (default 1.5, the paper value; for a square lattice $\alpha > 1.12$ keeps the minimum inter-atomic
distance of the lattice during moves) so that paths do not cross. ``hungarian`` is the Kuhn-Munkres algorithm with potentials
in numpy, $O(n^2 m)$ for an $n \times m$ cost with $n \le m$ (the rectangular case: more atoms than targets; the unmatched
atoms are released), tested against brute force for $n \le 7$. ``count_crossings`` counts pairs of straight paths that
intersect or overlap.

Hologram sequence (dossier D3.2, arXiv 2501.01391, linear phase interpolation, READ via HTML): compute the initial and final
phase-fixed weighted GS holograms (M07, FFT form on bins, point form otherwise; ``budget`` iterations each), extract each
tweezer's position, amplitude and optical phase $\psi_m = \arg V_m$ from them, interpolate linearly over $S$ steps
$$x_m(s) = x_m^{i} + \tfrac{s}{S}(x_m^{f} - x_m^{i}),\quad a_m(s) = a_m^{i} + \tfrac{s}{S}(a_m^{f} - a_m^{i}),\quad
\psi_m(s) = \psi_m^{i} + \tfrac{s}{S}\,\mathrm{wrap}(\psi_m^{f} - \psi_m^{i})$$
and invert the transform at each step: $\phi(s) = \arg \sum_m a_m(s) e^{i\psi_m(s)} e^{+i\Delta_j^m(s)}$ (the point-trap
back-projection, exact at fractional positions). $S$ is set by the longest path: $S = \lceil d_{max} / s_{max} \rceil$ with
``max_step_bins`` $s_{max}$ (default ``pad`` bins, one Fourier unit $\lambda f / (n_{pix} p)$). UNVERIFIED: the paper
gives the unit as $\lambda f/(mL)$ with $m \approx 0.41$ in prose, the equations above are the extraction's rendering of the
described procedure, and the wrapped phase difference (shortest phase path) is DinHot's reading of "interpolate linearly".
Because the amplitude is interpolated and the phase advances smoothly, no trap passes through zero intensity, unlike
independent weighted GS holograms whose free phases jump between steps (flicker; the paper: LPI stays above 70 percent).

Output: ``phi`` is the last frame; ``meta`` has ``frames`` ($(S+1) \times n \times n$), ``n_steps``, ``assignment`` (atom
index of each target), ``min_ratio`` (per trap: minimum over the steps of $I_m(s)$ divided by its mean over the steps, with
$V_m(s)$ the point-trap field of that frame at that step's positions), ``moved`` (traps with non-zero displacement),
``crossings``, ``trap_sequence`` (the ``TrapSet`` of each step). ``atoms`` (a ``TrapSet`` of loaded atom positions) is
required. Defaults: ``alpha=1.5``, ``max_step_bins=pad``, ``n_fix=12``.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ...core.forward import point_trap_backproject, point_trap_fields
from ...core.geometry import focal_bin_m
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, MethodSpec, Result, Target
from ..baseline import m07_phase_fixed_wgs
from ..baseline._common import Recorder, require_kinds

SPEC = MethodSpec(id="M16", name="Hungarian assignment and linear phase interpolation", family="control", lane="live",
                  targets=("traps",), dims=(2,))


def hungarian(cost: np.ndarray) -> tuple[list, float]:
    """Minimum-cost assignment of every row to a distinct column (``n <= m``): ``(column of each row, total cost)``."""
    a = np.asarray(cost, dtype=np.float64)
    if a.ndim != 2 or a.shape[0] > a.shape[1] or a.shape[0] == 0:
        raise ValueError(f"cost must be an n x m matrix with 1 <= n <= m, got shape {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError("cost must be finite")
    n, m = a.shape
    u = np.zeros(n + 1)
    v = np.zeros(m + 1)
    p = np.zeros(m + 1, dtype=np.int64)       # p[j]: row assigned to column j (1-based, 0 = free)
    way = np.zeros(m + 1, dtype=np.int64)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(m + 1, np.inf)
        used = np.zeros(m + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            free = ~used
            free[0] = False
            cur = np.full(m + 1, np.inf)
            cur[1:] = a[i0 - 1] - u[i0] - v[1:]
            upd = free & (cur < minv)
            minv[upd] = cur[upd]
            way[upd] = j0
            cand = np.where(free, minv, np.inf)
            j1 = int(np.argmin(cand))
            delta = cand[j1]
            u[p[used]] += delta
            v[used] -= delta
            minv[free] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = int(way[j0])
            p[j0] = p[j1]
            j0 = j1
    cols = [0] * n
    for j in range(1, m + 1):
        if p[j]:
            cols[p[j] - 1] = j - 1
    return cols, float(sum(a[i, c] for i, c in enumerate(cols)))


def assign(targets_xy: np.ndarray, atoms_xy: np.ndarray, alpha: float = 1.5) -> list:
    """Atom index of every target by the Hungarian algorithm on the cost $d^\\alpha$ (positions in any one unit)."""
    if not (math.isfinite(alpha) and alpha > 0):
        raise ValueError(f"alpha must be finite and positive, got {alpha!r}")
    t, a = np.asarray(targets_xy, float), np.asarray(atoms_xy, float)
    d = np.hypot(t[:, None, 0] - a[None, :, 0], t[:, None, 1] - a[None, :, 1])
    return hungarian(d**alpha)[0]


def _orient(p, q, r) -> float:
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _paths_cross(p1, p2, q1, q2, eps: float = 1e-9) -> bool:
    d1, d2 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    d3, d4 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    if d1 * d2 < -eps and d3 * d4 < -eps:
        return True
    if abs(d1) <= eps and abs(d2) <= eps:          # collinear: overlap of positive length
        axis = 0 if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]) else 1
        a0, a1 = sorted((p1[axis], p2[axis]))
        b0, b1 = sorted((q1[axis], q2[axis]))
        return min(a1, b1) - max(a0, b0) > eps
    return False


def count_crossings(starts: np.ndarray, ends: np.ndarray) -> int:
    """Number of pairs of straight paths ``starts[i] -> ends[i]`` that cross or overlap along a segment."""
    s, e = np.asarray(starts, float), np.asarray(ends, float)
    n = len(s)
    return sum(_paths_cross(s[i], e[i], s[j], e[j]) for i in range(n) for j in range(i + 1, n))


def _wrap(x):
    return np.angle(np.exp(1j * x))


def run(setup, target: Target, *, device=None, budget: Budget, rng: Rng, init=None, atoms: TrapSet | None = None,
        alpha: float = 1.5, max_step_bins: float | None = None, n_fix: int = 12) -> Result:
    require_kinds(target, SPEC.targets, SPEC.id)
    if atoms is None:
        raise ValueError("M16 needs atoms: the TrapSet of the loaded atom positions")
    tgt = target.traps
    if len(atoms) < len(tgt):
        raise ValueError(f"fewer atoms ({len(atoms)}) than targets ({len(tgt)}): the sort cannot fill every target")
    b = focal_bin_m(setup)
    step = float(setup.pad if max_step_bins is None else max_step_bins)
    if not (math.isfinite(step) and step > 0):
        raise ValueError(f"max_step_bins must be finite and positive, got {max_step_bins!r}")
    t_xy, a_xy = np.c_[tgt.x_m, tgt.y_m] / b, np.c_[atoms.x_m, atoms.y_m] / b
    f = assign(t_xy, a_xy, alpha)
    start_xy, end_xy = a_xy[f], t_xy
    crossings = count_crossings(start_xy, end_xy)
    dist = np.hypot(*(end_xy - start_xy).T)
    n_steps = max(1, int(math.ceil(dist.max() / step)))
    moved = dist > 1e-9

    def make(xy):
        return TrapSet(replace(t, x_m=float(x * b), y_m=float(y * b), z_m=0.0) for t, (x, y) in zip(tgt, xy))

    ts_start, ts_end = make(start_xy), make(end_xy)

    def wgs(ts):
        return m07_phase_fixed_wgs.run(setup, Target.from_traps(ts), budget=budget, rng=rng, n_fix=n_fix, form="auto")

    r0, r1 = wgs(ts_start), wgs(ts_end)
    amp0, amp1 = np.abs(r0.fields), np.abs(r1.fields)
    psi0, psi1 = np.angle(r0.fields), np.angle(r1.fields)
    dpsi = _wrap(psi1 - psi0)
    rec = Recorder(budget, tgt.weight)
    frames, seq, vs = [], [], []
    for s in range(n_steps + 1):
        w = s / n_steps
        xy = start_xy + w * (end_xy - start_xy)
        ts = make(xy)
        c = (amp0 + w * (amp1 - amp0)) * np.exp(1j * (psi0 + w * dpsi))
        phi = np.angle(point_trap_backproject(c, setup, ts))
        v = point_trap_fields(phi, setup, ts)
        rec.add(s + 1, v)
        frames.append(phi)
        seq.append(ts)
        vs.append(v)
    inten = np.abs(np.array(vs)) ** 2
    mean = inten.mean(axis=0)
    min_ratio = inten.min(axis=0) / np.maximum(mean, 1e-300)
    meta = {"method": SPEC.id, "frames": np.array(frames), "n_steps": n_steps, "assignment": list(f),
            "min_ratio": min_ratio, "moved": moved, "crossings": crossings, "trap_sequence": seq,
            "alpha": float(alpha), "max_step_bins": step}
    return Result(phi=frames[-1], history=rec.history, fields=vs[-1], meta=meta)
