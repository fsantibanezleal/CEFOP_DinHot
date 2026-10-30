#!/usr/bin/env python3
"""Extract every number of the DinHot technical report from the committed files and write ``studio.json``, the macro file
``studio_numbers.tex`` and the table files ``table_*.tex``.

Run from the repository root (standard library only):

    python manuscripts/holographic-trap-studio/data/extract.py

Sources, all committed with the product:
  * ``docs/design/SDD.md``: the method ladder (id, tier, method, acceptance criterion).
  * ``data/derived/manifests/*.json`` and ``data/derived/C*/trace.json``: the baked cases (setup, device, per-method scores,
    feedback steps, bead and atom dynamics).
  * ``data/derived/benchmark/results.json``: the benchmark protocol, its cells and the skipped cells with their reasons; the
    tables summarize the cells at 100 iterations and at the 1 s budget with the default parameters.
  * ``data/derived/models/*.json`` and ``models/cgh-net.json``: the learned models and the measured negative of the
    warm-start model.
  * ``content/executive.json``: the published figures of the executive view, with their source ids.
  * ``data/derived/readiness.json``: what is real in the build.

``UNIT_ACCEPTANCE`` below is read from ``acceptance.json``, written by ``acceptance.py`` (run it first, same folder), which measures
the acceptance quantity of each method M01 to M19, BS-4 and BS-5 as its gate test computes it, on the current engine. The values
of BS-1 and BS-2 in the companion manuscript are measured by ``manuscripts/device-aware-flicker-bounded/data/measure.py``.
``QUOTED_LIVE`` holds the browser measurements, which a standard-library script cannot repeat; each names the section of
``docs/design/measured-resources.md`` or of the SDD that records it. The count of engine fixtures and their loosest tolerance are
read from ``tests/fixtures/engine``.
"""
from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"

# Published anchors of the calibration case (SDD, section Research basis, row 1: Di Leonardo, Ianni and Ruocco 2007,
# 10x10 task, efficiency / uniformity). They are quoted values of a source, used as the reference column of a table.
PUBLISHED_ANCHORS = {"M01": (0.29, 0.01), "M02": (0.69, 0.01), "M03": (0.01, 0.58), "M04": (0.94, 0.60),
                     "M05": (0.93, 0.79), "M06": (0.93, 0.99)}

# Measured acceptance of every ladder method (M01 to M19, BS-4, BS-5), read from acceptance.json, which acceptance.py writes by
# computing each method's gate quantity on the current engine; nothing of the table is typed here.
# (id, measured acceptance text, seeds, source: the gate test the row mirrors)
def load_acceptance() -> list[tuple[str, str, str, str]]:
    path = HERE / "acceptance.json"
    if not path.is_file():
        raise SystemExit(f"{path} is missing: run manuscripts/holographic-trap-studio/data/acceptance.py first")
    return [(r["id"], r["text"], r["seeds"], r["source"]) for r in json.loads(path.read_text(encoding="utf-8"))["rows"]]


UNIT_ACCEPTANCE = load_acceptance()


def acceptance_numbers() -> dict[str, dict]:
    return {r["id"]: r["numbers"] for r in json.loads((HERE / "acceptance.json").read_text(encoding="utf-8"))["rows"]}


def fixtures_summary() -> dict:
    """The engine fixtures the TypeScript parity tests read: their count and the loosest absolute tolerance they state."""
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "tests" / "fixtures" / "engine").glob("*.json"))]
    tols = [d["tolerance"]["abs"] for d in docs if isinstance(d.get("tolerance"), dict) and d["tolerance"].get("abs")]
    return {"n": len(docs), "loosest_abs": max(tols)}


