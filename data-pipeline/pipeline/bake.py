"""The bake of one case: run every valid method, the drivers, the gates, and write the trace and the manifest.

``bake_case`` returns the manifest and the list of failures; it never raises for a method or a gate problem, so one bad
case does not hide the others (``pipeline.run_all`` raises ``BakeFailed`` at the end with every failure). A failure is
named by case, method or driver, and metric.

Order: contract-1 record -> methods through the registry (``stages/infer.py``) -> expected ranges (``core/expect.py``) ->
lane measurement (``core/gate.py``) -> maps, drivers (feedback, dynamics, rearrangement) -> trace within the byte gate ->
units gate (``core/units.py``) -> manifest. Timing decides the lane verdict and is never stored (ADR-0054).
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any

from . import registry
from .cases import build
from .core import expect as expectations
from .core import gate, trace as tracing, units
from .core import score as scoring
from .core.gate import classify_lane
from .io.model_card import is_valid_slot
from .model.holo.core.forward import axial_cut
from .model.holo.core.geometry import focal_bin_m, half_field_m
from .stages import dynamics, export, feedback, infer, rearrangement

MODEL_SLOTS = ("cgh-net", "warmstart-model")
FEEDBACK_PREFERENCE = ("M07", "M06", "M04")
AXIAL_NZ = 48
SCORE_KEYS = ("efficiency", "uniformity", "rel_std_pct", "zero_order", "ghost")
SIGNAL_KEYS = ("signal_rms_error_pct", "signal_efficiency")   # the metrics of a shaped target (core/score.py)


class BakeFailed(RuntimeError):
    """One or more cases failed their methods, drivers, expected ranges, gates or units; ``failures`` lists them all."""

    def __init__(self, failures: list[str]):
        super().__init__(f"{len(failures)} bake failure(s):\n  " + "\n  ".join(failures))
        self.failures = failures


def _extent_bins(rec: dict) -> float:
    b = focal_bin_m(build.setup_of(rec)) * 1e6
    t = rec["target"]
    if t["kind"] == "traps":
        return max(max(abs(p["x_um"]), abs(p["y_um"])) for p in t["traps"]) / b
    return max(t.get("radius_um", 0.0) + t.get("width_um", 0.0) / 2.0, t.get("length_um", 0.0) / 2.0) / b


def _ref_level(rec: dict, outcome: Any) -> float:
    """The dB reference of the maps: the mean trap intensity, or the mean intensity in the shape's interior."""
    if rec["target"]["kind"] == "traps":
        return outcome.score["efficiency"] / len(rec["target"]["traps"])
    inten = scoring.intensity_map(outcome.score["field"], build.setup_of(rec))
    return float(inten[scoring._interior(build.shape_mask(rec))].mean())


def _axial(rec: dict, outcome: Any, ctx: dict) -> dict | None:
    if rec["target"]["kind"] != "traps":
        return None
    setup, traps = ctx["setup"], rec["target"]["traps"]
    centre = min(traps, key=lambda t: (math.hypot(t["x_um"], t["y_um"]), t["id"]))
    half_z = max(5.0 * setup.wavelength_m * setup.n_imm / setup.na**2, 1.5 * max(abs(t["z_um"]) * 1e-6 for t in traps))
    ab = build.aberration_phase(rec, setup)
    phi = outcome.phi if ab is None else outcome.phi + ab
    cut, z, _lat = axial_cut(phi, setup, y_m=centre["y_um"] * 1e-6, z_range_m=(-half_z, half_z), nz=AXIAL_NZ)
    return {"trap_id": centre["id"], "z_um": [z[0] * 1e6, z[-1] * 1e6], "xz": cut}


def _signal_history(history: list[dict]) -> list[dict]:
    """The trace history of a shaped target: the trap metrics do not apply, so the two required slots carry the signal-region
    error of each iteration (``rel_std`` = 100 x error, clipped to the units domain; ``uniformity`` = 1 - error)."""
    out = []
    for h in history:
        err = float(h["error"])
        out.append({"iteration": h["iteration"], "efficiency": h["efficiency"], "uniformity": max(0.0, 1.0 - err),
                    "rel_std": min(100.0 * err, scoring.REL_STD_CAP)})
    return out


