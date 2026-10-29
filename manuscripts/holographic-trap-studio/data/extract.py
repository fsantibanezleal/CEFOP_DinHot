#!/usr/bin/env python3
"""Extract every number of the DinHot technical report from the committed files and write ``studio.json``, the macro file
``studio_numbers.tex`` and the table files ``table_*.tex``.

Run from the repository root (standard library only):

    python manuscripts/holographic-trap-studio/data/extract.py

Sources, all committed with the product:
  * ``docs/design/SDD.md``: the method ladder (id, tier, method, acceptance criterion).
  * ``data/derived/manifests/*.json`` and ``data/derived/C*/trace.json``: the baked cases (setup, device, per-method scores,
    feedback steps, bead and atom dynamics).
  * ``data/derived/benchmark/results.json``: the benchmark protocol and the cells measured so far. A cell that the file does
    not hold is reported as not yet measured; nothing is filled in.
  * ``data/derived/models/*.json`` and ``models/cgh-net.json``: the learned models and the measured negative of the
    warm-start model.
  * ``content/executive.json``: the published figures of the executive view, with their source ids.
  * ``data/derived/readiness.json``: what is real in the build.

``UNIT_ACCEPTANCE`` below is read from ``acceptance.json``, written by ``acceptance.py`` (run it first, same folder), which measures
the acceptance quantity of each method M01 to M19, BS-4 and BS-5 as its gate test computes it, on the current engine. The values
of BS-1 and BS-2 in the companion manuscript are measured by ``manuscripts/device-aware-flicker-bounded/data/measure.py``.
"""
from __future__ import annotations

import json
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

# Live-engine measurements quoted from the T1 unit report (wip/dinhot/t1-live-engine-2026-10-28.md, Summary and D4) and the
# lane budget of the design document (SDD, section Lanes). Source tag in the last field of each entry.
QUOTED_LIVE = {
    "liveFixtures": ("46", "T1 Summary"), "liveTests": ("104", "T1 Summary"), "liveWorst": (r"1.8\times 10^{-11}", "T1 Summary"),
    "liveGpuS": ("0.30 to 0.32", "T1 D4"), "liveCpuS": ("1.5 to 1.6", "T1 D4"), "liveAdapter": ("an integrated Intel gen-12lp adapter", "T1 D4"),
    "liveIterMs": ("24", "SDD Lanes"), "liveBudgetMs": ("1500", "SDD Lanes"), "liveTraceKiB": ("256", "SDD Lanes"),
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


def benchmark_summary() -> dict:
    r = load(DERIVED / "benchmark" / "results.json")
    rows = r["rows"]
    methods = sorted({x["method"] for x in rows})
    cells = {}
    for x in rows:
        if x["budget_kind"] == "iterations" and x["budget"] == 100:
            cells[f"{x['method']}/{x['geometry']}/{x['device']}"] = {
                "eff": x["efficiency"]["median"], "sigma": x["rel_std_pct"]["median"], "sigma_q1": x["rel_std_pct"]["q1"],
                "sigma_q3": x["rel_std_pct"]["q3"], "n_seeds": x["n_seeds"]}
    skipped = {}
    for s in r["skipped"]:
        skipped.setdefault(s["reason"]["en"], 0)
        skipped[s["reason"]["en"]] += 1
    all_methods = sorted({s["method"] for s in r["skipped"]} | set(methods))
    return {"schema": r["schema"], "engine_version": r["engine_version"], "grids": r["protocol"]["grids"],
            "seeds": r["protocol"]["seeds"], "budgets": r["protocol"]["budgets"], "geometries": r["geometries"],
            "rows": len(rows), "methods_measured": methods, "methods_in_protocol": all_methods,
            "skipped": len(r["skipped"]), "skipped_reasons": skipped, "cells_100": cells}


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
            "contracts": [{"id": c["id"], "state": c["state"], "provenance": c["provenance"]} for c in r["contracts"]]}


def macro(name: str, value) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


# ---------------------------------------------------------------------------------------------------- tables

def table_ladder(ladder: list[dict]) -> str:
    out = ["\\begin{longtable}{@{}p{0.07\\textwidth} p{0.14\\textwidth} p{0.34\\textwidth} p{0.40\\textwidth}@{}}\n",
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
           "\\caption{The thirteen cases: category, optical setup, target and the methods that ran in the bake. C11 is refused by the input contract and never computed.}\\label{tab:cases}\n",
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
        out.append(f"{c['short']} & {c['best_method']} & {f(b['efficiency'], 3)} & {f(b['rel_std_pct'], 2)} & "
                   f"{f(m7['rel_std_pct'], 2) if m7 else 'n/a'} & {f(m7['efficiency'], 3) if m7 else 'n/a'} & "
                   f"{f(m4['rel_std_pct'], 1) if m4 else 'n/a'}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


def table_benchmark(bench: dict) -> str:
    out = ["\\begin{table}[t]\\centering\\footnotesize\n",
           "\\caption{Benchmark cells measured so far in the committed results file (budget of 100 iterations, medians over the seeds). A cell absent from the file is not yet measured.}\\label{tab:benchmark}\n",
           "\\begin{tabular}{@{}l l l r r r@{}}\\toprule Method & Geometry & Device & Seeds & $e$ & $\\sigma$ (\\%)\\\\\\midrule\n"]
    for key, v in sorted(bench["cells_100"].items()):
        mth, geo, dev = key.split("/")
        out.append(f"{mth} & {geo} & {dev} & {v['n_seeds']} & {f(v['eff'], 3)} & {f(v['sigma'], 2)}\\\\\n")
    if not bench["cells_100"]:
        out.append("\\multicolumn{6}{c}{no cell at 100 iterations yet}\\\\\n")
    out.append("\\bottomrule\\end{tabular}\\end{table}\n")
    return "".join(out)


# ---------------------------------------------------------------------------------------------------- main

def main() -> int:
    ladder = parse_ladder()
    cases = case_summary()
    bench = benchmark_summary()
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
    for short, pre in (("C02", "atom"), ("C05", "bead"), ("C08", "devc")):
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
    L.append(macro("notBakedList", " and ".join(sorted(set(bench["methods_in_protocol"]) - set(engine_methods)))))
    for k, (v, _src) in QUOTED_LIVE.items():
        L.append(macro(k, v))
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
    (HERE / "studio_numbers.tex").write_text("".join(L), encoding="utf-8")

    (HERE / "table_ladder.tex").write_text(table_ladder(ladder), encoding="utf-8")
    (HERE / "table_acceptance.tex").write_text(table_acceptance(), encoding="utf-8")
    (HERE / "table_cases.tex").write_text(table_cases(cases), encoding="utf-8")
    (HERE / "table_calibration.tex").write_text(table_calibration(cases), encoding="utf-8")
    (HERE / "table_results.tex").write_text(table_results(cases), encoding="utf-8")
    (HERE / "table_benchmark.tex").write_text(table_benchmark(bench), encoding="utf-8")
    print("wrote studio.json, studio_numbers.tex and 6 tables;", "tiers", tiers, "cases", len(cases), "baked", len(baked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
