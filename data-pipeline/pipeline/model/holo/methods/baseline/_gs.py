r"""The Gerchberg-Saxton iteration shared by M04 to M08, M12, M14, M15 and M16 (no ``SPEC``: the registry skips it).

Two engines:

``run_traps``: the point-trap iteration. One iteration maps the trap fields ``V_m`` of the current hologram to the focal
coefficients ``c_m`` (the rule of the method), back-projects them to the SLM and keeps the phase:
$$\phi_j \leftarrow \arg \sum_m c_m\, e^{+i\Delta_j^m}\quad(\text{point form}),\qquad
\phi \leftarrow \arg\,\mathcal F^{-1}\big[\textstyle\sum_m c_m\,\delta(\mathbf u - \mathbf u_m)\big]\quad(\text{FFT form}).$$
The two forms are the same linear map up to a scale for traps on FFT bins (z = 0, no vortex), so they give the same hologram
to rounding (tested). The rules (``gs``, ``gaa``, ``gsw``, ``wgs_fixed``) are the ones the method docstrings state.

``run_field``: the FFT-form iteration for a shaped ``Target`` (signal mask and amplitude), mixed-region amplitude freedom
with mixing parameter ``mixing`` (``mixing = 1`` is plain GS with a zero noise region).
"""
from __future__ import annotations

import time

import numpy as np

from ...core.forward import fft_focal_field, fft_inverse, point_trap_backproject, point_trap_fields
from ...core.geometry import Setup, focal_bin_m, slm_grid
from ...core.rng import Rng
from ...core.traps import TrapSet
from ...core.types import Budget, Result, Target
from ._common import Recorder, amp_targets, fft_backproject, fft_fields, phasor, start_phase

FORMS = ("point", "fft")
AUTO = "auto"
ON_BIN_TOL = 2e-3   # bins: a trap this close to a bin centre is on it (case coordinates are rounded to 1e-4 um)


def check_form(form: str) -> str:
    if form not in FORMS + (AUTO,):
        raise ValueError(f"form must be one of {list(FORMS) + [AUTO]}, got {form!r}")
    return form


def on_bins(setup: Setup, traps: TrapSet) -> bool:
    """True when every trap is on an FFT bin (to ``ON_BIN_TOL`` bins) with z = 0 and no vortex charge."""
    b = focal_bin_m(setup)
    off = np.abs(traps.x_m / b - np.rint(traps.x_m / b)) + np.abs(traps.y_m / b - np.rint(traps.y_m / b))
    return not (np.any(off > ON_BIN_TOL) or np.any(traps.z_m != 0.0) or np.any(traps.charge != 0))


def resolve_form(setup: Setup, traps: TrapSet, form: str) -> str:
    """``form`` itself, or for ``'auto'`` the FFT form when the traps are on bins (z = 0, no vortex), else the point form."""
    check_form(form)
    if form == AUTO:
        return "fft" if on_bins(setup, traps) else "point"
    return form


def check_on_bins(setup: Setup, traps: TrapSet) -> None:
    """The FFT form samples the focal field at bins: traps must sit on bins with z = 0 and no vortex."""
    if not on_bins(setup, traps):
        raise ValueError("the fft form needs traps on FFT bins with z = 0 and no vortex (use form='point' or 'auto')")


def make_engine(setup: Setup, traps: TrapSet, form: str):
    """``(fwd, back)``: ``fwd(phi) -> V_m`` and ``back(c) -> complex SLM field`` for the chosen form."""
    form = resolve_form(setup, traps, form)
    if form == "fft":
        check_on_bins(setup, traps)
        return (lambda phi: fft_fields(phi, setup, traps)[1]), (lambda c: fft_backproject(c, setup, traps))
    return (lambda phi: point_trap_fields(phi, setup, traps)), (lambda c: point_trap_backproject(c, setup, traps))


# ---- rules: each takes the state dict, the trap fields V and the 1-based iteration, returns the coefficients c_m ----

