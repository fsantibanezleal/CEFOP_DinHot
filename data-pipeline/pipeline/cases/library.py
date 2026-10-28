"""DinHot's twelve cases C01 to C12 (SDD, section Cases), four categories.

Each case is a params record (``docs/contracts/schemas/params-record.schema.json``) plus the reader-facing metadata the
manifest carries: bilingual title, category and expected band, the real or synthetic flag and the published anchor. The
records are written to ``data/examples/cases.json`` by ``python data-pipeline/run.py cases``; contract 1 reads them back.

Optics. Two setups carry the arrays. The atom setup (850 nm, f = 6 mm, SLM 256 x 256 at 20 um in the pupil plane, NA 0.5)
has a focal bin of 0.498 um and an unaliased half-field of 127.5 um; the bead setup (1064 nm, f = 2.4 mm, 10 um, NA 1.2 in
water) has 0.499 um and 127.7 um. The pupil (n_pix x pitch) matches 2 f NA, so the diffraction-limited spot (about
lambda f / (n_pix p), two bins) agrees with the numerical aperture. The published setups differ in detail; the parameters
that matter for each anchor (trap count, spacing in focal units, device model) are those of the source, stated per case.

Expected ranges (``expect``): a key is a metric of the reference method, or ``<method>.<metric>`` (core/expect.py). Each
case lists in ``EXPECT_BASIS`` whether its bands are ``anchor`` (a published result sets them, with the margin of the
seed spread) or ``provisional`` (set from the physical limits of the case; to be replaced by a measured band with its
margin at the first bake of the real methods). The report of the unit that last changed this file says which.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..model.holo.core.rng import Rng

Text = dict  # {"en": str, "es": str}: every reader-facing string is bilingual at the source (ADR-0011)

DEFAULT_CASE = "C02_grid_feedback"
SEED = 20261028
COORD = 4

CAT_ARRAYS = {"en": "Arrays", "es": "Matrices"}
CAT_SHAPED = {"en": "Shaped and 3D", "es": "Formas y 3D"}
CAT_DEVICE = {"en": "Device and optics", "es": "Dispositivo y óptica"}
CAT_DYNAMICS = {"en": "Dynamics and controls", "es": "Dinámica y controles"}

ATOM = dict(wavelength_nm=850, focal_mm=6, na=0.5, n_imm=1.0, n_pix=256, pitch_um=20, pad=2)
BEAD = dict(wavelength_nm=1064, focal_mm=2.4, na=1.2, n_imm=1.33, n_pix=256, pitch_um=10, pad=2)
GAUSS = {"kind": "gaussian", "waist_frac": 1.0}
DEVICE_C08 = {"bit_depth": 4, "crosstalk": {"sigma_per_px": 1.24, "q": 1.8}, "upsample": 3, "fill_factor": 0.85,
              "flicker_rad": 0.05, "lut_gamma": 1.0}
DEVICE_C04 = {"bit_depth": 8, "crosstalk": {"sigma_per_px": 1.24, "q": 1.8}, "upsample": 3, "fill_factor": 1.0,
              "flicker_rad": 0.0, "lut_gamma": 1.0}
BUDGET = {"iterations": 30, "time_s": None}


@dataclass(frozen=True)
class Case:
    id: str
    title: Text
    category: Text
    record: dict
    expected_band: Text
    real_or_synthetic: str
    anchor: dict          # {"source": Text, "url": str | None}
    expect_basis: str     # "anchor" or "provisional"


def _trap(i: int, x: float, y: float, z: float = 0.0, w: float = 1.0, charge: int = 0) -> dict:
    return {"id": i, "x_um": round(float(x), COORD) + 0.0, "y_um": round(float(y), COORD) + 0.0,
            "z_um": round(float(z), COORD) + 0.0, "weight": float(w), "charge": int(charge)}


def _grid(nx: int, ny: int, spacing_um: float, ox: float = 0.0, oy: float = 0.0) -> list[dict]:
    out = []
    for iy in range(ny):
        for ix in range(nx):
            out.append(_trap(len(out), (ix - (nx - 1) / 2) * spacing_um + ox, (iy - (ny - 1) / 2) * spacing_um + oy))
    return out


def _fourier_unit_um(s: dict) -> float:
    """One Fourier unit ``lambda f / (n_pix p)`` in micrometres."""
    return s["wavelength_nm"] * 1e-9 * s["focal_mm"] * 1e-3 / (s["n_pix"] * s["pitch_um"] * 1e-6) * 1e6


def _record(case_id: str, setup: dict, target: dict, methods: list[str], reference: str, expect: dict, *,
            device: dict | None = None, aberration: dict | None = None, feedback: dict | None = None,
            dynamics: dict | None = None, rearrangement: dict | None = None, beam: dict = GAUSS,
            budget: dict = BUDGET) -> dict:
    return {"case_id": case_id, "setup": {**setup, "beam": beam}, "device": device, "target": target,
            "aberration": aberration, "methods": methods, "reference_method": reference, "budget": dict(budget),
            "seed": SEED, "feedback": feedback, "dynamics": dynamics, "rearrangement": rearrangement, "expect": expect}


# method sets by what a case needs (the ladder of the SDD; the bake checks each against the registered MethodSpec)
POINT_2D = ["M01", "M02", "M03", "M04", "M05", "M06", "M07", "M09", "M10", "M11", "B3", "B4", "B5"]
POINT_3D = ["M01", "M02", "M04", "M06", "M09", "M10", "M11", "M15", "M19", "B5"]
FIELD = ["M04", "M08", "M10", "M11", "M13", "M17", "M18"]
DEVICE = ["M04", "M06", "M07", "M10", "M13", "B1", "B4"]


def _ring_line() -> list[dict]:
    out = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        out.append(_trap(len(out), 10.0 * math.cos(a), 20.0 + 10.0 * math.sin(a), charge=1))
    for k in range(9):
        out.append(_trap(len(out), (k - 4) * 6.0, -25.0))
    return out


def _hex_plane(n: int, spacing: float, z: float, first_id: int, vortex_slots: tuple) -> list[dict]:
    """The ``n`` sites of a hexagonal lattice nearest to the centre at height ``z``."""
    r = int(math.ceil(math.sqrt(n))) + 2
    pts = []
    for a in range(-r, r + 1):
        for b in range(-r, r + 1):
            x, y = spacing * (a + 0.5 * b), spacing * (math.sqrt(3) / 2) * b
            pts.append((round(math.hypot(x, y) / spacing, 6), round(math.atan2(y, x) % (2 * math.pi), 6), x, y))
    pts.sort()
    return [_trap(first_id + k, p[2], p[3], z, charge=8 if k in vortex_slots else 0) for k, p in enumerate(pts[:n])]


def _build() -> list[Case]:
    cases: list[Case] = []

    def add(*args, **kw):
        cases.append(Case(*args, **kw))

    lo, hi = 0.0, 1.0
    # --- Arrays -------------------------------------------------------------------------------------------------
    add("C01_square_grid", {"en": "Small square grid, 3 x 3", "es": "Matriz cuadrada pequeña, 3 x 3"}, CAT_ARRAYS,
        _record("C01_square_grid", ATOM, {"kind": "traps", "traps": _grid(3, 3, 4.0)},
                POINT_2D + ["M12"], "M06",
                {"efficiency": [0.6, hi], "uniformity": [0.85, hi], "rel_std_pct": [lo, 8.0],
                 "feedback_final_rel_std_pct": [lo, 5.0], "fc_ratio": [0.8, 1.2], "boltzmann_tv": [lo, 0.15]},
                feedback={"gain": 0.7, "steps": 5, "camera": {"gain_rms": 0.1, "noise_rms": 0.0, "blur_bins": 0.0}},
                dynamics={"particle": "bead", "trap_id": 4, "power_mw": 10.0, "bead_radius_um": 0.5,
                          "n_particle": 1.59, "viscosity_pa_s": 0.00089, "temperature_k": 295.0,
                          "n_steps": 131072, "dt_s": 5e-5}),
        {"en": "Nine equal traps. A weighted hologram reaches a relative standard deviation of a few percent and an "
               "efficiency above 0.6; one camera step brings the spread under 5 percent. A 0.5 um bead in the central "
               "trap fits a Lorentzian whose corner frequency is the trap stiffness over 2 pi gamma.",
         "es": "Nueve trampas iguales. Un holograma ponderado alcanza una desviación estándar relativa de pocos por "
               "ciento y una eficiencia sobre 0,6; un paso de cámara baja la dispersión de 5 por ciento. Una esfera de "
               "0,5 um en la trampa central ajusta una lorentziana cuya frecuencia de corte es la rigidez de la "
               "trampa sobre 2 pi gamma."},
        "synthetic",
        {"source": {"en": "Nogrette et al. 2014, Phys. Rev. X 4, 021034 (3 x 3 array, occupancy about 0.5 per trap)",
                    "es": "Nogrette et al. 2014, Phys. Rev. X 4, 021034 (matriz 3 x 3, ocupación cercana a 0,5 por trampa)"},
         "url": "https://arxiv.org/abs/1402.5329"}, "provisional")

    add(DEFAULT_CASE, {"en": "Grid with camera feedback, 10 x 10", "es": "Matriz con retroalimentación de cámara, 10 x 10"},
        CAT_ARRAYS,
        _record(DEFAULT_CASE, ATOM, {"kind": "traps", "traps": _grid(10, 10, 4.0)},
                POINT_2D + ["M12"], "M07",
                {"efficiency": [0.6, hi], "uniformity": [0.8, hi], "rel_std_pct": [lo, 10.0],
                 "feedback_initial_rel_std_pct": [10.0, 30.0], "feedback_final_rel_std_pct": [lo, 3.0]},
                feedback={"gain": 0.7, "steps": 20, "camera": {"gain_rms": 0.19, "noise_rms": 0.0, "blur_bins": 0.0}}),
        {"en": "One hundred traps whose measured depths spread by 19 percent rms before feedback (the camera gain error "
               "of the emulator). Twenty closed-loop steps at gain 0.7 bring the measured spread to the order of 1.4 "
               "percent, a 15-fold reduction.",
         "es": "Cien trampas cuyas profundidades medidas se dispersan 19 por ciento rms antes de la retroalimentación "
               "(el error de ganancia de la cámara del emulador). Veinte pasos de lazo cerrado con ganancia 0,7 llevan "
               "la dispersión medida al orden de 1,4 por ciento, una reducción de 15 veces."},
        "synthetic",
        {"source": {"en": "Nogrette et al. 2014, Phys. Rev. X 4, 021034, section III.E and Fig. 9 (19 percent rms to 1.4 "
                          "percent in 20 iterations at gain 0.7)",
                    "es": "Nogrette et al. 2014, Phys. Rev. X 4, 021034, sección III.E y Fig. 9 (19 por ciento rms a 1,4 "
                          "por ciento en 20 iteraciones con ganancia 0,7)"},
         "url": "https://arxiv.org/abs/1402.5329"}, "anchor")

    add("C03_large_array", {"en": "Large array, 32 x 32 = 1024 traps", "es": "Matriz grande, 32 x 32 = 1024 trampas"},
        CAT_ARRAYS,
        _record("C03_large_array", ATOM, {"kind": "traps", "traps": _grid(32, 32, 5.0)},
                ["M01", "M02", "M04", "M06", "M07", "M12", "B3"], "M07",
                {"efficiency": [0.4, hi], "rel_std_pct": [lo, 15.0], "feedback_initial_rel_std_pct": [10.0, 35.0],
                 "feedback_final_rel_std_pct": [lo, 4.0], "fc_ratio": [0.8, 1.2]},
                feedback={"gain": 0.9, "steps": 3, "camera": {"gain_rms": 0.22, "noise_rms": 0.0, "blur_bins": 0.0}},
                dynamics={"particle": "atom", "trap_id": 528, "power_mw": 3000.0, "mass_amu": 87.0,
                          "detuning_thz": -31.5, "temperature_k": 5e-05, "n_steps": 50000, "dt_s": 1e-7}),
        {"en": "A thousand and twenty-four equal traps at 5 um. Phase-fixed weighted GS plus three adaptive camera steps "
               "bring a 22 percent measured spread to the percent level. A rubidium atom in one trap oscillates at the "
               "radial frequency the computed intensity curvature predicts.",
         "es": "Mil veinticuatro trampas iguales a 5 um. GS ponderado con fase fija más tres pasos adaptativos de cámara "
               "llevan una dispersión medida de 22 por ciento al nivel de un por ciento. Un átomo de rubidio en una "
               "trampa oscila a la frecuencia radial que predice la curvatura de la intensidad calculada."},
        "synthetic",
        {"source": {"en": "Kim et al. 2019, Opt. Lett. 44, 3178 (22 percent to 1.4 percent in three steps); Ebadi et al. "
                          "2021 for the array size",
                    "es": "Kim et al. 2019, Opt. Lett. 44, 3178 (22 por ciento a 1,4 por ciento en tres pasos); Ebadi et "
                          "al. 2021 para el tamaño de la matriz"},
         "url": "https://doi.org/10.1364/OL.44.003178"}, "provisional")

    s12 = round(8 * _fourier_unit_um(ATOM), COORD)
    add("C12_calibration", {"en": "Calibration: the 10 x 10 task of the baselines", "es": "Calibración: la tarea 10 x 10 de las líneas base"},
        CAT_ARRAYS,
        _record("C12_calibration", ATOM, {"kind": "traps", "traps": _grid(10, 10, s12)},
                ["M01", "M02", "M03", "M04", "M05", "M06", "M07"], "M06",
                {"M06.efficiency": [0.8, hi], "M06.uniformity": [0.9, hi], "M04.efficiency": [0.8, hi],
                 "M04.uniformity": [0.3, 0.9], "M02.efficiency": [0.4, 0.95], "M02.uniformity": [lo, 0.3],
                 "M01.efficiency": [0.1, 0.6], "M01.uniformity": [lo, 0.25]}),
        {"en": "The 10 x 10 task at 8 Fourier units of the published comparison: superposition about 0.29 efficiency and "
               "0.01 uniformity, random superposition 0.69 and 0.01, GS 0.94 and 0.60, weighted GS 0.93 and 0.99, each "
               "within the seed spread of this engine.",
         "es": "La tarea 10 x 10 a 8 unidades de Fourier de la comparación publicada: superposición cerca de 0,29 de "
               "eficiencia y 0,01 de uniformidad, superposición aleatoria 0,69 y 0,01, GS 0,94 y 0,60, GS ponderado "
               "0,93 y 0,99, cada una dentro de la dispersión entre semillas de este motor."},
        "synthetic",
        {"source": {"en": "Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, Table 1",
                    "es": "Di Leonardo, Ianni y Ruocco 2007, Opt. Express 15, 1913, Tabla 1"},
         "url": "https://doi.org/10.1364/OE.15.001913"}, "anchor")

    # --- Shaped and 3D ------------------------------------------------------------------------------------------
    add("C04_disc_crosstalk", {"en": "Disc potential with the crosstalk model", "es": "Potencial de disco con el modelo de diafonía"},
        CAT_SHAPED,
        _record("C04_disc_crosstalk", ATOM,
                {"kind": "shaped", "shape": "disc", "radius_um": 15.0, "signal_margin_bins": 3}, FIELD, "M13",
                {"efficiency": [0.05, 0.9], "rel_std_pct": [lo, 30.0]}, device=DEVICE_C04,
                budget={"iterations": 30, "time_s": None}),
        {"en": "A uniform disc of 15 um radius on a device with pixel crosstalk (sigma 1.24, q 1.80). The crosstalk-aware "
               "method reaches a lower error than the same optimizer without the model, at the cost of efficiency.",
         "es": "Un disco uniforme de 15 um de radio en un dispositivo con diafonía de píxel (sigma 1,24, q 1,80). El "
               "método que conoce la diafonía alcanza un error menor que el mismo optimizador sin el modelo, a costa de "
               "eficiencia."},
        "synthetic",
        {"source": {"en": "Schroff et al. 2023, Sci. Rep. 13, 3252 (RMS error below 2 percent, efficiency 15 to 40 percent)",
                    "es": "Schroff et al. 2023, Sci. Rep. 13, 3252 (error RMS bajo 2 por ciento, eficiencia 15 a 40 por ciento)"},
         "url": "https://doi.org/10.1038/s41598-023-30296-6"}, "provisional")

    planes = (_hex_plane(17, 8.0, -10.0, 0, (0, 3, 6, 9)) + _hex_plane(17, 8.0, 0.0, 17, (0, 3, 6, 9))
              + _hex_plane(17, 8.0, 10.0, 34, (0, 3, 6, 9)))
    add("C05_multiplane_vortices", {"en": "Three-plane array with vortices", "es": "Matriz de tres planos con vórtices"},
        CAT_SHAPED,
        _record("C05_multiplane_vortices", BEAD, {"kind": "traps", "traps": planes}, POINT_3D, "M09",
                {"efficiency": [0.05, hi], "rel_std_pct": [lo, 40.0]}),
        {"en": "Fifty-one traps on three planes 10 um apart, twelve of them optical vortices of charge 8. Direct search "
               "holds the traps near their planned relative brightness.",
         "es": "Cincuenta y una trampas en tres planos separados 10 um, doce de ellas vórtices ópticos de carga 8. La "
               "búsqueda directa mantiene las trampas cerca de su brillo relativo planificado."},
        "synthetic",
        {"source": {"en": "Polin et al. 2005, Opt. Express 13, 5831 (51 traps, 12 vortices of charge 8, traps within 5 "
                          "percent after direct search)",
                    "es": "Polin et al. 2005, Opt. Express 13, 5831 (51 trampas, 12 vórtices de carga 8, trampas dentro de "
                          "5 por ciento tras búsqueda directa)"},
         "url": "https://doi.org/10.1364/OPEX.13.005831"}, "provisional")

    add("C06_vortex_ring_line", {"en": "Vortex ring plus a line of traps", "es": "Anillo de vórtices más una línea de trampas"},
        CAT_SHAPED,
        _record("C06_vortex_ring_line", BEAD, {"kind": "traps", "traps": _ring_line()},
                ["M01", "M02", "M04", "M06", "M07", "M09", "M10", "M15"], "M07",
                {"efficiency": [0.3, hi], "rel_std_pct": [lo, 30.0]}),
        {"en": "A ring of sixteen charge-1 vortex traps and a line of nine plain traps with equal power: can extended and "
               "point-like structures be balanced. No published band exists in the sources read; the band is computed.",
         "es": "Un anillo de dieciséis trampas vórtice de carga 1 y una línea de nueve trampas simples con igual "
               "potencia: se puede equilibrar lo extendido con lo puntual. No hay banda publicada en las fuentes leídas; "
               "la banda es calculada."},
        "synthetic",
        {"source": {"en": "Polin et al. 2005 show independent control of brightness and topology; no published band for this "
                          "mix (computed only)",
                    "es": "Polin et al. 2005 muestran control independiente de brillo y topología; no hay banda publicada "
                          "para esta mezcla (solo calculada)"}, "url": "https://doi.org/10.1364/OPEX.13.005831"},
        "provisional")

    # --- Device and optics --------------------------------------------------------------------------------------
    add("C07_high_na", {"en": "High numerical aperture, 5 x 5", "es": "Apertura numérica alta, 5 x 5"}, CAT_DEVICE,
        _record("C07_high_na", BEAD, {"kind": "traps", "traps": _grid(5, 5, 3.0)}, POINT_2D, "M07",
                {"efficiency": [0.5, hi], "rel_std_pct": [lo, 15.0]}),
        {"en": "Twenty-five traps at NA 1.2 in water. The scalar model is used past its validity (NA 0.7): the manifest "
               "carries the flag and the trap shape is not the vectorial one.",
         "es": "Veinticinco trampas con NA 1,2 en agua. El modelo escalar se usa más allá de su validez (NA 0,7): el "
               "manifiesto lleva la advertencia y la forma de la trampa no es la vectorial."},
        "synthetic",
        {"source": {"en": "Leutenegger et al. 2006 for the vectorial correction (equations not read in this build); no "
                          "published band",
                    "es": "Leutenegger et al. 2006 para la corrección vectorial (ecuaciones no leídas en esta versión); "
                          "sin banda publicada"}, "url": "https://doi.org/10.1364/OE.14.011277"}, "provisional")

    c08 = dict(wavelength_nm=850, focal_mm=3, na=0.5, n_imm=1.0, n_pix=128, pitch_um=20, pad=2)
    add("C08_device_limited", {"en": "Device-limited array, 4-bit phase and crosstalk", "es": "Matriz limitada por el dispositivo, fase de 4 bits y diafonía"},
        CAT_DEVICE,
        _record("C08_device_limited", c08, {"kind": "traps", "traps": _grid(8, 8, 5.0)}, DEVICE, "B1",
                {"efficiency": [0.1, hi], "rel_std_pct": [lo, 40.0]}, device=DEVICE_C08),
        {"en": "An 8 x 8 array on a device with 4-bit phase, pixel crosstalk, a fill factor of 0.85 and flicker. The "
               "device-aware weighted GS recovers uniformity that the ideal-model methods lose.",
         "es": "Una matriz 8 x 8 en un dispositivo con fase de 4 bits, diafonía de píxel, factor de llenado 0,85 y "
               "parpadeo. El GS ponderado que conoce el dispositivo recupera la uniformidad que pierden los métodos del "
               "modelo ideal."},
        "synthetic",
        {"source": {"en": "Crosstalk parameters from Schroff et al. 2023; the 4-bit, fill-factor and flicker effects have no "
                          "published source in this build (computed only)",
                    "es": "Parámetros de diafonía de Schroff et al. 2023; los efectos de 4 bits, factor de llenado y "
                          "parpadeo no tienen fuente publicada en esta versión (solo calculados)"},
         "url": "https://doi.org/10.1038/s41598-023-30296-6"}, "provisional")

    ab = {"noll": {"4": 0.08, "5": 0.07, "6": 0.05, "7": 0.06, "8": -0.05, "11": 0.04}}
    add("C09_aberrated", {"en": "Aberrated array, with and without correction", "es": "Matriz aberrada, con y sin corrección"},
        CAT_DEVICE,
        _record("C09_aberrated", ATOM, {"kind": "traps", "traps": _grid(4, 4, 5.0)},
                ["M01", "M04", "M06", "M07", "M14", "B4"], "M14",
                {"efficiency": [0.2, hi], "rel_std_pct": [lo, 40.0]}, aberration=ab),
        {"en": "A 4 x 4 array with a system wavefront of 0.15 waves rms (six Noll modes). Methods that ignore the "
               "aberration lose depth and uniformity; the Zernike correction recovers them.",
         "es": "Una matriz 4 x 4 con un frente de onda del sistema de 0,15 ondas rms (seis modos de Noll). Los métodos "
               "que ignoran la aberración pierden profundidad y uniformidad; la corrección de Zernike las recupera."},
        "synthetic",
        {"source": {"en": "Nogrette et al. 2014, Phys. Rev. X 4, 021034, section III.D (wavefront rms 0.15 to 0.014 waves, "
                          "trap depth up by about 50 percent)",
                    "es": "Nogrette et al. 2014, Phys. Rev. X 4, 021034, sección III.D (rms del frente de onda 0,15 a "
                          "0,014 ondas, profundidad de la trampa mayor en cerca de 50 por ciento)"},
         "url": "https://arxiv.org/abs/1402.5329"}, "provisional")

    # --- Dynamics and controls ----------------------------------------------------------------------------------
    target_ids = [r * 10 + c for r in range(2, 8) for c in range(2, 8)]
    add("C10_rearrangement", {"en": "Rearrangement sequence, 100 sites", "es": "Secuencia de reordenamiento, 100 sitios"},
        CAT_DYNAMICS,
        _record("C10_rearrangement", ATOM, {"kind": "traps", "traps": _grid(10, 10, 4.0)},
                ["M06", "M07", "M16", "B2"], "M16",
                {"efficiency": [0.3, hi], "min_transient": [0.1, 1.5], "final_filling": [0.9, hi]},
                rearrangement={"loading_p": 0.55, "target_ids": target_ids, "alpha": 1.5, "steps_per_move": 10}),
        {"en": "A 10 x 10 site array loaded at 55 percent; Hungarian assignment with cost d^1.5 moves the surplus atoms "
               "into the central 6 x 6 target without crossings, and the hologram of every intermediate frame keeps the "
               "moving trap lit.",
         "es": "Una matriz de 10 x 10 sitios cargada al 55 por ciento; la asignación húngara con costo d^1,5 mueve los "
               "átomos sobrantes al objetivo central de 6 x 6 sin cruces, y el holograma de cada cuadro intermedio "
               "mantiene encendida la trampa que se mueve."},
        "synthetic",
        {"source": {"en": "Barredo et al. 2016, Science 354, 1021; Endres et al. 2016; Ebadi et al. 2021; Lee, Kim and Ahn "
                          "2017 (Hungarian assignment); linear phase interpolation, arXiv 2501.01391",
                    "es": "Barredo et al. 2016, Science 354, 1021; Endres et al. 2016; Ebadi et al. 2021; Lee, Kim y Ahn "
                          "2017 (asignación húngara); interpolación lineal de fase, arXiv 2501.01391"},
         "url": "https://arxiv.org/abs/1704.07074"}, "provisional")

    add("C11_outside_field", {"en": "A trap outside the field of view (refused)", "es": "Una trampa fuera del campo de visión (rechazado)"},
        CAT_DYNAMICS,
        _record("C11_outside_field", ATOM, {"kind": "traps", "traps": [_trap(0, 200.0, 0.0)]}, ["M04", "M06"], "M06",
                {"efficiency": [0.0, hi]}),
        {"en": "One trap beyond the unaliased field of view lambda f / (2 p) = 127.5 um. Contract 1 refuses the case and "
               "names the bound; it is never computed.",
         "es": "Una trampa más allá del campo de visión sin solapamiento lambda f / (2 p) = 127,5 um. El contrato 1 "
               "rechaza el caso y nombra el límite; nunca se calcula."},
        "synthetic",
        {"source": {"en": "Derived from the pixel relation of Schroff et al. 2023 (replica period lambda f / p); an error "
                          "state, not a metric",
                    "es": "Derivado de la relación de píxel de Schroff et al. 2023 (periodo de réplica lambda f / p); un "
                          "estado de error, no una métrica"}, "url": "https://doi.org/10.1038/s41598-023-30296-6"},
        "provisional")
    return cases


CASES: list[Case] = _build()
EXPECT_BASIS = {c.id: c.expect_basis for c in CASES}


def random_loading(rec: dict) -> list[int]:
    """The ids of the loaded sites of a rearrangement record: one portable-RNG uniform per site, in id order."""
    rng = Rng(rec["seed"])
    p = rec["rearrangement"]["loading_p"]
    ids = sorted(t["id"] for t in rec["target"]["traps"])
    u = rng.uniform_array(len(ids))
    return [i for i, v in zip(ids, np.asarray(u)) if v < p]
