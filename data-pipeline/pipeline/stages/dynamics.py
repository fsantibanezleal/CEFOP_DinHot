"""The trapped-particle driver of a case (catalog row trace, ``dynamics``): a bead or an atom in the intensity the hologram
computes (physics-viz D3.2 to D3.4).

The map is the focal intensity of the reference hologram on a local grid of 0.25 focal bins and +-3 bins around the chosen
trap, evaluated with the point-trap form (exact between bins). Units: the map is in ``I_m`` (fraction of the input power
per peak), so the physical intensity is ``P I_m / (pad^2 bin^2)`` W/m^2 (one bin carries ``I_m / pad^2`` of the power).
``power_mw`` is the laser power on the SLM.

- Bead (overdamped Langevin): Rayleigh polarizability in the immersion medium, depth ``alpha I_peak / (2 c eps0)`` (the
  gradient force of ``core/trapphys.py``), drag ``6 pi eta r``. Expected corner frequency ``kappa / (2 pi gamma)`` with
  ``kappa`` from the curvature of the same map; the measured one is the Lorentzian fit of the simulated spectrum
  (``fc_ratio`` = measured over expected, the particle oracle of the SDD). The position histogram is compared with the
  Boltzmann law of the same potential (``boltzmann_tv``).
- Atom (underdamped, velocity Verlet): rubidium D2 line (780.241 nm, 6.065 MHz) with the record's detuning, dipole
  potential of Grimm et al. 2000; expected radial frequency ``sqrt(U |d2 I_hat/dx2| / m)`` from the map curvature, measured
  as the peak of the simulated position spectrum. The constants of the transition are those of the D2 line of rubidium, the
  only atom the record's mass field is used with here; another species needs its own constants.
"""
from __future__ import annotations

import math

import numpy as np

from ..core.trace import MAX_TRAJECTORY, log_psd
from ..io.contract import bin_um
from ..model.holo.core import trapphys as tp
from ..model.holo.core.dynamics import (AtomParams, BeadParams, atom_trajectory, bead_trajectory, boltzmann_check,
                                        fit_lorentzian, psd)
from ..model.holo.core.forward import point_trap_fields
from ..model.holo.core.geometry import Setup, focal_bin_m
from ..model.holo.core.rng import Rng
from ..model.holo.core.traps import Trap, TrapSet

HALF_BINS = 2.5
STEP_BINS = 0.1
RB_LAMBDA0_M = 780.241e-9
RB_GAMMA_HZ = 6.065e6
AMU_KG = 1.66053906660e-27
FIT_BAND = 5.0
SEGMENT_SAMPLES = 2048   # samples per spectrum segment: the setting of the oracle test of the engine (tests/engine)