def _signal_flag(cid: str, outcomes: dict, ran: list[str]) -> dict:
    """The manifest flag that states, per method, the signal-region metrics the two required slots stand for."""
    rows = "; ".join(f"{m}: signal_rms_error_pct={outcomes[m].score['signal_rms_error_pct']:.4g}, "
                     f"signal_efficiency={outcomes[m].score['signal_efficiency']:.4g}" for m in ran)
    return {"case_id": cid, "flag": "shaped target: uniformity and rel_std_pct are not trap metrics here; rel_std_pct is "
            "signal_rms_error_pct (percent, clipped at 1000) and uniformity is max(0, 1 - signal_rms_error_pct / 100). " + rows}


def _effective(rec: dict, ran: list[str], reference: str) -> dict:
    eff = copy.deepcopy(rec)
    eff["methods"] = ran
    eff["reference_method"] = reference
    keep = {}
    for key, rng_ in rec["expect"].items():
        method, _ = expectations.parse_key(key)
        if method is None or method in ran:
            keep[key] = rng_
    eff["expect"] = keep
    return eff


def bake_case(rec: dict, *, derived_dir: Path, manifests_dir: Path, models_dir: Path, allow_missing: bool = False,
              contract_flags: list[dict] | None = None) -> tuple[dict | None, list[str]]:
    """Bake one accepted record. ``(manifest or None, failures)``."""
    cid = rec["case_id"]
    case = registry.case_for(rec)
    failures: list[str] = []
    flags = list(contract_flags or [])
    present, missing = infer.registered(rec["methods"])
    if missing:
        if allow_missing:
            flags.append({"case_id": cid, "flag": f"methods not registered in this build: {', '.join(missing)}"})
        else:
            failures.append(f"{cid}: methods not registered: {', '.join(missing)}")
    if not present:
        return None, failures or [f"{cid}: no method is registered"]
    ctx = infer.case_context(rec)
    outcomes, failed = infer.run_case(rec, present, ctx)
    for f in failed:
        failures.append(f"{cid} method {f.method}: {f.error}")
        flags.append({"case_id": cid, "flag": f"method {f.method} raised {f.error}"[:300]})
    ran = [m for m in present if m in outcomes]
    if not ran:
        return None, failures
    reference = rec["reference_method"]
    if reference not in outcomes:
        reference = ran[0]
        flags.append({"case_id": cid, "flag": f"reference method {rec['reference_method']} did not run; {reference} stands in"})
        if not allow_missing and not failed:
            failures.append(f"{cid}: reference method {rec['reference_method']} did not run")
    eff = _effective(rec, ran, reference)
    ref = outcomes[reference]

    # lane: warm re-runs of the live-lane methods (the first run carries import and cache effects)
    seconds = {}
    for m in ran:
        spec_live = outcomes[m].spec_lane in ("live", "both")
        seconds[m] = infer.time_again(eff, m, ctx, repeats=3 if m == reference else 1) if spec_live else outcomes[m].seconds
    lanes = {m: infer.lane_of(outcomes[m].spec_lane, seconds[m]) for m in ran}

    methods_manifest = {m: {"lane": lanes[m], **{k: round(float(outcomes[m].score[k]), 6) for k in SCORE_KEYS},
                            "iterations": int(outcomes[m].iterations), "converged": bool(outcomes[m].converged)}
                        for m in ran}

    # drivers
    case_metrics: dict[str, float] = {}
    fb_trace = dyn_trace = rea_trace = None
    static_ids = [m for m in FEEDBACK_PREFERENCE if m in outcomes]
    weight_method = reference if reference in FEEDBACK_PREFERENCE else (static_ids[0] if static_ids else reference)
    for name, active, fn in (
        ("feedback", eff["feedback"] is not None, lambda: feedback.run(eff, ctx, weight_method, outcomes[weight_method])),
        ("dynamics", eff["dynamics"] is not None, lambda: dynamics.run(eff, ref.phi, ctx["setup"])),
        ("rearrangement", eff["rearrangement"] is not None, lambda: rearrangement.run(eff, ctx, weight_method)),
    ):
        if not active:
            continue
        try:
            out = fn()
        except Exception as exc:  # noqa: BLE001 - a driver failure is a bake failure naming the driver
            failures.append(f"{cid} driver {name}: {type(exc).__name__}: {exc}")
            continue
        if name == "feedback":
            fb_trace = out
            case_metrics.update(feedback.case_metrics(out))
        elif name == "dynamics":
            dyn_trace, m = out
            case_metrics.update(m)
        else:
            rea_trace, m = out
            case_metrics.update(m)

    # expected ranges
    shaped = eff["target"]["kind"] == "shaped"
    method_metrics = {m: {**{k: float(outcomes[m].score[k]) for k in SCORE_KEYS + (SIGNAL_KEYS if shaped else ())},
                          "iterations": float(outcomes[m].iterations)} for m in ran}
    if shaped:
        flags.append(_signal_flag(cid, outcomes, ran))
    ranges: dict[str, list[float]] = dict(eff["expect"])
    try:
        ranges = expectations.check(cid, eff["expect"], method_metrics, reference, case_metrics)
    except expectations.ExpectationError as exc:
        failures.append(str(exc))
        ranges = {k: [float(v[0]), float(v[1])] for k, v in eff["expect"].items()}
    eff["expect"] = ranges

    # trace
    setup = ctx["setup"]
    parts = {
        "case_id": cid,
        "grid": {"n_pix": setup.n_pix, "pad": setup.pad, "bin_um": focal_bin_m(setup) * 1e6,
                 "half_field_um": half_field_m(setup) * 1e6},
        "traps": eff["target"]["traps"] if not shaped else [],
        "shape": {"kind": eff["target"]["shape"], "mask": build.shape_mask(eff)} if shaped else None,
        "methods": {m: {"history": _signal_history(outcomes[m].history) if shaped else outcomes[m].history,
                        "final": {k: outcomes[m].score[k] for k in SCORE_KEYS},
                        "trap_intensity": outcomes[m].score["trap_intensity"]} for m in ran},
        "reference": {"method": reference, "phi": ref.phi, "intensity": scoring.intensity_map(ref.score["field"], setup),
                      "ref_level": _ref_level(eff, ref), "extent_bins": max(_extent_bins(eff), 4.0),
                      "axial": _axial(eff, ref, ctx)},
        "feedback": fb_trace, "dynamics": dyn_trace, "rearrangement": rea_trace,
        "summary": export.summary(methods_manifest, shaped=shaped),
    }
    try:
        trace, trace_bytes, squeeze = tracing.fit(parts)
    except tracing.TraceTooLarge as exc:
        return None, failures + [str(exc)]
    if squeeze:
        flags.append({"case_id": cid, "flag": f"trace squeezed to level {squeeze} to fit {gate.TRACE_BYTES_GATE} bytes"})
    reasons = () if outcomes[reference].spec_lane in ("live", "both") else (f"reference method {reference} is baked-lane",)
    gate_doc = classify_lane(pure_python=True, wheels={"numpy"}, run_ms=seconds[reference] * 1000.0,
                             trace_bytes=trace_bytes, extra_reasons=reasons)
    models = {slot: "real" if is_valid_slot(models_dir, slot) else "baseline" for slot in MODEL_SLOTS}
    manifest = export.run(case=case, record=eff, trace=trace, gate=gate_doc, flags=flags, methods=methods_manifest,
                          models=models, expect=ranges, derived_dir=str(derived_dir), manifests_dir=str(manifests_dir))
    problems = units.check_case(manifest, trace)
    failures += [f"units: {p}" for p in problems]
    return manifest, failures

