"""Engine reference values: the Python engine's answers that the TypeScript port is held to (catalog row engine-reference 1.0.0).

``python -m pipeline.stages.engine_reference [--out DIR]`` writes one JSON document per engine function or method under
``tests/fixtures/engine/`` (schema ``docs/contracts/schemas/engine-reference.schema.json``, ``dinhot.engine-ref/v1``). The inputs are
seeded and stored with the outputs, so the TypeScript parity tests (``frontend/src/engine/holo/*.parity.test.ts``) read both from the
file and never regenerate anything; the output is a pure function of the engine code (sorted keys, no clock), so running this
module twice, or on another machine, writes identical bytes (the contract test regenerates and compares).

Encoding. A number array is ``{"shape": [...], "complex": bool, "data": [...]}`` for at most 64 values, else ``"b64"`` (little-endian
float64 of the values, complex interleaved ``re, im``); integer vectors and scalars are plain JSON. A document's ``tolerance`` is
the default comparison for the float quantities of its cases (``abs`` plus ``rel`` times the reference magnitude); a case may
carry ``outputs.tol`` with a per-quantity override, and the reason for every tolerance is in the T1 report. Integer streams (the
RNG words, quantized levels) are compared exactly.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path

import numpy as np

from ..model.holo import methods as registry
from ..model.holo.core import camera as cam
from ..model.holo.core import device as dev
from ..model.holo.core import dynamics as dyn
from ..model.holo.core import forward as fw
from ..model.holo.core import geometry as geo
from ..model.holo.core import metrics as mt
from ..model.holo.core import modes as md
from ..model.holo.core import trapphys as tp
from ..model.holo.core import traps as tr
from ..model.holo.core import zernike as zk
from ..model.holo.core.rng import Rng
from ..model.holo.core.types import Budget, Target
from ..model.holo.methods.control import m15_vortex, m16_rearrangement

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "dinhot.engine-ref/v1"
INLINE = 64


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def arr(a) -> dict:
    """Encode a float or complex array (see the module docstring)."""
    a = np.asarray(a)
    is_c = np.iscomplexobj(a)
    flat = np.ascontiguousarray(a.astype(np.complex128)).view(np.float64).ravel() if is_c else a.astype(np.float64).ravel()
    out: dict = {"shape": list(a.shape), "complex": bool(is_c)}
    if flat.size <= INLINE:
        out["data"] = [float(v) for v in flat]
    else:
        out["b64"] = base64.b64encode(flat.astype("<f8").tobytes()).decode("ascii")
    return out


def setup_doc(s: geo.Setup) -> dict:
    return {"wavelength_m": s.wavelength_m, "focal_m": s.focal_m, "na": s.na, "n_imm": s.n_imm, "n_pix": s.n_pix,
            "pitch_m": s.pitch_m, "pad": s.pad, "beam": s.beam, "waist_frac": s.waist_frac}


def traps_doc(t: tr.TrapSet) -> dict:
    return {"ids": [int(i) for i in t.ids], "x_m": [float(v) for v in t.x_m], "y_m": [float(v) for v in t.y_m],
            "z_m": [float(v) for v in t.z_m], "weight": [float(v) for v in t.weight], "charge": [int(v) for v in t.charge]}


def device_doc(d: dev.Device | None) -> dict | None:
    if d is None:
        return None
    return {"bit_depth": d.bit_depth, "crosstalk": None if d.crosstalk is None else list(d.crosstalk), "upsample": d.upsample,
            "fill_factor": d.fill_factor, "flicker_rad": d.flicker_rad, "lut_gamma": d.lut_gamma}


def hist_doc(history: list) -> dict:
    keys = [k for k in history[0] if k != "time_s"]
    return {k: [float(h[k]) for h in history] for k in keys}


def document(function: str, abs_tol: float, rel_tol: float, cases: list[dict]) -> dict:
    return {"schema": SCHEMA, "engine_version": version(), "function": function, "tolerance": {"abs": abs_tol, "rel": rel_tol},
            "cases": cases}


# ---- setups used by the fixtures (small grids; one at the live grid) ----

def S(n_pix: int = 32, pad: int = 2, beam: str = "gaussian", n_imm: float = 1.0, waist: float = 1.0) -> geo.Setup:
    return geo.Setup(wavelength_m=850e-9, focal_m=6e-3, na=0.5, n_imm=n_imm, n_pix=n_pix, pitch_m=20e-6, pad=pad, beam=beam,
                     waist_frac=waist)


def phases(seed: int, n: int) -> np.ndarray:
    return Rng(seed).phases(n * n).reshape(n, n)


def on_bins(setup: geo.Setup, traps: tr.TrapSet) -> tr.TrapSet:
    return tr.snap_to_bins(setup, traps)


def grid_bins(setup: geo.Setup, nx: int, ny: int, step_bins: int) -> tr.TrapSet:
    b = geo.focal_bin_m(setup)
    return tr.square_grid(nx, ny, step_bins * b * 1e6)


# ---- documents ----

def rng_docs() -> list[dict]:
    cases = []
    for seed in (0, 1, 7, 20261028, 4294967295):
        r = Rng(seed)
        u32 = [r.next_u32() for _ in range(32)]
        r = Rng(seed)
        unif = [r.uniform() for _ in range(16)]
        r = Rng(seed)
        norm = [r.normal() for _ in range(17)]
        r = Rng(seed)
        ph = r.phases(9)
        cases.append({"inputs": {"seed": seed}, "outputs": {"u32": u32, "uniform": unif, "normal": norm, "phases": [float(v) for v in ph]}})
    return [document("rng.stream", 1e-14, 1e-14, cases)]


def geometry_docs() -> list[dict]:
    cases = []
    for s in (S(16), S(32, beam="flat"), S(32, waist=0.7), S(24, pad=3, n_imm=1.33)):
        cases.append({"inputs": {"setup": setup_doc(s), "um": [-3.5, 0.0, 12.25], "bins": [-2.0, 0.5, 7.0]},
                      "outputs": {"input_amplitude": arr(geo.input_amplitude(s)), "focal_bin_m": geo.focal_bin_m(s),
                                  "half_field_m": geo.half_field_m(s), "n_fft": s.n_fft,
                                  "um_to_bin": [geo.um_to_bin(s, v) for v in (-3.5, 0.0, 12.25)],
                                  "bin_to_um": [geo.bin_to_um(s, v) for v in (-2.0, 0.5, 7.0)]}})
    vals = [-7.0, -6.283185307179586, -1e-18, -0.5, 0.0, 0.5, 6.283185307179586, 6.9, 100.0, -100.0]
    cases.append({"inputs": {"values": vals}, "outputs": {"wrap_phase": [float(v) for v in geo.wrap_phase(np.array(vals))]}})
    return [document("geometry.setup_functions", 1e-12, 1e-12, cases)]


def traps_docs() -> list[dict]:
    s = S(32)
    gens = {
        "square_grid": (lambda: tr.square_grid(4, 3, 9.0), {"nx": 4, "ny": 3, "spacing_um": 9.0}),
        "hex_lattice": (lambda: tr.hex_lattice(19, 8.0), {"n": 19, "spacing_um": 8.0}),
        "ring": (lambda: tr.ring(7, 30.0), {"n": 7, "radius_um": 30.0}),
        "lattice_3d": (lambda: tr.lattice_3d(2, 3, 2, 10.0, 25.0), {"nx": 2, "ny": 3, "nz": 2, "spacing_um": 10.0, "dz_um": 25.0}),
        "random_min_spacing": (lambda: tr.random_min_spacing(12, 120.0, 12.0, Rng(11)),
                               {"n": 12, "extent_um": 120.0, "min_spacing_um": 12.0, "seed": 11}),
    }
    cases = []
    for name, (make, args) in gens.items():
        t = make()
        cases.append({"inputs": {"generator": name, "args": args}, "outputs": {"traps": traps_doc(t)}})
    base = tr.square_grid(3, 3, 9.5)
    cases.append({"inputs": {"generator": "snap_to_bins", "setup": setup_doc(s), "traps": traps_doc(base)},
                  "outputs": {"traps": traps_doc(tr.snap_to_bins(s, base))}})
    bad = tr.TrapSet([tr.Trap(0, 1e-5, 0.0), tr.Trap(5, 0.0, -s.wavelength_m * s.focal_m / (2 * s.pitch_m) * 1.5),
                      tr.Trap(6, 2e-4, 0.0)])
    try:
        tr.check_in_field(s, bad)
        raise AssertionError("the planted trap must be out of the field")
    except tr.OutOfFieldError as e:
        err = {"message": str(e), "trap_id": e.trap_id, "axis": e.axis, "bound_m": e.bound_m, "value_m": e.value_m}
    cases.append({"inputs": {"generator": "check_in_field", "setup": setup_doc(s), "traps": traps_doc(bad)}, "outputs": {"error": err}})
    return [document("traps.generators", 1e-12, 1e-12, cases)]


def forward_docs() -> list[dict]:
    docs = []
    cases_pt, cases_bp, cases_fft, cases_inv, cases_tf = [], [], [], [], []
    s32, s64 = S(32), S(64, beam="flat")
    plain = tr.TrapSet([tr.Trap(0, 20e-6, -15e-6, 0.0, 1.0), tr.Trap(1, -33e-6, 8e-6, 0.0, 2.0), tr.Trap(2, 5e-6, 41e-6, 0.0, 0.5)])
    z3 = tr.TrapSet([tr.Trap(0, 20e-6, -15e-6, 120e-6, 1.0), tr.Trap(1, -33e-6, 8e-6, -80e-6, 1.0), tr.Trap(2, 0.0, 0.0, 0.0)])
    vort = tr.TrapSet([tr.Trap(0, 20e-6, -15e-6, 0.0, 1.0, 2), tr.Trap(1, -33e-6, 8e-6, 50e-6, 1.0, -3), tr.Trap(2, 1e-6, 2e-6)])
    for s, t, seed in ((s32, plain, 3), (s32, z3, 4), (s32, vort, 5), (s64, plain, 6)):
        phi = phases(seed, s.n_pix)
        cases_pt.append({"inputs": {"setup": setup_doc(s), "traps": traps_doc(t), "phi": arr(phi)},
                         "outputs": {"v": arr(fw.point_trap_fields(phi, s, t))}})
        c = np.random.default_rng(seed).standard_normal(2 * len(t)).view(np.complex128)
        cases_bp.append({"inputs": {"setup": setup_doc(s), "traps": traps_doc(t), "coeffs": arr(c)},
                         "outputs": {"field": arr(fw.point_trap_backproject(c, s, t))}})
    for s, seed in ((s32, 8), (s64, 9), (S(16, pad=3), 10)):
        phi = phases(seed, s.n_pix)
        e = fw.fft_focal_field(phi, s)
        cases_fft.append({"inputs": {"setup": setup_doc(s), "phi": arr(phi)}, "outputs": {"e": arr(e), "parseval": float(np.sum(np.abs(e) ** 2))}})
        inv = fw.fft_inverse(e * (1 + 0.1j), s)
        cases_inv.append({"inputs": {"setup": setup_doc(s), "e": arr(e * (1 + 0.1j))}, "outputs": {"field": arr(inv)}})
        t = grid_bins(s, 3, 3, 3)
        cases_tf.append({"inputs": {"setup": setup_doc(s), "traps": traps_doc(t), "e": arr(e)},
                         "outputs": {"bins": [[int(v) for v in b] for b in fw.trap_bins(s, t)], "v": arr(fw.trap_fields_from_fft(e, s, t))}})
    docs += [document("forward.point_trap_fields", 1e-12, 1e-11, cases_pt), document("forward.point_trap_backproject", 1e-11, 1e-11, cases_bp),
             document("forward.fft_focal_field", 1e-12, 1e-11, cases_fft), document("forward.fft_inverse", 1e-12, 1e-11, cases_inv),
             document("forward.trap_fields_from_fft", 1e-12, 1e-11, cases_tf)]
    asp = []
    for s, seed, dz in ((s32, 12, 40e-6), (S(32, n_imm=1.33), 13, -25e-6)):
        e = fw.fft_focal_field(phases(seed, s.n_pix), s)
        asp.append({"inputs": {"setup": setup_doc(s), "e": arr(e), "dz_m": dz}, "outputs": {"e": arr(fw.angular_spectrum(e, dz, s))}})
    docs.append(document("forward.angular_spectrum", 1e-11, 1e-9, asp))
    ax = []
    for s, seed, kw in ((s32, 14, {"y_m": 8e-6}), (s32, 15, {"x_m": -12e-6}), (S(32, n_imm=1.33), 16, {"y_m": 0.0})):
        phi = phases(seed, s.n_pix)
        cut, z, lat = fw.axial_cut(phi, s, z_range_m=(-60e-6, 60e-6), nz=7, **kw)
        ax.append({"inputs": {"setup": setup_doc(s), "phi": arr(phi), "kw": kw, "z_range_m": [-60e-6, 60e-6], "nz": 7},
                   "outputs": {"intensity": arr(cut), "z_m": arr(z), "lateral_m": arr(lat)}})
    docs.append(document("forward.axial_cut", 1e-11, 1e-8, ax))
    return docs


def metrics_docs() -> list[dict]:
    cases, pb = [], []
    for seed, w in ((1, None), (2, [1.0, 2.0, 0.5, 1.0, 3.0, 1.5])):
        v = np.random.default_rng(seed).standard_normal(12).view(np.complex128) * 0.2
        wv = None if w is None else np.array(w)
        raw, rel = mt.trap_intensities(v), mt.trap_intensities(v, wv)
        cases.append({"inputs": {"v": arr(v), "weights": None if w is None else w},
                      "outputs": {"intensities": arr(raw), "weighted": arr(rel), "efficiency": mt.efficiency(raw),
                                  "uniformity": mt.uniformity(rel), "rel_std": mt.rel_std(rel)}})
    for s, seed in ((S(32), 21), (S(32, pad=3), 22)):
        t = grid_bins(s, 3, 3, 4)
        e = fw.fft_focal_field(phases(seed, s.n_pix), s)
        b = mt.power_budget(e, s, t)
        pb.append({"inputs": {"setup": setup_doc(s), "traps": traps_doc(t), "e": arr(e), "radius_bins": 3.0},
                   "outputs": {"zero_order": mt.zero_order_fraction(e, s), "budget": b, "budget_r3": mt.power_budget(e, s, t, 3.0),
                               "ghost_r3": mt.ghost_fraction(e, s, t, 3.0)}})
    return [document("metrics.trap_metrics", 1e-13, 1e-12, cases), document("metrics.power_budget", 1e-12, 1e-11, pb)]


def device_docs() -> list[dict]:
    s = S(16)
    phi = phases(31, 16) * 1.3 - 0.4
    q, dp, ct, cta, env, foc = [], [], [], [], [], []
    for b in (1, 3, 8):
        q.append({"inputs": {"phi": arr(phi), "bit_depth": b}, "outputs": {"levels": [int(round(v / (2 * math.pi) * (1 << b))) % (1 << b) for v in dev.quantize(phi, b).ravel()],
                                                                       "phase": arr(dev.quantize(phi, b))}})
    for d, seed in ((dev.Device(bit_depth=4, lut_gamma=1.4), None), (dev.Device(bit_depth=6, flicker_rad=0.07), 5), (dev.Device(flicker_rad=0.2, lut_gamma=0.8), 9)):
        rng = None if seed is None else Rng(seed)
        dp.append({"inputs": {"phi": arr(phi), "device": device_doc(d), "seed": seed}, "outputs": {"phase": arr(dev.displayed_phase(phi, d, rng))}})
    for d in (dev.Device(crosstalk=(1.24, 1.8)), dev.Device(crosstalk=(0.8, 2.5), upsample=2), dev.Device(upsample=3)):
        psi = dev.crosstalk(phi, d)
        g = np.random.default_rng(3).standard_normal(psi.shape)
        ct.append({"inputs": {"phi": arr(phi), "device": device_doc(d)}, "outputs": {"upsampled": arr(psi)}})
        cta.append({"inputs": {"g": arr(g), "device": device_doc(d)}, "outputs": {"adjoint": arr(dev.crosstalk_adjoint(g, d)),
                                                                                "inner_lhs": float(np.sum(dev.crosstalk(phi, d) * g)),
                                                                                "inner_rhs": float(np.sum(phi * dev.crosstalk_adjoint(g, d)))}})
    for fill in (1.0, 0.7):
        d = dev.Device(fill_factor=fill)
        env.append({"inputs": {"setup": setup_doc(s), "device": device_doc(d)}, "outputs": {"envelope": arr(dev.pixel_envelope(s, d))}})
    kern = dev.crosstalk_kernel(24, 1.24, 1.8, 3)
    env.append({"inputs": {"kernel": {"n_up": 24, "sigma": 1.24, "q": 1.8, "upsample": 3}}, "outputs": {"kernel": arr(kern)}})
    for d, seed in ((dev.Device(bit_depth=4, fill_factor=0.85), 2), (dev.Device(bit_depth=8, crosstalk=(1.24, 1.8), fill_factor=0.9), 3),
                    (dev.Device(crosstalk=(1.0, 2.0), upsample=2, flicker_rad=0.05), 4)):
        e = dev.device_focal_field(phi, s, d, Rng(seed))
        foc.append({"inputs": {"setup": setup_doc(s), "phi": arr(phi), "device": device_doc(d), "seed": seed}, "outputs": {"e": arr(e)}})
    return [document("device.quantize", 0.0, 0.0, q), document("device.displayed_phase", 1e-12, 1e-12, dp),
            document("device.crosstalk", 1e-11, 1e-11, ct), document("device.crosstalk_adjoint", 1e-10, 1e-10, cta),
            document("device.pixel_envelope", 1e-13, 1e-12, env), document("device.device_focal_field", 1e-11, 1e-10, foc)]


def zernike_docs() -> list[dict]:
    s = S(24)
    nm = {"inputs": {"j": list(range(1, 22))}, "outputs": {"nm": [list(zk.noll_to_nm(j)) for j in range(1, 22)],
                                                          "names": [zk.zernike_name(j) for j in range(1, 22)]}}
    c = [0.0, 0.1, -0.2, 0.3, 0.05, -0.12, 0.08, 0.0, 0.02, -0.03, 0.07, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.04]
    wf = {"inputs": {"setup": setup_doc(s), "coeffs": c}, "outputs": {"waves": arr(zk.wavefront_waves(c, s)), "phase": arr(zk.phase_from_coeffs(c, s)),
                                                                     "rms": zk.rms_waves(c), "rms_piston": zk.rms_waves(c, True), "strehl": zk.strehl(c)}}
    wf2 = {"inputs": {"setup": setup_doc(S(24, beam="flat")), "coeffs": [0.0, 0.0, 0.0, 0.5]},
           "outputs": {"waves": arr(zk.wavefront_waves([0, 0, 0, 0.5], S(24, beam="flat"))), "phase": arr(zk.phase_from_coeffs([0, 0, 0, 0.5], S(24, beam="flat")))}}
    mo = {"inputs": {"setup": setup_doc(s), "charge": -3, "centre": [1e-5, -2e-5], "z_m": 5e-5, "x_m": 1.5e-5, "y_m": -2.5e-5},
          "outputs": {"vortex": arr(md.vortex_phase(s, -3, (1e-5, -2e-5))), "lens": arr(md.lens_phase(s, 5e-5)), "grating": arr(md.grating_phase(s, 1.5e-5, -2.5e-5))}}
    return [document("zernike.noll_to_nm", 0.0, 0.0, [nm]), document("zernike.wavefront", 1e-12, 1e-11, [wf, wf2]),
            document("modes.phases", 1e-11, 1e-11, [mo])]


def camera_docs() -> list[dict]:
    s = S(32)
    t = grid_bins(s, 3, 3, 4)
    e = fw.fft_focal_field(phases(41, 32), s)
    cases = []
    for kw in ({"gain_rms": 0.1, "noise_rms": 0.0, "blur_bins": 0.0, "rolloff": True, "fill_factor": 0.9},
               {"gain_rms": 0.0, "noise_rms": 0.002, "blur_bins": 1.5, "rolloff": False},
               {"gain_rms": 0.19, "noise_rms": 0.001, "blur_bins": 0.0, "rolloff": False}):
        c = cam.EmulatedCamera(77, **kw)
        frames = [c.measure(e, s, t) for _ in range(3)]
        cases.append({"inputs": {"setup": setup_doc(s), "traps": traps_doc(t), "e": arr(e), "seed": 77, "camera": kw},
                      "outputs": {"gains": [c.gain(i) for i in range(5)], "frames": arr(np.array(frames))}})
    return [document("camera.measure", 1e-12, 1e-10, cases)]


def physics_docs() -> list[dict]:
    a = tp.rayleigh_polarizability_Fm2(0.5e-6, 1.59, 1.33)
    grid = np.exp(-((np.arange(21)[None, :] - 10) ** 2 + (np.arange(21)[:, None] - 10) ** 2) / 18.0)
    sm = tp.stiffness_map(grid, 1e-7, 1e10, a)
    om0 = 2 * math.pi * tp.C_M_PER_S / 780.241e-9
    gam = 2 * math.pi * 6.065e6
    delta = -2 * math.pi * 1e12
    depth = tp.dipole_trap_depth_J(1e-3, 2e-6, om0, gam, delta)
    case = {"inputs": {"radius_m": 0.5e-6, "n_particle": 1.59, "n_medium": 1.33, "power_w": 1e-3, "waist_m": 2e-6, "omega0": om0, "gamma": gam,
                       "delta": delta, "mass_kg": 1.443e-25, "wavelength_m": 780.241e-9, "map": arr(grid), "spacing_m": 1e-7, "scale": 1e10},
            "outputs": {"alpha": a, "i0": tp.gaussian_peak_intensity_W_per_m2(1e-3, 2e-6), "kappa_gauss": tp.gaussian_stiffness_N_per_m(a, 1e10, 2e-6),
                        "kappa": tp.gradient_stiffness_N_per_m(a, 1e12), "k_map_xx": arr(sm[0]), "k_map_yy": arr(sm[1]),
                        "z_rayleigh": tp.rayleigh_range_m(2e-6, 780.241e-9), "u_dip": tp.dipole_potential_J(1e10, om0, gam, delta),
                        "gamma_sc": tp.scattering_rate_per_s(1e10, om0, gam, delta), "depth": depth,
                        "freqs": list(tp.trap_frequencies_rad_s(depth, 1.443e-25, 2e-6, 780.241e-9))}}
    return [document("trapphys.formulas", 0.0, 1e-12, [case])]


def dynamics_docs() -> list[dict]:
    n = 41
    ax = (np.arange(n) - 20) * 5e-8
    gx, gy = np.meshgrid(ax, ax)
    inten = np.exp(-(gx**2 + gy**2) / (2 * (4e-7) ** 2)) + 0.02
    bead = dyn.BeadParams(depth_J=2e-20, gamma_Ns_per_m=1e-8, temperature_K=295.0, start_m=(1e-7, -5e-8))
    atom = dyn.AtomParams(depth_J=1e-28, mass_kg=1.443e-25, temperature_K=1e-4, kick_m_per_s=1e-4, start_m=(1e-7, 0.0))
    pos_b = dyn.bead_trajectory(inten, (ax, ax), bead, 400, 1e-5, Rng(5))
    pos_a, vel_a = dyn.atom_trajectory(inten, (ax, ax), atom, 400, 1e-7, Rng(6))
    traj = {"inputs": {"map": arr(inten), "axis_m": arr(ax), "bead": {"depth_J": bead.depth_J, "gamma": bead.gamma_Ns_per_m, "T": bead.temperature_K, "start_m": list(bead.start_m)},
                       "atom": {"depth_J": atom.depth_J, "mass_kg": atom.mass_kg, "T": atom.temperature_K, "kick": atom.kick_m_per_s, "start_m": list(atom.start_m)},
                       "n_steps": 400, "dt_bead": 1e-5, "dt_atom": 1e-7, "seed_bead": 5, "seed_atom": 6},
            "outputs": {"bead": arr(pos_b), "atom_pos": arr(pos_a), "atom_vel": arr(vel_a)}}
    x = Rng(9).normal_array(4096)
    x = np.cumsum(x) * 1e-9
    f, p = dyn.psd(x, 1e-4, 8)
    fc, d = dyn.fit_lorentzian(f[:80], p[:80])
    spec = {"inputs": {"x": arr(x), "dt": 1e-4, "segments": 8, "fit_count": 80}, "outputs": {"f": arr(f), "p": arr(p), "fc": fc, "d": d}}
    xs = Rng(10).normal_array(3000) * 3e-8
    k = 2e-6
    bz = dyn.boltzmann_check(xs, lambda v: 0.5 * k * np.asarray(v) ** 2, 295.0, 30)
    boltz = {"inputs": {"x": arr(xs), "k_N_per_m": k, "T": 295.0, "bins": 30},
             "outputs": {"total_variation": bz["total_variation"], "empirical": arr(bz["empirical"]), "expected": arr(bz["expected"])}}
    return [document("dynamics.trajectories", 1e-12, 1e-9, [traj]), document("dynamics.psd_fit", 1e-18, 1e-9, [spec]),
            document("dynamics.boltzmann_check", 1e-12, 1e-9, [boltz])]


# ---- methods ----

def shaped_target(setup: geo.Setup, radius_bins: float, margin: int) -> Target:
    m = setup.n_fft
    iy, ix = np.indices((m, m))
    shape = np.hypot(ix - m // 2, iy - m // 2) <= radius_bins
    region = shape.copy()
    for _ in range(margin):
        g = region.copy()
        g[1:, :] |= region[:-1, :]
        g[:-1, :] |= region[1:, :]
        g[:, 1:] |= region[:, :-1]
        g[:, :-1] |= region[:, 1:]
        region = g
    return Target.from_field(shape.astype(np.float64), region)


def run_case(mid: str, setup: geo.Setup, target: Target, iterations: int, seed: int, *, device: dev.Device | None = None,
             init: np.ndarray | None = None, **kw) -> dict:
    method = registry.get(mid)
    res = method.run(setup, target, device=device, budget=Budget(iterations), rng=Rng(seed), init=init, **kw)
    inputs: dict = {"method": mid, "setup": setup_doc(setup), "iterations": iterations, "seed": seed, "device": device_doc(device),
                    "init": None if init is None else arr(init)}
    if target.kind == "traps":
        inputs["target"] = {"kind": "traps", "traps": traps_doc(target.traps)}
    else:
        inputs["target"] = {"kind": "field", "amplitude": arr(target.amplitude), "mask": arr(target.mask.astype(np.float64))}
    out = {"phi": arr(res.phi), "history": hist_doc(res.history), "fields": arr(res.fields)}
    return {"inputs": inputs, "kw": kw, "outputs": out, "meta": res.meta}


def case_doc(c: dict, extra_inputs: dict | None = None, extra_outputs: dict | None = None) -> dict:
    inputs = {**c["inputs"], "options": c["kw"], **(extra_inputs or {})}
    return {"inputs": inputs, "outputs": {**c["outputs"], **(extra_outputs or {})}}


def methods_docs() -> list[dict]:
    docs = []
    s = S(32)
    t3 = tr.square_grid(3, 3, 14.0)
    t3w = tr.TrapSet([tr.Trap(t.id, t.x_m, t.y_m, 0.0, w) for t, w in zip(t3, [1, 2, 1, 0.5, 1, 1, 1.5, 1, 1])])
    tb = on_bins(s, tr.square_grid(4, 3, 16.0))
    tz = tr.TrapSet([tr.Trap(0, 24e-6, 8e-6, 60e-6), tr.Trap(1, -24e-6, 8e-6, -60e-6), tr.Trap(2, 0.0, -24e-6, 0.0), tr.Trap(3, 8e-6, 24e-6, 30e-6)])
    tv = tr.TrapSet([tr.Trap(0, 24e-6, 0.0, 0.0, 1.0, 2), tr.Trap(1, -24e-6, 0.0, 0.0, 1.0, -1), tr.Trap(2, 0.0, 24e-6, 0.0, 1.0, 3)])

    def one(fn, cases):
        docs.append(document(f"methods.{fn}", 1e-9, 1e-9, [case_doc(c) for c in cases]))

    T = Target.from_traps
    one("M01", [run_case("M01", s, T(t3), 1, 1), run_case("M01", s, T(tz), 1, 1), run_case("M01", s, T(tv), 1, 1)])
    one("M02", [run_case("M02", s, T(t3), 1, 7), run_case("M02", s, T(tz), 1, 8)])
    one("M03", [run_case("M03", s, T(t3w), 1, 5), run_case("M03", s, T(tv), 1, 6)])
    fld = shaped_target(s, 8.0, 3)
    one("M04", [run_case("M04", s, T(t3), 15, 3), run_case("M04", s, T(tb), 15, 4, form="fft"), run_case("M04", s, fld, 10, 5),
                run_case("M04", s, T(tz), 8, 6)])
    one("M05", [run_case("M05", s, T(t3w), 12, 3), run_case("M05", s, T(tb), 12, 4, alpha=0.3, scale="absolute", form="fft")])
    one("M06", [run_case("M06", s, T(t3w), 12, 3), run_case("M06", s, T(tb), 12, 4, form="fft"), run_case("M06", s, T(tv), 8, 5)])
    one("M07", [run_case("M07", s, T(tb), 15, 3, n_fix=6), run_case("M07", s, T(t3w), 10, 4, n_fix=4, form="point")])
    one("M08", [run_case("M08", s, fld, 15, 3), run_case("M08", s, fld, 10, 4, mixing=0.5, start_waves=None)])
    tm = tr.TrapSet([tr.Trap(0, 8 * 7.96e-6, 0.0, 0.0), tr.Trap(1, -8 * 7.96e-6, 8 * 7.96e-6, 150e-6), tr.Trap(2, 0.0, -12 * 7.96e-6, -150e-6)])
    m19 = run_case("M19", s, T(tm), 6, 3, dz_m=150e-6, nz=32)
    docs.append(document("methods.M19", 1e-9, 1e-9, [case_doc(m19, extra_outputs={"snapped": traps_doc(m19["meta"]["snapped"]), "nz": m19["meta"]["nz"]})]))
    tcg = tr.square_grid(2, 2, 16.0)
    dv = dev.Device(bit_depth=4, crosstalk=(1.24, 1.8), upsample=3, fill_factor=0.9, flicker_rad=0.05)
    s16 = S(16)
    tb16 = on_bins(s16, tr.square_grid(2, 2, 24.0))
    fld16 = shaped_target(s16, 4.0, 2)
    docs.append(document("methods.M10", 1e-9, 1e-8, [case_doc(c) for c in (
        run_case("M10", s16, T(tb16), 6, 3), run_case("M10", s, T(tcg), 5, 4, efficiency=0.8), run_case("M10", s16, fld16, 6, 5, t=(4, 2)))]))
    docs.append(document("methods.M11", 1e-9, 1e-8, [case_doc(c) for c in (
        run_case("M11", s, T(tcg), 8, 3, lr=0.5), run_case("M11", s16, T(tb16), 5, 4, device=dev.Device(bit_depth=4, fill_factor=0.9)),
        run_case("M11", s16, T(tb16), 4, 5, device=dv), run_case("M11", s16, fld16, 5, 6, device=dev.Device(fill_factor=0.8)))]))
    tb12 = on_bins(s, tr.square_grid(3, 3, 16.0))
    docs.append(document("methods.M12", 1e-9, 1e-8, [case_doc(c) for c in (
        run_case("M12", s, T(tb12), 4, 3, n_start=6), run_case("M12", s, T(tb12), 3, 4, variant="kim", n_start=6),
        run_case("M12", s, T(tb12), 3, 5, n_start=4, start="gs", n_inner=2, camera=None))]))
    inj = [0.0, 0.0, 0.0, 0.25, 0.1, -0.1, 0.05, 0.0, 0.0, 0.0, 0.03]
    cam0 = cam.EmulatedCamera(8, gain_rms=0.0, rolloff=False)
    m14a = run_case("M14", s, T(tb12), 2, 3, injected=inj, camera=cam0, base_iterations=8)
    m14b = run_case("M14", s, T(tb12), 1, 3, mode="correct", injected=inj, known=[0, 0, 0, 0.2, 0.1, -0.1, 0.05, 0, 0, 0, 0.03], base_iterations=8)
    m14c = run_case("M14", s, T(tb12), 1, 4, injected=inj, camera=cam.EmulatedCamera(9, gain_rms=0.0, noise_rms=0.001, rolloff=False),
                    modes=[4, 5, 6], trial_waves=0.05, base_iterations=6)
    docs.append(document("methods.M14", 1e-9, 1e-8, [
        {"inputs": {**c["inputs"], "options": {k: v for k, v in c["kw"].items() if k != "camera"}, "camera": None if "camera" not in c["kw"] else
                    {"seed": c["kw"]["camera"].seed, "gain_rms": c["kw"]["camera"].gain_rms, "noise_rms": c["kw"]["camera"].noise_rms, "rolloff": c["kw"]["camera"].rolloff}},
         "outputs": {**c["outputs"], "coefficients": arr(c["meta"]["coefficients"]), "base_efficiency": c["meta"]["base_efficiency"],
                     "uncorrected_efficiency": c["meta"]["uncorrected_efficiency"]}} for c in (m14a, m14b, m14c)]))
    m15 = run_case("M15", s, T(tv), 10, 3)
    phi15 = registry.get("M15").run(s, T(tv), budget=Budget(10), rng=Rng(3)).phi
    prof = m15_vortex.ring_phase_profile(phi15, s, tv.traps[0])
    m15b = run_case("M15", s, T(tr.TrapSet([tr.Trap(0, 24e-6, 0.0), tr.Trap(1, -24e-6, 0.0)])), 6, 4, charge=2)
    docs.append(document("methods.M15", 1e-9, 1e-9, [case_doc(m15, extra_outputs={"ring_profile": prof}, extra_inputs={"ring": {"trap": 0}}),
                                                       case_doc(m15b)]))
    atoms = on_bins(s, tr.square_grid(4, 3, 16.0))
    tg = on_bins(s, tr.square_grid(3, 2, 16.0))
    r16 = registry.get("M16").run(s, T(tg), budget=Budget(8), rng=Rng(3), atoms=atoms, n_fix=4)
    r16b = registry.get("M16").run(s, T(tg), budget=Budget(8), rng=Rng(4), atoms=atoms, alpha=2.0, max_step_bins=3.0, n_fix=4)
    rc = []
    for r, seed, kw in ((r16, 3, {"n_fix": 4}), (r16b, 4, {"alpha": 2.0, "max_step_bins": 3.0, "n_fix": 4})):
        rc.append({"inputs": {"method": "M16", "setup": setup_doc(s), "iterations": 8, "seed": seed, "target": {"kind": "traps", "traps": traps_doc(tg)},
                              "atoms": traps_doc(atoms), "options": kw},
                   "outputs": {"phi": arr(r.phi), "history": hist_doc(r.history), "fields": arr(r.fields), "frames": arr(r.meta["frames"]),
                               "n_steps": r.meta["n_steps"], "assignment": [int(v) for v in r.meta["assignment"]], "min_ratio": arr(r.meta["min_ratio"]),
                               "moved": [bool(v) for v in r.meta["moved"]], "crossings": r.meta["crossings"]}})
    docs.append(document("methods.M16", 1e-9, 1e-8, rc))
    # assignment helpers
    rng = np.random.default_rng(5)
    hc = []
    for n, m in ((1, 1), (3, 5), (5, 5), (6, 9)):
        cost = rng.random((n, m)) * 10
        cols, total = m16_rearrangement.hungarian(cost)
        hc.append({"inputs": {"cost": arr(cost)}, "outputs": {"cols": [int(c) for c in cols], "total": total}})
    pts = rng.random((6, 2)) * 10
    at = rng.random((9, 2)) * 10
    hc.append({"inputs": {"targets": arr(pts), "atoms": arr(at), "alpha": 1.5}, "outputs": {"assign": [int(v) for v in m16_rearrangement.assign(pts, at, 1.5)],
                                                                                       "crossings": m16_rearrangement.count_crossings(at[:6], pts)}})
    docs.append(document("methods.assignment", 1e-12, 1e-12, hc))
    return docs


def live_docs() -> list[dict]:
    """The live grid: 256 x 256 pixels padded 2 (the lane budget grid), 30 iterations, 5 x 5 traps on bins."""
    s = S(256)
    t = on_bins(s, grid_bins(s, 5, 5, 20))
    tw = tr.TrapSet([tr.Trap(x.id, x.x_m, x.y_m, 0.0, 1.0 + 0.5 * (x.id % 3)) for x in t])
    docs = []
    for mid, kw, label in (("M07", {}, "M07"), ("M06", {"form": "fft"}, "M06"), ("M04", {"form": "fft"}, "M04")):
        c = run_case(mid, s, Target.from_traps(tw), 30, 20261028, **kw)
        docs.append(document(f"live.{label}", 1e-10, 1e-9, [case_doc(c)]))
    c = run_case("M11", s, Target.from_traps(t), 6, 20261028, lr=0.5)
    docs.append(document("live.M11", 1e-9, 1e-8, [case_doc(c)]))
    return docs


def all_documents(live: bool = True) -> dict[str, dict]:
    docs = rng_docs() + geometry_docs() + traps_docs() + forward_docs() + metrics_docs() + device_docs() + zernike_docs() + camera_docs() \
        + physics_docs() + dynamics_docs() + methods_docs() + (live_docs() if live else [])
    out = {d["function"]: d for d in docs}
    if len(out) != len(docs):
        raise ValueError("duplicate function names")
    return out


def _plain(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(f"{type(o).__name__} is not JSON serializable")


def dump(doc: dict) -> str:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_plain) + "\n"


def write(out_dir: Path, live: bool = True) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = set()
    paths = []
    for name, doc in sorted(all_documents(live).items()):
        p = out_dir / f"{name}.json"
        p.write_text(dump(doc), encoding="utf-8", newline="\n")
        keep.add(p.name)
        paths.append(p)
    for stale in out_dir.glob("*.json"):
        if stale.name not in keep and (live or not stale.name.startswith("live.")):
            stale.unlink()
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "tests" / "fixtures" / "engine")
    ap.add_argument("--no-live", action="store_true", help="skip the live-grid documents (the 256 x 256 runs)")
    args = ap.parse_args(argv)
    for p in write(args.out, not args.no_live):
        print(f"{p.name}  {p.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