def local_map(phi: np.ndarray, setup: Setup, cx_m: float, cy_m: float, z_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(I_m map [ny, nx], x_m axis, y_m axis)`` around a trap."""
    b = focal_bin_m(setup)
    n = int(round(2 * HALF_BINS / STEP_BINS)) + 1
    ax = (np.arange(n) - (n - 1) / 2) * STEP_BINS * b
    xs, ys = cx_m + ax, cy_m + ax
    traps = TrapSet(Trap(iy * n + ix, float(xs[ix]), float(ys[iy]), z_m) for iy in range(n) for ix in range(n))
    inten = np.abs(point_trap_fields(phi, setup, traps)) ** 2
    return inten.reshape(n, n), xs, ys


def _curvature(inten: np.ndarray, h_m: float) -> tuple[float, tuple[int, int]]:
    """-d2 I_hat/dx2 at the maximum, in 1/m^2 (I_hat = I / I_max): the stiffness along x, the axis the spectrum is of."""
    iy, ix = np.unravel_index(int(np.argmax(inten)), inten.shape)
    iy, ix = min(max(iy, 2), inten.shape[0] - 3), min(max(ix, 2), inten.shape[1] - 3)
    nrm = inten.max()
    # the wide stencil is the slope of the gradient field the integrator interpolates (np.gradient is a central difference)
    dxx = (inten[iy, ix + 2] - 2 * inten[iy, ix] + inten[iy, ix - 2]) / (2 * h_m) ** 2 / nrm
    return float(-dxx), (iy, ix)


def run(rec: dict, phi: np.ndarray, setup: Setup) -> tuple[dict, dict]:
    """``(trace dynamics, case metrics)`` for the record's dynamics block and the reference phase ``phi``."""
    d = rec["dynamics"]
    trap = next(t for t in rec["target"]["traps"] if t["id"] == d["trap_id"])
    inten, xs, ys = local_map(phi, setup, trap["x_um"] * 1e-6, trap["y_um"] * 1e-6, trap["z_um"] * 1e-6)
    h = STEP_BINS * focal_bin_m(setup)
    curv, (iy, ix) = _curvature(inten, h)
    if curv <= 0:
        raise ValueError(f"trap {d['trap_id']}: the computed intensity has no maximum curvature (not a trap)")
    p_w = d["power_mw"] * 1e-3
    bin_m = bin_um(rec["setup"]) * 1e-6
    i_peak = float(inten.max()) * p_w / (setup.pad**2 * bin_m**2)           # W/m^2
    rng = Rng(rec["seed"] + 7919)
    n, dt = d["n_steps"], d["dt_s"]
    start = (float(xs[ix]), float(ys[iy]))
    if d["particle"] == "bead":
        alpha = tp.rayleigh_polarizability_Fm2(d["bead_radius_um"] * 1e-6, d["n_particle"], setup.n_imm)
        depth = alpha * i_peak / (2.0 * tp.C_M_PER_S * tp.EPS0_F_PER_M)
        gamma = 6.0 * math.pi * d["viscosity_pa_s"] * d["bead_radius_um"] * 1e-6
        kappa = depth * curv
        fc_expected = kappa / (2.0 * math.pi * gamma)
        pos = bead_trajectory(inten, (xs, ys), BeadParams(depth, gamma, d["temperature_k"], start), n, dt, rng)
        f, p = psd(pos[:, 0], dt, max(4, n // SEGMENT_SAMPLES))
        band = f <= FIT_BAND * fc_expected          # the Lorentzian is the model near the corner, not up to Nyquist
        fc_fit, _ = fit_lorentzian(f[band], p[band])
        row = inten[iy, :] / inten.max()
        tv = boltzmann_check(pos[:, 0], lambda x: -depth * np.interp(x, xs, row), d["temperature_k"])["total_variation"]
        extra = {"kappa_pn_per_um": float(f"{kappa * 1e6:.6g}")}
        measured, ratio = fc_fit, fc_fit / fc_expected
        depth_out = {"value": float(f"{depth / (tp.KB_J_PER_K * d['temperature_k']):.6g}"), "unit": "kBT"}
        metrics = {"fc_ratio": ratio, "boltzmann_tv": float(tv)}
    else:
        om0 = 2.0 * math.pi * tp.C_M_PER_S / RB_LAMBDA0_M
        gam = 2.0 * math.pi * RB_GAMMA_HZ
        delta = 2.0 * math.pi * d["detuning_thz"] * 1e12
        depth = -tp.dipole_potential_J(i_peak, om0, gam, delta)
        if depth <= 0:
            raise ValueError("a positive (blue) detuning repels the atom: there is no trap")
        mass = d["mass_amu"] * AMU_KG
        omega = math.sqrt(depth * curv / mass)
        fc_expected = omega / (2.0 * math.pi)
        pos, _vel = atom_trajectory(inten, (xs, ys), AtomParams(depth, mass, d["temperature_k"], 0.0, start), n, dt, rng)
        f, p = psd(pos[:, 0], dt, 4)
        smooth = np.convolve(p, np.ones(3) / 3.0, mode="same")
        measured = float(f[int(np.argmax(smooth[1:-1])) + 1])
        extra = {"omega_r_hz": float(f"{fc_expected:.6g}")}
        depth_out = {"value": float(f"{depth / tp.KB_J_PER_K * 1e6:.6g}"), "unit": "uK"}
        metrics = {"fc_ratio": measured / fc_expected}
    rel_x, rel_y = (pos[:, 0] - start[0]) * 1e6, (pos[:, 1] - start[1]) * 1e6
    dec = max(1, math.ceil(len(rel_x) / MAX_TRAJECTORY))
    fo, po = log_psd(f, p * 1e12)
    trace = {"particle": d["particle"], "dt_s": dt, "t_decimation": dec,
             "x_um": [round(float(v), 4) for v in rel_x[::dec][:MAX_TRAJECTORY]],
             "y_um": [round(float(v), 4) for v in rel_y[::dec][:MAX_TRAJECTORY]],
             "psd": {"f_hz": [float(f"{v:.6g}") for v in fo], "p": [float(f"{v:.6g}") for v in po]},
             "fc_hz": float(f"{measured:.6g}"), **extra, "depth": depth_out}
    return trace, metrics

