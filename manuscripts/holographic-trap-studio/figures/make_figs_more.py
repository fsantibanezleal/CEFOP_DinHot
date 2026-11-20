#!/usr/bin/env python3
"""The second set of figures of the DinHot technical report, from the COMMITTED artifacts and formulas (called by ``make_figs.py``).

  fig-dataflow.pdf     the data flow of the build: source cases, the two contracts, the stages, the artifacts and the three lanes.
  fig-convergence.pdf  relative standard deviation against iteration from the baked traces: C02 (ideal device) and C08 (device).
  fig-device.pdf       the device model: crosstalk kernel, quantization efficiency and pixel-aperture envelope, from the formulas.
  fig-geometry.pdf     the spread by geometry: every method at 100 iterations, ideal and C08 device (benchmark medians).
  fig-pareto.pdf       the stored points of the efficiency-uniformity continuation in the benchmark against the single points of published methods.
  bench_deadline.tex and bench_deadline_table.tex: the deadline reading of the benchmark (the time rows over budget, tab:benchmark).
  fig-nfix.pdf         phase-fixed weighted GS: minimum spread against the freeze index, and iterations to 0.5 percent against weighted GS.

Run from the repository root:  python manuscripts/holographic-trap-studio/figures/make_figs.py   (it calls this module)
Deps: matplotlib, numpy.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from method_names import ID, RUN  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ROOT = HERE.parents[2]
DER = ROOT / "data" / "derived"

INK = "#1a1a2e"
GRID = "#d8d8e0"
BLUE, ORANGE, GREEN, RED, PURPLE = "#1b6ca8", "#e07a3f", "#3fa34d", "#b23a48", "#7b4fa0"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200})


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def studio() -> dict:
    return _load(DATA / "studio.json")


def fig_dataflow() -> None:
    d = studio()
    n_methods, n_cases = len(d["ladder"]), len(d["cases"])
    n_contracts = len(d["readiness"]["contracts"])
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(-2, 50)
    ax.axis("off")

    def box(x, y, w, h, text, col, fs=6.6):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.0", fc="white", ec=col, lw=1.3))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9))

    box(1, 36, 15, 11, f"Source cases\n({n_cases} records)\ncase library", BLUE)
    box(21, 36, 15, 11, "Contract 1\nparams-record\nschema and rules", PURPLE)
    box(41, 36, 17, 11, f"Stages\npreprocess, features,\ninfer ({n_methods} methods)", ORANGE)
    box(63, 36, 15, 11, "Gates\nlane, expected\nranges, units", RED)
    box(83, 36, 15, 11, "Contract 2\nindex, manifests,\ntraces", PURPLE)
    for x in (16.5, 36.5, 58.5, 78.5):
        arrow(x, 41.5, x + 4, 41.5)
    box(1, 19, 20, 10, "Training (offline, GPU)\ncgh-net, warm start,\nheld-out metrics", GREEN)
    bm = d["benchmark"]
    box(26, 19, 20, 10, f"Benchmark protocol\n{len(bm['geometries'])} geometries, {bm['seeds']} seeds,\nfronts, skipped cells", GREEN)
    box(51, 19, 22, 10, f"Committed artifacts\ndata/derived, models\n(readiness judges {n_contracts} rows)", BLUE)
    box(78, 19, 20, 10, "Readiness document\ncomputed from the\ncatalog: six states", PURPLE)
    arrow(90.5, 36, 62, 29.5)
    arrow(46.5, 24, 50.5, 24)
    arrow(21.5, 24, 25.5, 24)
    arrow(73.5, 24, 77.5, 24)
    box(3, 2, 26, 10, "Replay lane\nstatic site reads the\ncommitted artifacts", BLUE)
    box(37, 2, 26, 10, "Live lane\nTypeScript engine in a\nWeb Worker, parity-tested", ORANGE)
    box(71, 2, 26, 10, "API lane (dormant)\nGET only; 503 with the\ndeclared state", RED)
    for x0, x1 in ((62, 16), (62, 50), (62, 84)):
        arrow(x0, 18.6, x1, 12.6)
    fig.savefig(HERE / "fig-dataflow.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_convergence() -> None:
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.9))
    pick = lambda *keys: [ID[k] for k in keys]  # noqa: E731
    spec = [("C02_grid_feedback", pick("gs", "gaa", "wgs", "pfwgs", "wirtadam"), "C02: ideal device, 100 traps"),
            ("C08_device_limited", pick("gs", "wgs", "pfwgs", "cgmin", "crosstalkcg", "devicewgs"), "C08: crosstalk device, 4-bit phase")]
    cols = {ID["gs"]: GREEN, ID["gaa"]: "#8a8a8a", ID["wgs"]: ORANGE, ID["pfwgs"]: BLUE, ID["wirtadam"]: PURPLE,
            ID["cgmin"]: "#555555", ID["crosstalkcg"]: RED, ID["devicewgs"]: "#000000"}
    marks = {ID["gs"]: "o", ID["gaa"]: "s", ID["wgs"]: "^", ID["pfwgs"]: "v", ID["wirtadam"]: "D", ID["cgmin"]: "x",
             ID["crosstalkcg"]: "P", ID["devicewgs"]: "*"}
    for ax, (case, methods, title) in zip(axs, spec):
        t = _load(DER / case / "trace.json")
        for m in methods:
            if m not in t["methods"]:
                continue
            h = t["methods"][m]["history"]
            x = [r["iteration"] for r in h]
            y = [max(r["rel_std_pct"], 1e-4) for r in h]
            ax.plot(x, y, color=cols[m], marker=marks[m], markevery=max(1, len(x) // 6), ms=3.5, lw=1.0, label=RUN[m])
        ax.set_yscale("log")
        ax.set_xlabel("iteration")
        ax.set_title(title, fontsize=8)
        ax.grid(True, color=GRID, lw=0.5)
        ax.legend(fontsize=5.5, ncol=1, frameon=False)
    axs[0].set_ylabel("relative standard deviation (%)")
    fig.tight_layout()
    fig.savefig(HERE / "fig-convergence.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_device() -> None:
    m = _load(DER / "manifests" / "C08_device_limited.json")["params"]["device"]
    sigma, q, u, fill = m["crosstalk"]["sigma_per_px"], m["crosstalk"]["q"], m["upsample"], m["fill_factor"]
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.5))
    n = 96
    k = np.fft.fftfreq(n, d=1.0 / u)                      # cycles per SLM pixel on a grid of u samples per pixel
    h = np.exp(-(np.abs(k) ** q) / sigma ** q)
    ker = np.fft.fftshift(np.real(np.fft.ifft(h)))
    x = (np.arange(n) - n // 2) / u
    ker = ker / ker.sum()
    axs[0].plot(x, ker, color=BLUE, lw=1.2)
    axs[0].axvspan(-0.5, 0.5, color=GRID, alpha=0.6, lw=0)
    axs[0].set_xlim(-3, 3)
    axs[0].set_xlabel("offset (SLM pixels)")
    axs[0].set_ylabel("kernel (sum 1, one axis)")
    axs[0].set_title(f"(a) crosstalk kernel, $\\sigma$={sigma:g}, q={q:g}", fontsize=7.6)
    bits = np.arange(1, 9)
    eff = np.sinc(1.0 / 2.0 ** bits) ** 2
    axs[1].plot(bits, eff, color=ORANGE, marker="o", ms=3.5, lw=1.1)
    axs[1].axvline(m["bit_depth"], color=INK, ls=":", lw=0.8)
    axs[1].set_xlabel("phase bits")
    axs[1].set_ylabel("first-order efficiency")
    axs[1].set_title("(b) stepped grating, $\\mathrm{sinc}^2(1/N)$", fontsize=7.6)
    xx = np.linspace(0, 1, 200)
    for fl, ls in ((1.0, "-"), (fill, "--"), (0.64, ":")):
        axs[2].plot(xx, np.sinc(np.sqrt(fl) * xx / 2) ** 2, color=GREEN, ls=ls, lw=1.2, label=f"fill {fl:g}")
    axs[2].set_xlabel("position / half field")
    axs[2].set_ylabel("relative intensity")
    axs[2].legend(fontsize=6, frameon=False)
    axs[2].set_title("(c) pixel-aperture envelope", fontsize=7.6)
    for a in axs:
        a.grid(True, color=GRID, lw=0.5)
        a.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(HERE / "fig-device.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_geometry() -> None:
    d = studio()
    bench = d["benchmark"]
    lad = {r["id"]: r["tier"] for r in d["ladder"]}
    geos = list(bench["point_geometries"])
    methods = sorted({k.split("/")[0] for k in bench["grid_100"]})
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
    for ax, dev, title in zip(axs, ("ideal", "device"), ("(a) ideal device", "(b) C08 device")):
        for i, g in enumerate(geos):
            for j, m in enumerate(methods):
                v = bench["grid_100"].get(f"{m}/{g}/{dev}")
                if v is None:
                    continue
                prop = lad.get(m) == "beyond"
                ax.scatter(i + (0.14 if prop else -0.14) + 0.012 * (j % 7 - 3), max(v, 1e-3), s=14 if prop else 9,
                           marker="D" if prop else "o", color=ORANGE if prop else BLUE, alpha=0.8, lw=0)
        ax.set_yscale("log")
        ax.set_xticks(range(len(geos)), geos)
        ax.set_xlabel("geometry")
        ax.set_title(title, fontsize=8)
        ax.grid(True, color=GRID, lw=0.5)
    axs[0].set_ylabel("median relative standard deviation (%)")
    axs[0].scatter([], [], marker="o", color=BLUE, s=9, label="published methods")
    axs[0].scatter([], [], marker="D", color=ORANGE, s=14, label="methods proposed here")
    axs[0].legend(fontsize=6, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(HERE / "fig-geometry.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_pareto() -> None:
    b = _load(DER / "benchmark" / "results.json")
    n_panels = len(b["pareto"])
    ncols = 4 if n_panels > 6 else 3
    nrows = -(-n_panels // ncols)
    fig, axs = plt.subplots(nrows, ncols, figsize=(7.4, 2.1 * nrows + 0.2), squeeze=False)
    marks = {ID["gs"]: ("o", GREEN), ID["gaa"]: ("s", "#8a8a8a"), ID["wgs"]: ("^", ORANGE), ID["directsearch"]: ("D", PURPLE)}
    for ax, fr in zip(axs.flat, b["pareto"]):
        pts = sorted(fr["points"], key=lambda p: p["lambda"])
        ax.plot([p["efficiency"] for p in pts], [p["uniformity"] for p in pts], color=BLUE, marker=".", ms=4, lw=1.0, label="continuation")
        for m, (mk, col) in marks.items():
            cell = [x for x in b["rows"] if x["method"] == m and x["geometry"] == fr["geometry"] and x["device"] == "ideal"
                    and x["budget_kind"] == "iterations" and x["budget"] == 100 and x["params"] == "default"]
            if cell:
                ax.scatter(cell[0]["efficiency"]["median"], cell[0]["uniformity"]["median"], marker=mk, color=col, s=16, label=RUN[m], zorder=3)
        ax.set_title(fr["geometry"], fontsize=8)
        ax.grid(True, color=GRID, lw=0.5)
        ax.tick_params(labelsize=6.5)
    for ax in axs.flat[n_panels:]:
        ax.axis("off")
    for ax in axs[-1]:
        ax.set_xlabel("efficiency")
    for ax in axs[:, 0]:
        ax.set_ylabel("uniformity")
    axs[0, 0].legend(fontsize=5.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(HERE / "fig-pareto.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_nfix() -> None:
    acc = {r["id"]: r["numbers"] for r in _load(DATA / "acceptance.json")["rows"]}
    sweep = acc[ID["pfwgs"]]["n_fix_sweep_min_rel_std_150"]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.5))
    ns = [int(k) for k in sweep]
    axs[0].plot(ns, [max(v, 1e-3) for v in sweep.values()], color=BLUE, marker="o", ms=4, lw=1.1)
    axs[0].axhline(0.5, color=RED, ls="--", lw=0.9)
    axs[0].text(ns[0], 0.6, "0.5 percent", color=RED, fontsize=6.5)
    axs[0].set_yscale("log")
    axs[0].set_xlabel("freeze index $N$")
    axs[0].set_ylabel("minimum $\\sigma$ in 150 iterations (%)")
    axs[0].set_title("(a) the source value stalls on this grid", fontsize=8)
    i7, i6 = acc[ID["pfwgs"]]["iterations_m07"], acc[ID["pfwgs"]]["iterations_m06"]
    w = 0.35
    xs = np.arange(len(i7))
    axs[1].bar(xs - w / 2, i6, w, color=ORANGE, label="weighted GS")
    axs[1].bar(xs + w / 2, i7, w, color=BLUE, label="phase-fixed weighted GS, $N = 60$")
    axs[1].set_xticks(xs, [f"seed {k + 1}" for k in xs])
    axs[1].set_ylabel("iterations to 0.5 percent")
    axs[1].set_title("(b) $50\\times30$ array", fontsize=8)
    axs[1].legend(fontsize=6.5, frameon=False)
    for a in axs:
        a.grid(True, color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-nfix.pdf", bbox_inches="tight")
    plt.close(fig)


def bench_deadline() -> None:
    """The deadline reading of the benchmark, from the committed results file and the win rule of ``data/extract_methods.py``.

    Writes ``bench_deadline.tex`` (macros: the time rows over budget, the optimal-transport and mixed-region rows of the shaped fields)
    and ``bench_deadline_table.tex`` (``tab:benchmark``: per geometry and device at the longest time row the best published and the best
    proposed method with spread, seeds and time, the reading with its reason, and the rows over budget). Nothing is typed: every figure
    is read from ``data/derived/benchmark/results.json`` and the rule is the one the extraction and the app share."""
    import extract_methods as em

    r = _load(DER / "benchmark" / "results.json")
    em.require_contract(r, "make_figs_more.py")
    rows = r["rows"]
    read_s = max(r["protocol"]["budgets"]["time_s"])
    short_s = min(r["protocol"]["budgets"]["time_s"])
    default = [x for x in rows if x["params"] == "default"]
    timed = [x for x in default if x["budget_kind"] == "time"]

    def at(b):
        return [x for x in timed if x["budget"] == b]

    def over(b):
        return [x for x in at(b) if em.is_over_budget(x)]

    names = {g["id"]: g["name"]["en"] for g in r["geometries"]}

    def dev(d):
        return "ideal" if d == "ideal" else "C08"

    out = ["% Generated by figures/make_figs_more.py from data/derived/benchmark/results.json. Do not edit.\n"]

    def mac(name, value):
        out.append("\\newcommand{\\" + name + "}{" + str(value) + "}\n")

    mac("dlRowsRead", len(at(read_s)))
    mac("dlOverRead", len(over(read_s)))
    mac("dlRowsShort", len(at(short_s)))
    mac("dlOverShort", len(over(short_s)))
    mac("dlFactor", f"{em.OVER_BUDGET_FACTOR:g}")
    mac("dlReadS", f"{read_s:g}")
    mac("dlShortS", f"{short_s:g}")
    kept = [x["time_s"]["median"] for x in at(read_s) if not em.is_over_budget(x)]
    mac("dlMaxKept", f"{max(kept):.2f}")
    mac("dlOverMethodsShort", len({x["method"] for x in over(short_s)}))
    mac("dlMethodsShort", len({x["method"] for x in at(short_s)}))
    parts = [f"{em.RUN[x['method']]} on {x['geometry']} ({x['time_s']['median']:.2f}~s)"
             for x in sorted(over(read_s), key=lambda y: (y["method"], y["geometry"], y["device"]))]
    if len(parts) > 1:
        listed = ", ".join(parts[:-1]) + " and " + parts[-1]
    else:
        listed = parts[0] if parts else "none"
    mac("dlOverList", listed)
    mac("dlOverDevices", " and ".join(sorted({dev(x["device"]) for x in over(read_s)})) or "none")

    # the cells: the reading, its reason, and the reading without the over-budget rule (does the rule change any cell?)
    cells, changed, with_over = [], 0, 0
    keep_rule = em.is_over_budget
    for g in r["geometries"]:
        for d in ("ideal", "device"):
            rs = [{**x, "budget_kind": "time"} for x in at(read_s) if x["geometry"] == g["id"] and x["device"] == d]
            if not rs:
                continue
            res = em.cell_result(rs)
            em.is_over_budget = lambda row: False
            free = em.cell_result(rs)["result"]
            em.is_over_budget = keep_rule
            ovr = [x for x in rs if em.is_over_budget(x)]
            with_over += bool(ovr)
            changed += free != res["result"]
            cells.append((g["id"], d, res, ovr))
    def joined(xs):
        xs = list(xs)
        return "none" if not xs else (xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1])

    for dd, dn in (("ideal", "Ideal"), ("device", "Device")):
        for kind in ("published", "proposed"):
            won = [(gid, res[kind]["method"]) for gid, d, res, ovr in cells if d == dd and res["result"] == kind]
            mac(f"dlWin{dn}{kind.capitalize()}Cells", joined(g for g, _ in won))
            mac(f"dlWin{dn}{kind.capitalize()}Methods", joined(dict.fromkeys(em.RUN[m] for _, m in won)))
    mac("dlCellsOver", with_over)
    mac("dlCellsChanged", changed)
    mac("dlCellsAll", len(cells))

    # the shaped fields: the optimal-transport seed and mixed-region amplitude freedom at the read row and at 100 iterations
    g7 = next(g["id"] for g in r["geometries"] if not g["n_traps"])
    for tag, m in (("Ot", ID["otmraf"]), ("Mraf", ID["mraf"])):
        for d, dn in (("ideal", "Ideal"), ("device", "Device")):
            for rowtag, kind, budget in (("One", "time", read_s), ("Hundred", "iterations", 100)):
                x = next((y for y in default if y["method"] == m and y["geometry"] == g7 and y["device"] == d
                          and y["budget_kind"] == kind and y["budget"] == budget), None)
                if x is None:
                    continue
                base = f"gs{tag}{dn}{rowtag}"
                mac(base + "Sig", em.sig(x["rel_std_pct"]["median"]))
                mac(base + "Eff", f"{x['efficiency']['median']:.3f}")
                mac(base + "Sec", f"{x['time_s']['median']:.3g}")
                mac(base + "N", x["n_seeds"])
    for d, dn in (("ideal", "Ideal"), ("device", "Device")):
        rs = [x for x in at(read_s) if x["geometry"] == g7 and x["device"] == d and not em.is_over_budget(x)
              and em.kind_of(x["method"]) == "published"]
        mac(f"gsFloor{dn}", f"{max(x['efficiency']['median'] for x in rs) / 2:.3f}")

    # the benchmark's replication of Schroff et al. (device-aware CG with pixel crosstalk) at the read row on the C08 device, the cells the
    # device-aware refinement wins: it starts cold, so the deadline limits it
    for gid, gtag in (("G1", "Gone"), ("G3", "Gthree")):
        x = next((y for y in at(read_s) if y["method"] == ID["crosstalkcg"] and y["geometry"] == gid and y["device"] == "device"), None)
        if x is not None:
            mac(f"sc{gtag}Sig", em.sig(x["rel_std_pct"]["median"]))
            mac(f"sc{gtag}Eff", f"{x['efficiency']['median']:.3f}")
            mac(f"sc{gtag}Iter", f"{x['iterations']['median']:.0f}")
            mac(f"sc{gtag}Eval", f"{x['evaluations']['median']:.0f}")
            mac(f"sc{gtag}Sec", f"{x['time_s']['median']:.2f}")
            mac(f"sc{gtag}N", x["n_seeds"])
        b = next((y for y in at(read_s) if y["method"] == ID["devicewgs"] and y["geometry"] == gid and y["device"] == "device"), None)
        if b is not None:
            mac(f"bo{gtag}Iter", f"{b['iterations']['median']:.0f}")

    # the quasi-periodic set on the C08 device: the proposed method of the cell
    g4 = next((c for c in cells if c[0] == "G4" and c[1] == "device"), None)
    if g4 is not None and g4[2]["proposed"] is not None:
        mac("gFourProposedName", em.RUN[g4[2]["proposed"]["method"]])
    # Zernike correction: its median time per hologram at 100 iterations over the point-trap geometries (the statistic of the per-method
    # table), and its slowest row at the read deadline
    point = [g["id"] for g in r["geometries"] if g["n_traps"]]
    for d, dn in (("ideal", "Ideal"), ("device", "Device")):
        xs = [y["time_s"]["median"] for y in default if y["method"] == ID["zernike"] and y["device"] == d and y["budget_kind"] == "iterations"
              and y["budget"] == 100 and y["geometry"] in point]
        if xs:
            import statistics
            mac(f"zernike{dn}Sec", f"{statistics.median(xs):.2f}")
    zr = [y for y in at(read_s) if y["method"] == ID["zernike"]]
    worst = max(zr, key=lambda y: y["time_s"]["median"])
    mac("zernikeReadMaxSec", f"{worst['time_s']['median']:.2f}")
    mac("zernikeReadMaxGeometry", worst["geometry"])

    short = {"the interquartile ranges overlap": "interquartile ranges overlap", "one kind has no row": "no proposed row",
             "every row of one kind is over its budget": "every row of one kind over budget"}
    tab = ["\\begin{table}[t]\\centering\\scriptsize\\setlength{\\tabcolsep}{3pt}\n",
           f"\\caption{{Benchmark at the {read_s:g}~s deadline, per geometry and device. For the published and the proposed kind, the method with the lowest "
           "median relative standard deviation $\\sigma$ (\\%) among those of the kind that reach at least half of the best median efficiency of the kind, with "
           "the seeds behind it ($n$) and its median wall clock per hologram in seconds. A row whose median wall clock exceeds "
           f"{em.OVER_BUDGET_FACTOR:g} times the budget is over budget: it is listed in the last column, and it is never a best and never part of a win. One kind wins "
           f"only if both have at least {em.WIN_MIN_SEEDS} seeds, their interquartile ranges do not overlap and their medians differ by at least "
           f"{em.WIN_MIN_DIFF_PCT} percentage points; otherwise the cell is a tie, and the reason is printed. Default parameters, medians over the "
           "seeds of each cell.}\\label{tab:benchmark}\n",
           "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{0.15\\textwidth} >{\\raggedright\\arraybackslash}p{0.25\\textwidth} "
           ">{\\raggedright\\arraybackslash}p{0.25\\textwidth} >{\\raggedright\\arraybackslash}p{0.14\\textwidth} "
           ">{\\raggedright\\arraybackslash}p{0.15\\textwidth}@{}}\\toprule Geometry and device & Published & Proposed & Reading & Over budget\\\\\\midrule\n"]

    def secs(t):
        return f"{t:.2g}" if t < 0.1 else f"{t:.2f}"

    def cell(b):
        if not b:
            return "n/a"
        return f"{em.RUN[b['method']]} {em.sig(b['rel_std_pct']['median'])} ($n={b['n_seeds']}$, {secs(b['time_s']['median'])}~s)"

    for gid, d, res, ovr in cells:
        label = f"{gid} {names[gid].split(' (')[0]}, {dev(d)}"
        reading = res["result"] if res["result"] != "tie" else f"tie ({short.get(res['reason'], res['reason'])})"
        ov = "; ".join(f"{em.RUN[x['method']]} {x['time_s']['median']:.2f}~s" for x in ovr) or "none"
        tab.append(f"{label} & {cell(res['published'])} & {cell(res['proposed'])} & {reading} & {ov}\\\\\n")
    tab.append("\\bottomrule\\end{tabular}\\end{table}\n")
    (HERE / "bench_deadline.tex").write_text("".join(out), encoding="utf-8")
    (HERE / "bench_deadline_table.tex").write_text("".join(tab), encoding="utf-8")


def split_fields() -> None:
    """Writes ``fields_<contract>.tex``, one longtable of ``data/appendix_fields.tex`` per file (the data file is read, never written), so that
    the appendix prints each table after the sentence that reads it and not after one paragraph that reads all six."""
    text = (DATA / "appendix_fields.tex").read_text(encoding="utf-8")
    chunks = [c for c in text.split("\\begingroup\\scriptsize\n") if c.strip()]
    for c in chunks:
        name = re.search(r"\\label\{tab:fields-([a-z-]+)\}", c).group(1)
        (HERE / f"fields_{name}.tex").write_text("\\begingroup\\scriptsize\n" + c, encoding="utf-8")
    print(len(chunks), "appendix tables split")


def main() -> int:
    bench_deadline()
    split_fields()
    fig_dataflow()
    fig_convergence()
    fig_device()
    fig_geometry()
    fig_pareto()
    fig_nfix()
    print("second set of figures written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