def rule_gs(state, v, k):
    return state["a"] * phasor(v)


def rule_gaa(state, v, k):
    r"""GAA coefficients (R2 D3.4, Eq. 16): c_m = a_m V_m/|V_m| [(1 - alpha) + alpha / r_m], r_m = |V_m|/a_m.

    scale='mean' (default) divides r_m by the mean of r (amplitudes in units of the mean trap amplitude);
    scale='absolute' is the bracket as printed (amplitudes as fractions of the input power).
    """
    a, alpha = state["a"], state["alpha"]
    r = np.maximum(np.abs(v) / a, 1e-300)
    if state["scale"] == "mean":
        r = r / np.mean(r)
    return a * phasor(v) * ((1.0 - alpha) + alpha / r)


def rule_gsw(state, v, k):
    r"""$w_m \leftarrow w_m \langle r\rangle / r_m$, $c_m = w_m V_m/|V_m|$, $r_m = |V_m|/a_m$ (R2 D3.4, Eq. 18)."""
    r = np.maximum(np.abs(v) / state["a"], 1e-300)
    state["w"] = state["w"] * (np.mean(r) / r)
    return state["w"] * phasor(v)


def rule_wgs_fixed(state, v, k):
    r"""Kim 2019: $g_i = (\langle B\rangle / B_m)\, g_{i-1}$, $c_m = g_m a_m e^{i\psi_i}$, $\psi_i = \psi_N$ for $i \ge N$."""
    a = state["a"]
    b = np.maximum(np.abs(v) / a, 1e-300)
    state["w"] = state["w"] * (np.mean(b) / b)
    if k < state["n_fix"]:
        psi = np.angle(v)
    elif k == state["n_fix"]:
        psi = state["psi"] = np.angle(v)
    else:
        psi = state["psi"]
    state["psi_last"] = psi
    return state["w"] * a * np.exp(1j * psi)


def run_traps(
    mid: str, setup: Setup, traps: TrapSet, budget: Budget, rng: Rng, init, form: str, rule, state: dict,
    meta: dict | None = None,
) -> Result:
    """Iterate ``rule`` from the SR start (or ``init``) until the budget is spent; ``history`` has one entry per iteration."""
    form = resolve_form(setup, traps, form)
    fwd, back = make_engine(setup, traps, form)
    rec = Recorder(budget, traps.weight)
    phi = start_phase(setup, traps, rng, init)
    v = fwd(phi)
    state.setdefault("a", amp_targets(traps))
    state.setdefault("w", state["a"].copy() if rule is rule_gsw else np.ones(len(traps)))
    k = 0
    while True:
        k += 1
        phi = np.angle(back(rule(state, v, k)))
        v = fwd(phi)
        rec.add(k, v)
        if rec.done(k):
            break
    out = {"method": mid, "form": form, "iterations": k}
    out.update(meta or {})
    return Result(phi=phi, history=rec.history, fields=v, meta=out)


# ---- shaped targets (FFT form, mixed-region amplitude freedom) ----

def measure_region(setup: Setup, target: Target) -> np.ndarray:
    """Pixels where the shape is evaluated: ``T > 0`` inside the signal mask, eroded by one resolution cell (``pad`` bins).

    The zero-padded transform resolves a cell of ``pad`` bins (``lambda f / (n_pix p)``); a pixel closer to the shape edge
    than that cannot reach its target value for any hologram, so it is left out of the error (the dossier does not
    define the measure region; this is DinHot's choice). ``ValueError`` when the shape is thinner than the erosion.
    """
    region = target.mask & (target.amplitude > 0)
    r = int(setup.pad)
    eroded = region.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            eroded &= np.roll(np.roll(region, dy, 0), dx, 1)
    if not eroded.any():
        raise ValueError(f"the shape is thinner than the resolution cell ({r} bins on each side of every pixel)")
    return eroded