NUMBER_WORDS = {10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen"}

# Browser measurements recorded in the product (docs/design/measured-resources.md, MR) and the lane budget of the design document
# (SDD, section Lanes). Source in the last field of each entry.
QUOTED_LIVE = {
    "liveTests": ("92", "MR, Live engine parity"),
    "liveGpuS": ("0.31 to 0.32", "MR, The live engine"), "liveCpuS": ("1.5 to 1.6", "MR, The live engine"),
    "liveAdapter": ("an integrated Intel gen-12lp adapter", "MR, The live engine"),
    "liveIterMs": ("24", "MR, The live engine"), "liveWorkerS": ("0.49 to 0.80", "MR, The live engine"),
    "liveBudgetMs": ("1500", "SDD Lanes"), "liveTraceKiB": ("256", "SDD Lanes"),
}

TIER_LABEL = {"classical": "Classical", "sota": "State of the art", "beyond": "Beyond"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tex_escape(s: str) -> str:
    return (s.replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
            .replace("#", "\\#").replace("$", "\\$"))


def parse_ladder() -> list[dict]:
    lines = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8").splitlines()
    i = next(k for k, line in enumerate(lines) if line.strip() == "## Method ladder")
    rows = []
    for line in lines[i + 1:]:
        if line.startswith("## "):
            break
        if re.match(r"^\| (M\d\d|BS-\d) \|", line) and not line.startswith("| BS-6 |"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append({"id": cells[0], "tier": cells[1], "method": cells[2], "criterion": cells[3], "gate": cells[4].strip("`")})
    return rows


def case_summary() -> list[dict]:
    index = load(DERIVED / "manifests" / "index.json")
    out = []
    for c in index["cases"]:
        row = {"case_id": c["case_id"], "short": c["case_id"].split("_")[0], "title": c["title"]["en"],
               "category": c["category"]["en"], "status": c["status"], "reason": (c.get("reason") or None)}
        if c["status"] == "baked":
            m = load(DERIVED / "manifests" / f"{c['case_id']}.json")
            t = load(DERIVED / c["case_id"] / "trace.json")
            p = m["params"]
            tgt = p["target"]
            row["setup"] = p["setup"]
            row["grid"] = t["grid"]
            row["wavelength_nm"] = p["setup"]["wavelength_nm"]
            row["na"] = p["setup"]["na"]
            row["n_pix"] = p["setup"]["n_pix"]
            row["target_kind"] = tgt["kind"]
            row["n_traps"] = len(tgt["traps"]) if tgt["kind"] == "traps" else None
            row["shape"] = tgt.get("shape")
            row["device"] = None if not p["device"] else {k: p["device"][k] for k in ("bit_depth", "fill_factor", "flicker_rad")}
            row["aberration"] = p.get("aberration")
            row["methods"] = {k: {a: v[a] for a in ("efficiency", "uniformity", "rel_std_pct", "iterations", "lane")}
                              for k, v in m["methods"].items()}
            row["reference_method"] = p["reference_method"]
            row["best_method"] = t["summary"]["best_method"]
            row["lane"] = m["lane"]
            row["trace_bytes"] = m["artifact"]["bytes"]
            row["seed"] = m["seed"]
            fb = t.get("feedback")
            row["feedback"] = None if not fb else [{"step": s["step"], "sigma": s["rel_std_pct"], "eff": s["efficiency"]} for s in fb["steps"]]
            dyn = t.get("dynamics")
            row["dynamics"] = None if not dyn else {k: dyn[k] for k in ("particle", "fc_hz", "kappa_pn_per_um", "omega_r_hz") if k in dyn}
            if dyn:
                row["dynamics"]["depth"] = dyn.get("depth")
        out.append(row)
    return out


def ladder_id(mid: str) -> str:
    """The SDD ladder id of an engine method (B1 is BS-1)."""
    return f"BS-{mid[1:]}" if mid.startswith("B") else mid


def bench_cells(rows: list[dict], kind: str, budget: float, params: str = "default") -> dict:
    return {(x["method"], x["geometry"], x["device"]): x for x in rows
            if x["budget_kind"] == kind and x["budget"] == budget and x["params"] == params}


def best_of(cells: dict, geometry: str, device: str, methods: set[str]) -> dict | None:
    """The method with the lowest median relative standard deviation among those of ``methods`` that reach at least half of the
    best median efficiency of the whole cell (every method, the rule of the results table), or None when none of them qualifies."""
    cell = [x for (m, g, d), x in cells.items() if g == geometry and d == device]
    cand = [(m, x) for (m, g, d), x in cells.items() if g == geometry and d == device and m in methods]
    if not cand:
        return None
    top = max(x["efficiency"]["median"] for x in cell)
    ok = [(m, x) for m, x in cand if x["efficiency"]["median"] >= 0.5 * top]
    if not ok:
        return None
    m, x = min(ok, key=lambda p: (p[1]["rel_std_pct"]["median"], p[0]))
    return {"method": m, "sigma": x["rel_std_pct"]["median"], "eff": x["efficiency"]["median"], "n_seeds": x["n_seeds"]}


def benchmark_summary(ladder: list[dict]) -> dict:
    r = load(DERIVED / "benchmark" / "results.json")
    rows = r["rows"]
    methods = sorted({x["method"] for x in rows})
    tier = {row["id"]: row["tier"] for row in ladder}
    tier_of = {m: tier.get(ladder_id(m)) for m in methods}
    skipped = {}
    for s in r["skipped"]:
        skipped.setdefault(s["reason"]["en"], 0)
        skipped[s["reason"]["en"]] += 1
    all_methods = sorted({s["method"] for s in r["skipped"]} | set(methods))
    geos = r["geometries"]
    point = [g["id"] for g in geos if g["n_traps"]]
    it100, t1 = bench_cells(rows, "iterations", 100), bench_cells(rows, "time", 1.0)
    by_geometry = {}
    for g in geos:
        for device in ("ideal", "device"):
            if not any(gg == g["id"] and d == device for (_, gg, d) in it100):
                continue
            cell = {"best": best_of(it100, g["id"], device, set(methods)), "best_1s": best_of(t1, g["id"], device, set(methods))}
            for tr in TIER_LABEL:
                cell[tr] = best_of(it100, g["id"], device, {m for m in methods if tier_of[m] == tr})
            by_geometry[f"{g['id']}/{device}"] = cell
    by_method = {}
    for m in methods:
        out = {"tier": tier_of[m]}
        for device in ("ideal", "device"):
            xs = [it100[(m, g, device)] for g in point if (m, g, device) in it100]
            out[device] = None if not xs else {
                "n": len(xs), "sigma": statistics.median(x["rel_std_pct"]["median"] for x in xs),
                "eff": statistics.median(x["efficiency"]["median"] for x in xs),
                "time_s": statistics.median(x["time_s"]["median"] for x in xs)}
        by_method[m] = out
    return {"schema": r["schema"], "engine_version": r["engine_version"], "grids": r["protocol"]["grids"],
            "seeds": r["protocol"]["seeds"], "budgets": r["protocol"]["budgets"], "geometries": geos, "point_geometries": point,
            "rows": len(rows), "methods_measured": methods, "methods_in_protocol": all_methods,
            "skipped": len(r["skipped"]), "skipped_reasons": skipped,
            "seeds_min": min((x["n_seeds"] for x in rows), default=0), "seeds_max": max((x["n_seeds"] for x in rows), default=0),
            "by_geometry": by_geometry, "by_method": by_method, "pareto": r.get("pareto") or [],
            "grid_100": {f"{m}/{g}/{d}": x["rel_std_pct"]["median"] for (m, g, d), x in it100.items()}}


def bench_leader(bench: dict, device: str) -> dict | None:
    """Over the point-trap geometries that have rows on ``device`` (the device rows leave the multi-plane geometry out): the method
    with the lowest median spread among those measured on all of them that reach at least half of the best median efficiency."""
    n = sum(1 for g in bench["point_geometries"] if f"{g}/{device}" in bench["by_geometry"])
    full = {m: v[device] for m, v in bench["by_method"].items() if v[device] and v[device]["n"] == n}
    if not full:
        return None
    top = max(v["eff"] for v in full.values())
    m, v = min(((m, v) for m, v in full.items() if v["eff"] >= 0.5 * top), key=lambda p: (p[1]["sigma"], p[0]))
    return {"method": m, **v}


def models_summary() -> dict:
    m = DERIVED / "models"
    card = load(ROOT / "models" / "cgh-net.json")
    met = load(m / "metrics.json")["slots"]["cgh-net"]
    det = load(m / "evaluation-detail.json")["cgh-net"]
    two = load(m / "cgh-net-2d-rejected.json")
    ws = load(m / "warmstart-model-rejected.json")
    tr = load(m / "cgh-net-training.json")
    return {
        "cgh_net": {"held_out_n": met["held_out_n"], "ratio": met["accuracy_vs_gs"], "time_ms": met["time_ms"],
                    "onnx_bytes": card["bytes"], "grid": card["grid"], "steps": tr["steps"], "batch": tr["config"]["batch"],
                    "ratio_by_kind": det["ratio_by_kind"], "ac_hybrid": det["ac_median"]["ac_hybrid"],
                    "ac_m19": det["ac_median"]["ac_m19_matched"], "network_ms": det["network_ms_median"],
                    "budget_ms": det["wall_clock_budget_ms"], "share_above": det["share_hybrid_above_m19"],
                    "parity_intensity": tr["parity_intensity_rel_max"], "params_note": "U-Net of 14 channels"},
        "cgh_net_2d": {"held_out_n": two["metrics_it_would_have_published"]["held_out_n"],
                       "ratio": two["metrics_it_would_have_published"]["accuracy_vs_gs"], "steps": two["candidate"]["steps"]},
        "warmstart": {"held_out_n": ws["metrics"]["held_out_n"], "iters": ws["metrics"]["iterations_to_1pct"],
                      "ratio": ws["ratio_random_over_model_median_iterations"],
                      "final_eff_diff": ws["final_metrics_relative_difference_of_medians"]["efficiency"],
                      "control": ws["control_without_the_network"]["median_and_q3_iterations"],
                      "control_never": ws["control_without_the_network"]["share_never_reaching_1pct"],
                      "n_fix_model": ws["candidate"]["n_fix_of_the_model_arm"], "n_fix_random": ws["candidate"]["n_fix_of_the_random_arm"]},
    }


def executive_summary() -> dict:
    e = load(ROOT / "content" / "executive.json")
    f = {h["source"]: h for h in e["headline_figures"]}
    en = lambda v: v["en"] if isinstance(v, dict) else v  # noqa: E731
    return {"atoms": en(f["tweezer-6100"]["value"]), "spread": en(f["tweezer-6100-full"]["value"]),
            "title": en(e["title"])}


def readiness_summary() -> dict:
    r = load(DERIVED / "readiness.json")
    return {"product_version": r["product_version"],
            "contracts": [{"id": c["id"], "state": c["state"], "provenance": c["provenance"],
                           "reason": (c.get("reason") or {}).get("en")} for c in r["contracts"]]}


def macro(name: str, value) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


# ---------------------------------------------------------------------------------------------------- tables

def table_ladder(ladder: list[dict]) -> str:
    out = ["\\begin{longtable}{@{}>{\\raggedright\\arraybackslash}p{0.07\\textwidth} >{\\raggedright\\arraybackslash}p{0.13\\textwidth} >{\\raggedright\\arraybackslash}p{0.32\\textwidth} >{\\raggedright\\arraybackslash}p{0.39\\textwidth}@{}}\n",
           "\\caption{The method ladder of the design document: identifier, tier, method and acceptance criterion.}\\label{tab:ladder}\\\\\n",
           "\\toprule Id & Tier & Method & Acceptance criterion\\\\\\midrule\\endfirsthead\n",
           "\\toprule Id & Tier & Method & Acceptance criterion\\\\\\midrule\\endhead\n"]
    for r in ladder:
        crit = tex_escape(re.sub(r"\s+", " ", r["criterion"]))
        crit = crit.replace("1e-9", "$10^{-9}$")
        out.append(f"{tex_escape(r['id'])} & {TIER_LABEL[r['tier']]} & {tex_escape(r['method'])} & \\footnotesize {crit}\\\\\n")
    out.append("\\bottomrule\\end{longtable}\n")
    return "".join(out)


def table_acceptance() -> str:
    out = ["\\begin{longtable}{@{}p{0.07\\textwidth} p{0.74\\textwidth} p{0.13\\textwidth}@{}}\n",
           "\\caption{Measured acceptance of the methods on DinHot's own grids (unit tests; seeds as stated). Intervals are [min, max].}\\label{tab:acceptance}\\\\\n",
           "\\toprule Id & Measured & Seeds\\\\\\midrule\\endfirsthead\n",
           "\\toprule Id & Measured & Seeds\\\\\\midrule\\endhead\n"]
    for mid, text, seeds, _src in UNIT_ACCEPTANCE:
        out.append(f"{mid} & \\footnotesize {tex_escape(text)} & \\footnotesize {seeds}\\\\\n")
    out.append("\\bottomrule\\end{longtable}\n")
    return "".join(out)


def table_cases(cases: list[dict]) -> str:
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           f"\\caption{{The {NUMBER_WORDS.get(len(cases), len(cases))} cases: category, optical setup, target and the methods that ran in the bake. C11 is refused by the input contract and never computed.}}\\label{{tab:cases}}\n",
           "\\begin{tabular}{@{}l l l l r l@{}}\\toprule Case & Category & Setup & Target & Methods & Reference\\\\\\midrule\n"]
    for c in cases:
        if c["status"] != "baked":
            out.append(f"{c['short']} & {tex_escape(c['category'])} & & one trap at 200 $\\mu$m, outside the field & 0 & refused\\\\\n")
            continue
        setup = f"{c['wavelength_nm']} nm, NA {c['na']:g}"
        if c["target_kind"] == "traps":
            tgt = f"{c['n_traps']} traps"
        else:
            tgt = f"{c['shape']} potential"
        dev = c["device"]
        extra = ""
        if dev:
            extra = f", {dev['bit_depth']}-bit" + (f", fill {dev['fill_factor']:g}" if dev["fill_factor"] != 1 else "")
        if c["aberration"]:
            extra += ", aberrated"
        out.append(f"{c['short']} & {tex_escape(c['category'])} & {setup} & {tgt}{extra} & {len(c['methods'])} & {c['reference_method']}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_calibration(cases: list[dict]) -> str:
    c12 = next(c for c in cases if c["short"] == "C12")
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Calibration case C12 (10 $\\times$ 10 traps at eight Fourier units): efficiency $e$ and uniformity $u$ of the analytic and Gerchberg--Saxton baselines as baked, against the values published by Di~Leonardo et al.\\ for the same task.}\\label{tab:calibration}\n",
           "\\begin{tabular}{@{}l r r r r r@{}}\\toprule Method & $e$ (baked) & $u$ (baked) & $\\sigma$ (\\%) & $e$ (published) & $u$ (published)\\\\\\midrule\n"]
    for mid in ("M01", "M02", "M03", "M04", "M05", "M06", "M07"):
        v = c12["methods"].get(mid)
        if not v:
            continue
        pe, pu = PUBLISHED_ANCHORS.get(mid, (None, None))
        pub = ("& " + f(pe, 2) + " & " + f(pu, 2)) if pe is not None else "& n/a & n/a"
        out.append(f"{mid} & {f(v['efficiency'], 3)} & {f(v['uniformity'], 3)} & {f(v['rel_std_pct'], 2)} {pub}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_results(cases: list[dict]) -> str:
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Baked results per case at the case budget: the method with the lowest relative standard deviation among those with at least half the best efficiency, and the phase-fixed WGS (M07) and plain GS (M04) rows where they ran. $e$ efficiency, $\\sigma$ relative standard deviation of the trap intensities (\\%).}\\label{tab:results}\n",
           "\\begin{tabular}{@{}l l r r r r r@{}}\\toprule Case & Best & $e$ & $\\sigma$ & M07 $\\sigma$ & M07 $e$ & M04 $\\sigma$\\\\\\midrule\n"]
    for c in cases:
        if c["status"] != "baked":
            continue
        b = c["methods"].get(c["best_method"])
        m7 = c["methods"].get("M07")
        m4 = c["methods"].get("M04")
        if c["target_kind"] != "traps":
            out.append(f"{c['short']} & shaped potential & n/a & n/a & n/a & n/a & n/a" + "\\\\\n")
            continue
        out.append(f"{c['short']} & {c['best_method']} & {f(b['efficiency'], 3)} & {sig2(b['rel_std_pct'])} & "
                   f"{sig2(m7['rel_std_pct']) if m7 else 'n/a'} & {f(m7['efficiency'], 3) if m7 else 'n/a'} & "
                   f"{f(m4['rel_std_pct'], 1) if m4 else 'n/a'}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def sig(x: float) -> str:
    """A spread in percent: two significant digits, and below the resolution of the results file (six decimals) a bound."""
    return "$<$0.001" if x < 1e-3 else (f"{x:.0f}" if x >= 100 else f"{x:.2g}")


def sig2(x: float) -> str:
    """A spread in percent at two decimals, and below them a bound."""
    return "$<$0.01" if x < 0.005 else f(x, 2)


def _cell(b: dict | None) -> str:
    return "n/a" if not b else f"{tex_escape(ladder_id(b['method']))} {sig(b['sigma'])}"


def table_benchmark(bench: dict) -> str:
    names = {g["id"]: g["name"]["en"] for g in bench["geometries"]}
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Benchmark, per geometry and device: the method of each tier with the lowest median relative standard deviation "
           "$\\sigma$ (\\%) at 100 iterations among those that reach at least half of the best median efficiency of the cell, and the best "
           "method of all at a time budget of 1~s. Default parameters, medians over the seeds of each cell.}\\label{tab:benchmark}\n",
           "\\begin{tabular}{@{}l l l l l l@{}}\\toprule Geometry & Device & Classical & State of the art & Beyond & Best at 1 s\\\\\\midrule\n"]
    for key, c in bench["by_geometry"].items():
        g, device = key.split("/")
        dev = "ideal" if device == "ideal" else "C08"
        out.append(f"{g} {tex_escape(names[g])} & {dev} & {_cell(c['classical'])} & {_cell(c['sota'])} & {_cell(c['beyond'])} & "
                   f"{_cell(c['best_1s'])}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_bench_methods(bench: dict) -> str:
    n = len(bench["point_geometries"])
    out = ["\\begin{table}[p]\\centering\\footnotesize\n",
           f"\\caption{{Benchmark, per method: medians over the point-trap geometries the method ran on (of {n}) at 100 iterations with "
           "the default parameters, on the ideal device and on the C08 device. $\\sigma$ relative standard deviation (\\%), $e$ efficiency, "
           "time wall-clock seconds under shared load.}\\label{tab:benchmethods}\n",
           "\\begin{tabular}{@{}l l r r r r r r@{}}\\toprule Id & Tier & Geometries & $\\sigma$ ideal & $e$ ideal & time (s) & $\\sigma$ C08 & "
           "$e$ C08\\\\\\midrule\n"]
    order = sorted(bench["by_method"], key=lambda m: (m.startswith("B"), m))
    for m in order:
        v = bench["by_method"][m]
        i, d = v["ideal"], v["device"]
        ideal = (f"{i['n']} & {sig(i['sigma'])} & {f(i['eff'], 3)} & {i['time_s']:.2g}" if i else "0 & n/a & n/a & n/a")
        dev = f"{sig(d['sigma'])} & {f(d['eff'], 3)}" if d else "n/a & n/a"
        out.append(f"{tex_escape(ladder_id(m))} & {TIER_LABEL.get(v['tier'], '')} & {ideal} & {dev}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


# ---------------------------------------------------------------------------------------------------- main

def main() -> int:
    ladder = parse_ladder()
    cases = case_summary()
    bench = benchmark_summary(ladder)
    models = models_summary()
    ex = executive_summary()
    ready = readiness_summary()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    tiers = {t: sum(1 for r in ladder if r["tier"] == t) for t in TIER_LABEL}
    baked = [c for c in cases if c["status"] == "baked"]
    traps = [c["n_traps"] for c in baked if c["n_traps"]]
    method_cells = sum(len(c["methods"]) for c in baked)
    engine_methods = sorted({m for c in baked for m in c["methods"]})
    fb = {c["short"]: c["feedback"] for c in baked if c["feedback"]}
    dyn = {c["short"]: c["dynamics"] for c in baked if c["dynamics"]}
    data = {"product_version": version, "ladder": ladder, "tiers": tiers, "cases": cases, "benchmark": bench, "models": models,
            "executive": ex, "readiness": ready, "unit_acceptance": UNIT_ACCEPTANCE, "published_anchors": PUBLISHED_ANCHORS}
    (HERE / "studio.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    L = ["% Generated by data/extract.py from the committed files. Do not edit.\n"]
    L.append(macro("productVersion", version))
    L.append(macro("nClassical", tiers["classical"]))
    L.append(macro("nSota", tiers["sota"]))
    L.append(macro("nBeyond", tiers["beyond"]))
    L.append(macro("nLadder", len(ladder)))
    L.append(macro("nCases", len(cases)))
    L.append(macro("nCasesBaked", len(baked)))
    L.append(macro("nMethodsBaked", len(engine_methods)))
    L.append(macro("nMethodCells", method_cells))
    L.append(macro("minTraps", min(traps)))
    L.append(macro("maxTraps", max(traps)))
    c13 = next(c for c in baked if c["short"] == "C13")
    L.append(macro("nDisordered", c13["n_traps"]))
    for short, pre in (("C02", "atom"), ("C05", "bead"), ("C08", "devc"), ("C14", "volu")):
        c = next(x for x in baked if x["short"] == short)
        st, gr = c["setup"], c["grid"]
        L.append(macro(pre + "Lambda", st["wavelength_nm"]))
        L.append(macro(pre + "Focal", f"{st['focal_mm']:g}"))
        L.append(macro(pre + "Na", f"{st['na']:g}"))
        L.append(macro(pre + "Nimm", f"{st['n_imm']:g}"))
        L.append(macro(pre + "Npix", st["n_pix"]))
        L.append(macro(pre + "Pitch", f"{st['pitch_um']:g}"))
        L.append(macro(pre + "Pad", st["pad"]))
        L.append(macro(pre + "Bin", f(gr["bin_um"], 3)))
        L.append(macro(pre + "Half", f(gr["half_field_um"], 1)))
    cc8 = next(x for x in baked if x["short"] == "C08")
    L.append(macro("devcBits", cc8["device"]["bit_depth"]))
    L.append(macro("devcFill", f"{cc8['device']['fill_factor']:g}"))
    L.append(macro("devcFlicker", f"{cc8['device']['flicker_rad']:g}"))
    not_baked = sorted(set(bench["methods_in_protocol"]) - set(engine_methods))
    L.append(macro("notBakedSentence", "every one of them ran in at least one case" if not not_baked else
                   " and ".join(not_baked) + (" is" if len(not_baked) == 1 else " are") + " not part of any case"))
    for k, (v, _src) in QUOTED_LIVE.items():
        L.append(macro(k, v))
    fx = fixtures_summary()
    L.append(macro("liveFixtures", fx["n"]))
    L.append(macro("liveTol", f"10^{{{round(math.log10(fx['loosest_abs']))}}}"))
    # the measured acceptance rows the prose cites (acceptance.json)
    acc = acceptance_numbers()
    m4, b4, b5 = acc["M04"], acc["BS-4"], acc["BS-5"]
    L.append(macro("accFourFlatEff", f(statistics.median(m4["flat_efficiency"]), 3)))
    L.append(macro("accFourFlatUni", f(statistics.median(m4["flat_uniformity"]), 3)))
    L.append(macro("accBFourRatio", f(statistics.median(b4["ratio"]), 3)))
    L.append(macro("accBFourRatioLo", f(min(b4["ratio"]), 2)))
    L.append(macro("accBFourRatioHi", f(max(b4["ratio"]), 2)))
    L.append(macro("accBFourSeeds", len(b4["ratio"])))
    L.append(macro("accBFourEffDrop", f"{100 * (1 - statistics.median(b4['eff_ratio'])):.1f}"))
    L.append(macro("accBFourPointing", f(b4["pointing_ratio"], 2)))
    L.append(macro("accBFiveHv", f(b5["hypervolume"], 4)))
    L.append(macro("accBFiveHvBase", f(b5["hypervolume_base"], 4)))
    L.append(macro("accBFiveDomFour", b5["dominating_m04"]))
    L.append(macro("accBFiveDomFive", b5["dominating_m05"]))
    L.append(macro("benchTimes", ", ".join(f"{x:g}" for x in bench["budgets"]["time_s"])))
    L.append(macro("bakeCeightMsevenSigma", f(cc8["methods"]["M07"]["rel_std_pct"], 1)))
    L.append(macro("bakeCeightBOneSigma", f(cc8["methods"]["B1"]["rel_std_pct"], 1)))
    L.append(macro("bakeCeightRatio", f(cc8["methods"]["M07"]["rel_std_pct"] / cc8["methods"]["B1"]["rel_std_pct"], 1)))
    L.append(macro("bakeCeightEffRatio", f(cc8["methods"]["B1"]["efficiency"] / cc8["methods"]["M07"]["efficiency"], 3)))
    # executive
    L.append(macro("execAtoms", f"{ex['atoms']}"))
    L.append(macro("execSpread", f"{ex['spread']}"))
    # benchmark
    L.append(macro("benchSeeds", bench["seeds"]))
    L.append(macro("benchGrids", ", ".join(str(g) for g in bench["grids"])))
    L.append(macro("benchIters", ", ".join(str(g) for g in bench["budgets"]["iterations"])))
    L.append(macro("benchGeometries", len(bench["geometries"])))
    L.append(macro("benchRows", bench["rows"]))
    L.append(macro("benchSkipped", bench["skipped"]))
    L.append(macro("benchMethodsMeasured", ", ".join(bench["methods_measured"])))
    L.append(macro("benchNMeasured", len(bench["methods_measured"])))
    L.append(macro("benchNProtocol", len(bench["methods_in_protocol"])))
    # BS-1 against M07 on the C08 device, per geometry, at 100 iterations (the grid of medians): both thresholds of the claim
    g100 = load(DERIVED / "benchmark" / "results.json")
    c100 = {(x["method"], x["geometry"]): x for x in g100["rows"] if x["budget_kind"] == "iterations" and x["budget"] == 100
            and x["params"] == "default" and x["device"] == "device"}
    b1_cells = [(g, c100[("M07", g)]["rel_std_pct"]["median"] / c100[("B1", g)]["rel_std_pct"]["median"],
                 c100[("B1", g)]["efficiency"]["median"] / c100[("M07", g)]["efficiency"]["median"])
                for (m, g) in sorted(c100) if m == "B1" and ("M07", g) in c100]
    b1_pass = [g for g, fac, eff in b1_cells if fac >= 2 and eff >= 0.9]
    L.append(macro("benchOneN", len(b1_cells)))
    L.append(macro("benchOnePass", len(b1_pass)))
    L.append(macro("benchOnePassList", " and ".join(b1_pass) if b1_pass else "none"))
    m8 = load(DERIVED / "manifests" / "C08_device_limited.json")["params"]["device"]
    L.append(macro("devcXtSigma", f"{m8['crosstalk']['sigma_per_px']:.2f}"))
    L.append(macro("devcXtQ", f"{m8['crosstalk']['q']:.2f}"))
    floor = re.search(r"^EFFICIENCY_FLOOR = ([0-9.]+)", (ROOT / "data-pipeline" / "pipeline" / "model" / "holo" / "methods" / "beyond"
                                                         / "b1_device_wgs.py").read_text(encoding="utf-8"), re.M)
    L.append(macro("bOneFloor", floor.group(1)))
    step = re.search(r"^CLAIM_STEP_FU = ([0-9.]+)", (ROOT / "data-pipeline" / "pipeline" / "model" / "holo" / "methods" / "beyond"
                                                     / "b2_flicker_bounded.py").read_text(encoding="utf-8"), re.M)
    L.append(macro("bTwoStep", step.group(1)))
    mr8 = load(ROOT / "data-pipeline" / "pipeline" / "cases" / "measured_ranges.json")["measured"]["C08_device_limited"]
    L.append(macro("bakeCeightRatioThree", f(statistics.mean(mr8["M07.rel_std_pct"]) / statistics.mean(mr8["B1.rel_std_pct"]), 1)))
    L.append(macro("bakeCeightSeedsN", len(mr8["B1.rel_std_pct"])))
    # BS-5 in the benchmark: the stored front against the union of the classical points of its criterion, ideal device, 100 iterations
    def hv(pts):
        pts = [p for p in pts if not any(q[0] >= p[0] and q[1] >= p[1] and (q[0] > p[0] or q[1] > p[1]) for q in pts)]
        pts.sort()
        area, prev = 0.0, 0.0
        for i, (e, _) in enumerate(pts):
            area += (e - prev) * max(u for _, u in pts[i:])
            prev = e
        return area
    rb = load(DERIVED / "benchmark" / "results.json")
    c5 = {(x["method"], x["geometry"]): x for x in rb["rows"] if x["budget_kind"] == "iterations" and x["budget"] == 100
          and x["params"] == "default" and x["device"] == "ideal"}
    five = []
    for f5 in rb.get("pareto") or []:
        g = f5["geometry"]
        pts = [(c5[(m, g)]["efficiency"]["median"], c5[(m, g)]["uniformity"]["median"]) for m in ("M04", "M05", "M06", "M09") if (m, g) in c5]
        if pts:
            five.append((g, hv([(p["efficiency"], p["uniformity"]) for p in f5["points"]]), hv(pts)))
    lost = [f"{g} ({a:.3f} against {b:.3f})" for g, a, b in sorted(five) if a < b]
    L.append(macro("benchFiveN", len(five)))
    L.append(macro("benchFivePass", sum(1 for _, a, b in five if a >= b)))
    L.append(macro("benchFiveLost", ", ".join(lost) if lost else "none"))
    no_rows = [m for m in bench["methods_in_protocol"] if m not in bench["methods_measured"]]
    # main.tex names the reasons of these three methods (a vortex charge, a rearrangement block, the learned model's geometry)
    if bench["rows"] > 100 and set(no_rows) != {"M15", "M16", "M17"}:
        raise SystemExit(f"the methods without a benchmark row are {no_rows}: revise the sentence of main.tex that names their reasons")
    L.append(macro("benchNoRows", " , ".join(tex_escape(ladder_id(m)) for m in no_rows).replace(" , ", ", ") or "none"))
    L.append(macro("benchNNoRows", len(no_rows)))
    L.append(macro("benchSeedsMin", bench["seeds_min"]))
    L.append(macro("benchSeedsMax", bench["seeds_max"]))
    L.append(macro("benchNPoint", len(bench["point_geometries"])))
    for device, nm in (("ideal", "Ideal"), ("device", "Device")):
        cells = [c for k, c in bench["by_geometry"].items() if k.endswith("/" + device)]
        L.append(macro(f"benchGeo{nm}", len(cells)))
        # a cell whose best spreads of two or more tiers sit below the file's resolution is a tie, not a win of one tier
        def tied(c: dict) -> bool:
            return sum(1 for tr in TIER_LABEL if c[tr] and c[tr]["sigma"] < 1e-3) >= 2

        for tr, tn in (("classical", "Classical"), ("sota", "Sota"), ("beyond", "Beyond")):
            L.append(macro(f"benchWins{nm}{tn}", sum(1 for c in cells if c["best"] and not tied(c)
                                                     and bench["by_method"][c["best"]["method"]]["tier"] == tr)))
        L.append(macro(f"benchTies{nm}", sum(1 for c in cells if tied(c))))
        meds = [v[device] for v in bench["by_method"].values() if v[device]]
        top = max((v["eff"] for v in meds), default=0.0)
        kept = sorted(v["sigma"] for v in meds if v["eff"] >= 0.5 * top)
        L.append(macro(f"benchSpread{nm}Low", sig(kept[0]) if kept else "n/a"))
        L.append(macro(f"benchSpread{nm}High", sig(kept[-1]) if kept else "n/a"))
        L.append(macro(f"benchSpread{nm}N", len(kept)))
        lead = bench_leader(bench, device)
        L.append(macro(f"benchBest{nm}", tex_escape(ladder_id(lead["method"])) if lead else "n/a"))
        L.append(macro(f"benchBest{nm}Sigma", sig(lead["sigma"]) if lead else "n/a"))
        L.append(macro(f"benchBest{nm}Eff", f(lead["eff"], 3) if lead else "n/a"))
    # feedback
    for short, nm in (("C01", "COne"), ("C02", "CTwo"), ("C03", "CThree"), ("C13", "CThirteen")):
        s = fb[short]
        L.append(macro(f"fb{nm}Start", f(s[0]["sigma"], 1)))
        L.append(macro(f"fb{nm}End", f(s[-1]["sigma"], 2)))
        L.append(macro(f"fb{nm}Steps", len(s) - 1))
    # dynamics
    d1, d3 = dyn["C01"], dyn["C03"]
    L.append(macro("beadFc", f(d1["fc_hz"], 1)))
    L.append(macro("beadKappa", f(d1["kappa_pn_per_um"], 2)))
    L.append(macro("atomFc", f"{d3['fc_hz']:.0f}"))
    L.append(macro("atomOmega", f"{d3['omega_r_hz']:.0f}"))
    # models
    cg = models["cgh_net"]
    L.append(macro("cghN", cg["held_out_n"]))
    L.append(macro("cghMed", f(cg["ratio"]["median"], 3)))
    L.append(macro("cghQOne", f(cg["ratio"]["q1"], 3)))
    L.append(macro("cghQThree", f(cg["ratio"]["q3"], 3)))
    L.append(macro("cghNetMs", f(cg["network_ms"], 0)))
    L.append(macro("cghBudgetS", f(cg["budget_ms"] / 1000.0, 2)))
    L.append(macro("cghAcHybrid", f(cg["ac_hybrid"], 3)))
    L.append(macro("cghAcMnine", f(cg["ac_m19"], 3)))
    L.append(macro("cghBytes", f"{cg['onnx_bytes'] / 1e6:.2f}"))
    L.append(macro("cghSteps", cg["steps"]))
    L.append(macro("cghParity", f"{cg['parity_intensity']:.1e}".replace("e-0", "\\times 10^{-").replace("e-", "\\times 10^{-") + "}"))
    L.append(macro("cghLatticeRatio", f(cg["ratio_by_kind"]["lattice"], 3)))
    L.append(macro("cghRingRatio", f(cg["ratio_by_kind"]["ring"], 3)))
    L.append(macro("cghRandomRatio", f(cg["ratio_by_kind"]["random"], 3)))
    L.append(macro("cghMixedRatio", f(cg["ratio_by_kind"]["mixed"], 3)))
    L.append(macro("cghGfiveRatio", f(cg["ratio_by_kind"]["G5_lattice"], 3)))
    L.append(macro("cghPlaneRatio", f(cg["ratio_by_kind"]["M19_three_plane"], 3)))
    L.append(macro("cghShareAbove", f"{100 * cg['share_above']:.0f}"))
    two = models["cgh_net_2d"]
    L.append(macro("cghTwoDMed", f(two["ratio"]["median"], 4)))
    L.append(macro("cghTwoDN", two["held_out_n"]))
    ws = models["warmstart"]
    L.append(macro("wsModelIt", f"{ws['iters']['model']['median']:.0f}"))
    L.append(macro("wsRandomIt", f"{ws['iters']['random']['median']:.0f}"))
    L.append(macro("wsRatio", f(ws["ratio"], 2)))
    L.append(macro("wsControlIt", f"{ws['control']['random_nfix3'][0]:.0f}"))
    L.append(macro("wsControlNever", f"{100 * ws['control_never']['random_nfix3']:.0f}"))
    L.append(macro("wsModelNever", f"{100 * ws['control_never']['model_nfix3']:.0f}"))
    L.append(macro("wsEffDiff", f"{100 * ws['final_eff_diff']:.1f}"))
    L.append(macro("wsN", ws["held_out_n"]))
    L.append(macro("wsNfixModel", ws["n_fix_model"]))
    L.append(macro("wsNfixRandom", ws["n_fix_random"]))
    # sigma statistics over cases: M07 against M04 where both ran
    both = [(c["methods"]["M04"]["rel_std_pct"], c["methods"]["M07"]["rel_std_pct"]) for c in baked if "M04" in c["methods"] and "M07" in c["methods"]]
    L.append(macro("nBothFourSeven", len(both)))
    L.append(macro("medSigmaMfour", f(statistics.median(a for a, _ in both), 1)))
    L.append(macro("medSigmaMseven", f(statistics.median(b for _, b in both), 2)))
    effs = [(c["methods"]["M07"]["efficiency"]) for c in baked if "M07" in c["methods"]]
    L.append(macro("minEffMseven", f(min(effs), 3)))
    L.append(macro("maxEffMseven", f(max(effs), 3)))
    # readiness
    real = sum(1 for c in ready["contracts"] if c["state"] == "available")
    L.append(macro("nContracts", len(ready["contracts"])))
    L.append(macro("nContractsAvailable", real))
    others = [c for c in ready["contracts"] if c["state"] != "available"]
    state_words = {"partial": "partial", "training": "answered by its baseline, with no released model", "missing": "missing"}
    L.append(macro("readinessOthers", "; ".join(
        f"\\texttt{{{tex_escape(c['id'])}}} is {state_words.get(c['state'], c['state'])}"
        + (f" ({tex_escape(c['reason'].rstrip('.'))})" if c["reason"] else "")
        for c in others)))
    (HERE / "studio_numbers.tex").write_text("".join(L), encoding="utf-8")

    (HERE / "table_ladder.tex").write_text(table_ladder(ladder), encoding="utf-8")
    (HERE / "table_acceptance.tex").write_text(table_acceptance(), encoding="utf-8")
    (HERE / "table_cases.tex").write_text(table_cases(cases), encoding="utf-8")
    (HERE / "table_calibration.tex").write_text(table_calibration(cases), encoding="utf-8")
    (HERE / "table_results.tex").write_text(table_results(cases), encoding="utf-8")
    (HERE / "table_benchmark.tex").write_text(table_benchmark(bench), encoding="utf-8")
    (HERE / "table_bench_methods.tex").write_text(table_bench_methods(bench), encoding="utf-8")
    print("wrote studio.json, studio_numbers.tex and 7 tables;", "tiers", tiers, "cases", len(cases), "baked", len(baked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
