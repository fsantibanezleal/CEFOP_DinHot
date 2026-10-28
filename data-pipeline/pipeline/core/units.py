"""The units gate (CAOS_MANAGE ``conventions/units-gate.md``): every observable the bake writes is checked to be in its
physical domain and in the units of the question it answers, in the bake and again over the shipped artifacts.

Observables and their units: efficiency, uniformity and zero-order fraction in [0, 1]; ghost fraction in [0, 1]; relative
standard deviation in percent (not a fraction); intensities relative to the mean trap (mean 1); positions in micrometres
inside the unaliased field of view (a position in metres would be about 1e-5); times in seconds; stiffness in pN per
micrometre; frequencies in Hz; filling in [0, 1].

The check that a method's output is in the units of the question is the consistency between the numbers a trace carries
twice: the relative standard deviation and the uniformity of a method are recomputed from its per-trap intensities (an
all-equal-weights case) and must agree, so a fraction written where a percent belongs, or a metric of another quantity
under the right name, fails (the Fragua lesson: a method that answers a different question in the same field).

Stdlib only (``statistics``): the check also runs over a shipped tree without numpy.
"""
from __future__ import annotations

import base64
import json
import math
import statistics
from pathlib import Path
from typing import Any

EPS = 1e-6


class UnitsError(ValueError):
    """An observable is outside its physical domain or in the wrong units; the message lists every problem."""


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _in(name: str, v: Any, lo: float, hi: float, out: list[str], who: str) -> None:
    if not _num(v) or not (lo - EPS <= v <= hi + EPS):
        out.append(f"{who}: {name}={v!r} is outside its domain [{lo:g}, {hi:g}]")


def check_method_row(row: dict, who: str) -> list[str]:
    out: list[str] = []
    for name in ("efficiency", "uniformity", "zero_order", "ghost"):
        if name in row:
            _in(name, row[name], 0.0, 1.0, out, who)
    if "rel_std_pct" in row:
        _in("rel_std_pct", row["rel_std_pct"], 0.0, 1000.0, out, who)
    if "iterations" in row and (not isinstance(row["iterations"], int) or row["iterations"] < 0):
        out.append(f"{who}: iterations={row['iterations']!r} is not a non-negative integer")
    return out


def _consistency(trace_method: dict, equal_weights: bool, who: str) -> list[str]:
    out: list[str] = []
    ti = trace_method["trap_intensity"]
    if not ti:
        return out
    mean = statistics.fmean(ti)
    if abs(mean - 1.0) > 2e-3:
        out.append(f"{who}: trap_intensity must be relative to the mean trap (mean 1), got mean {mean:.6g}")
    if equal_weights and mean > 0:
        pct = 100.0 * statistics.pstdev(ti) / mean
        got = trace_method["final"]["rel_std_pct"]
        if abs(pct - got) > 0.05 + 5e-3 * pct:
            out.append(f"{who}: rel_std_pct={got:.6g} but the per-trap intensities give {pct:.6g} percent "
                       f"(a fraction written as a percent, or the wrong quantity)")
        u = 1.0 - (max(ti) - min(ti)) / (max(ti) + min(ti)) if max(ti) + min(ti) > 0 else 0.0
        if abs(u - trace_method["final"]["uniformity"]) > 2e-3:
            out.append(f"{who}: uniformity={trace_method['final']['uniformity']:.6g} but the per-trap intensities give {u:.6g}")
    return out


def _b64_len(s: str) -> int:
    return len(base64.b64decode(s, validate=True))