def field_error(e: np.ndarray, target: Target, region: np.ndarray) -> float:
    r"""Signal-region error eta = sqrt(mean(((s I - T^2) / T^2)^2)) over the measure region.

    s = sum T^2 / sum I rescales the intensity to the target (Pasienski and DeMarco 2008, Eq. (2)).
    """
    t2 = target.amplitude[region] ** 2
    inten = np.abs(e[region]) ** 2
    s = t2.sum() / max(inten.sum(), 1e-300)
    return float(np.sqrt(np.mean(((s * inten - t2) / t2) ** 2)))


START_WAVES = 20.0


def run_field(mid: str, setup: Setup, target: Target, budget: Budget, rng: Rng, init, mixing: float,
              start_waves: float | None = START_WAVES) -> Result:
    r"""MRAF iteration (Pasienski and DeMarco 2008, Eq. (1)); ``mixing = 1`` reduces to GS (noise region forced to zero).

    $G = \{ m\, T|_{SR} + (1-m)\, |E|\,|_{NR}\}\, e^{i \arg E}$, then $\phi = \arg \mathcal F^{-1} G$ and the SLM amplitude is
    reset to the beam. ``T`` is rescaled to the input power ($\sum T^2 = N_{pix}$ over the signal region).
    """
    if not 0.0 < mixing <= 1.0:
        raise ValueError(f"mixing must be in (0, 1], got {mixing!r}")
    n = setup.n_fft
    if target.mask.shape != (n, n):
        raise ValueError(f"the shaped target must be {n} x {n} (the FFT grid), got {target.mask.shape}")
    sig = target.mask
    t = np.where(sig, target.amplitude, 0.0)
    if not np.any(t > 0):
        raise ValueError("the target amplitude is zero in the whole signal region")
    t = t * np.sqrt(setup.n_pix**2 / np.sum(t**2))
    n_pix2 = float(setup.n_pix**2)
    phi = start_phase_field(setup, rng, init, start_waves)
    e = fft_focal_field(phi, setup)
    t0 = time.perf_counter()
    history: list = []
    k = 0
    region = measure_region(setup, target)
    t2 = (t[region]) ** 2
    while True:
        k += 1
        amp = np.where(sig, mixing * t, (1.0 - mixing) * np.abs(e))
        phi = np.angle(fft_inverse(amp * phasor(e), setup))
        e = fft_focal_field(phi, setup)
        inten = np.abs(e[region]) ** 2
        ratio = inten / t2
        mean = ratio.mean()
        history.append({
            "iteration": k, "efficiency": float(np.sum(np.abs(e[sig]) ** 2) / n_pix2),
            "uniformity": float(1.0 - (ratio.max() - ratio.min()) / (ratio.max() + ratio.min())),
            "rel_std": float(100.0 * ratio.std() / mean), "time_s": time.perf_counter() - t0,
            "error": field_error(e, target, region),
        })
        if k >= budget.iterations or (budget.time_s is not None and history[-1]["time_s"] >= budget.time_s):
            break
    return Result(phi=phi, history=history, fields=e, meta={"method": mid, "mixing": mixing, "iterations": k})


def start_phase_field(setup: Setup, rng: Rng, init, start_waves: float | None) -> np.ndarray:
    """``init`` if given; else a Fresnel-lens phase of ``start_waves`` waves at the aperture edge (a smooth start, no
    randomness: the focal field starts as a broad spot, not as speckle); ``start_waves=None``: uniform random phase."""
    if init is not None:
        phi = np.asarray(init, dtype=np.float64)
        if phi.shape != (setup.n_pix, setup.n_pix) or not np.all(np.isfinite(phi)):
            raise ValueError(f"init must be a finite array of shape {(setup.n_pix, setup.n_pix)}")
        return phi.copy()
    if start_waves is None:
        return rng.phases(setup.n_pix**2).reshape(setup.n_pix, setup.n_pix)
    x, y = slm_grid(setup)
    return 2.0 * np.pi * start_waves * (x**2 + y**2) / (setup.n_pix * setup.pitch_m / 2.0) ** 2