def check_case(manifest: dict, trace: dict) -> list[str]:
    """Every units problem of one baked case (its manifest and its trace)."""
    cid = manifest["case_id"]
    out: list[str] = []
    grid = trace["grid"]
    half = grid["half_field_um"]
    if abs(2 * half - grid["bin_um"] * grid["n_pix"] * grid["pad"]) > 1e-3 * 2 * half:
        out.append(f"{cid}: grid bin_um={grid['bin_um']} and half_field_um={half} disagree (micrometres per bin)")
    for t in trace["traps"]:
        for ax in ("x_um", "y_um"):
            v = t[ax]
            if abs(v) >= half:
                out.append(f"{cid}: trap {t['id']} {ax}={v} outside the field of view +-{half:.4g} um")
            if v != 0 and abs(v) < 1e-3:
                out.append(f"{cid}: trap {t['id']} {ax}={v} looks like metres, not micrometres")
    for mid, row in manifest["methods"].items():
        out += check_method_row(row, f"{cid} {mid}")
    equal = len({t["weight"] for t in trace["traps"]}) <= 1
    for mid, m in trace["methods"].items():
        who = f"{cid} {mid}"
        out += check_method_row(m["final"], who)
        out += _consistency(m, equal, who)
        if trace["traps"] and len(m["trap_intensity"]) != len(trace["traps"]):
            out.append(f"{who}: {len(m['trap_intensity'])} trap intensities for {len(trace['traps'])} traps")
        last = -1
        for h in m["history"]:
            out += check_method_row({k: h[k] for k in ("efficiency", "uniformity", "rel_std_pct")}, f"{who} history")
            if h["iteration"] < last:
                out.append(f"{who}: history iterations go down")
            last = h["iteration"]
    ref = trace["reference"]
    if _b64_len(ref["phase_u8"]) != grid["n_pix"] ** 2:
        out.append(f"{cid}: phase_u8 is not n_pix x n_pix bytes")
    if _b64_len(ref["focal"]["intensity_db_u8"]) != ref["focal"]["size"] ** 2:
        out.append(f"{cid}: intensity_db_u8 is not size x size bytes")
    if ref["axial"] is not None and _b64_len(ref["axial"]["xz_u8"]) != ref["axial"]["nz"] * ref["axial"]["nx"]:
        out.append(f"{cid}: xz_u8 is not nz x nx bytes")
    fb = trace["feedback"]
    if fb is not None:
        for s in fb["steps"]:
            _in("rel_std_pct", s["rel_std_pct"], 0.0, 1000.0, out, f"{cid} feedback step {s['step']}")
            _in("efficiency", s["efficiency"], 0.0, 1.0, out, f"{cid} feedback step {s['step']}")
    d = trace["dynamics"]
    if d is not None:
        who = f"{cid} dynamics"
        _in("dt_s", d["dt_s"], 1e-9, 1e-3, out, who)
        if not _num(d["fc_hz"]) or d["fc_hz"] <= 0:
            out.append(f"{who}: fc_hz={d['fc_hz']!r} must be a positive frequency in Hz")
        if "kappa_pn_per_um" in d and not (1e-9 < d["kappa_pn_per_um"] < 1e6):
            out.append(f"{who}: kappa_pn_per_um={d['kappa_pn_per_um']!r} is outside 1e-9..1e6 pN/um")
        if "omega_r_hz" in d and not (d["omega_r_hz"] > 0):
            out.append(f"{who}: omega_r_hz={d['omega_r_hz']!r} must be positive (Hz)")
        if d["psd"]["f_hz"] and max(d["psd"]["f_hz"]) > 0.5 / d["dt_s"] * (1 + 1e-6):
            out.append(f"{who}: PSD frequencies exceed the Nyquist frequency 1/(2 dt_s)")
        if any(p <= 0 for p in d["psd"]["p"]):
            out.append(f"{who}: PSD must be positive")
        if not _num(d["depth"]["value"]) or d["depth"]["value"] <= 0:
            out.append(f"{who}: depth must be positive")
        if len(d["x_um"]) != len(d["y_um"]):
            out.append(f"{who}: x_um and y_um lengths differ")
        if any(abs(v) >= half for v in d["x_um"] + d["y_um"]):
            out.append(f"{who}: trajectory leaves the field of view (positions are micrometres)")
    r = trace["rearrangement"]
    if r is not None:
        who = f"{cid} rearrangement"
        for k, f in enumerate(r["filling"]):
            _in("filling", f, 0.0, 1.0, out, f"{who} frame {k}")
        _in("min_transient", r["min_transient"], 0.0, 100.0, out, who)
        times = [fr["t_s"] for fr in r["frames"]]
        if times != sorted(times) or any(not _num(t) or t < 0 for t in times):
            out.append(f"{who}: frame times (seconds) must be non-negative and increasing")
        for fr in r["frames"]:
            for mv in fr["moving"]:
                if abs(mv["x_um"]) >= half or abs(mv["y_um"]) >= half:
                    out.append(f"{who}: a moving trap leaves the field of view")
    return out


def _stat_ok(name: str, s: dict, lo: float, hi: float, out: list[str], who: str) -> None:
    for k in ("q1", "median", "q3"):
        _in(f"{name}.{k}", s.get(k), lo, hi, out, who)
    if _num(s.get("q1")) and _num(s.get("q3")) and _num(s.get("median")) and not s["q1"] - EPS <= s["median"] <= s["q3"] + EPS:
        out.append(f"{who}: {name} median outside [q1, q3]")


def check_benchmark(doc: dict) -> list[str]:
    """Units problems of a benchmark-results document: every statistic in its domain, q1 <= median <= q3."""
    out: list[str] = []
    for r in doc.get("rows", []):
        who = f"benchmark {r['method']}/{r['geometry']}/{r['device']}/{r['budget_kind']}={r['budget']}/{r['params']}"
        _stat_ok("efficiency", r["efficiency"], 0.0, 1.0, out, who)
        _stat_ok("uniformity", r["uniformity"], 0.0, 1.0, out, who)
        _stat_ok("rel_std_pct", r["rel_std_pct"], 0.0, 1000.0, out, who)
        _stat_ok("time_s", r["time_s"], 0.0, 1e5, out, who)
        _stat_ok("iterations", r["iterations"], 0.0, 1e6, out, who)
    for p in doc.get("pareto", []):
        for pt in p["points"]:
            _in("efficiency", pt["efficiency"], 0.0, 1.0, out, f"pareto {p['geometry']}")
            _in("uniformity", pt["uniformity"], 0.0, 1.0, out, f"pareto {p['geometry']}")
    return out


def check_tree(derived_root: str | Path) -> list[str]:
    """Units problems over the shipped artifacts under a ``data/derived`` layout (index, manifests, traces, benchmark).
    A document the index does not list is not read; an absent one is the readiness document's business."""
    root = Path(derived_root)
    out: list[str] = []
    idx_path = root / "manifests" / "index.json"
    if idx_path.is_file():
        for e in json.loads(idx_path.read_text(encoding="utf-8")).get("cases", []):
            if e.get("path") is None:
                continue
            mp = root / e["path"]
            if not mp.is_file():
                continue
            m = json.loads(mp.read_text(encoding="utf-8"))
            tp = root / m["artifact"]["path"]
            if tp.is_file():
                out += check_case(m, json.loads(tp.read_text(encoding="utf-8")))
    bp = root / "benchmark" / "results.json"
    if bp.is_file():
        out += check_benchmark(json.loads(bp.read_text(encoding="utf-8")))
    return out


def require(problems: list[str]) -> None:
    if problems:
        raise UnitsError("units gate failed:\n  " + "\n  ".join(problems))
