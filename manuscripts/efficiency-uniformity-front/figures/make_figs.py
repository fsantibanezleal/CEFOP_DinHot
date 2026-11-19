#!/usr/bin/env python3
"""Regenerate the figures of the efficiency-uniformity continuation manuscript from ``data/b5.json`` (written by ``data/measure.py``).

  fig-front.pdf     (a) the continuation curves of every seed with the points of the published methods; (b) the same, enlarged near the
                    efficient end, with the seed-1 front joined by a line.
  fig-lambda.pdf    efficiency and uniformity along the weight lambda, every seed, with the saturation value of Proposition 1.
  fig-shift.pdf     (a) the total light the shifted target asks for, against lambda; (b) the efficiency reached against that total.
  fig-bound.pdf     the relative standard deviation of every front point against the bound of Proposition 3.
  fig-rivals.pdf    the front of seed 1 against the one-parameter fronts of the published methods on the same task.
  fig-ablation.pdf  the change of the hypervolume of every variant of the ablation, with its 95 percent interval.
  fig-bench.pdf     the stored front of each benchmark geometry against the union of the published points, at 30 and 100 iterations.
  fig-cost.pdf      the seconds of a front against the number of conjugate-gradient iterations it takes.
  fig-schedule.pdf  the efficiency along the front for three schedules of lambda and for the cold start.

Also written (``spread_cells``): ``tab_spread.tex`` and ``fig_numbers.tex``, the spread cells of the benchmark in which the continuation
ran (the ideal device and the device of the benchmark, the longest wall-clock row), read from ``data/derived/benchmark/results.json``;
the continuation's own record is its row against the best published row of each cell by ``extract_methods.cell_result``, kept apart from
the cell reading of the technical report; the text types none of their numbers.

Run from the repository root after the measurement:  python manuscripts/efficiency-uniformity-front/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment). Every figure is a vector PDF readable in grayscale: series differ by marker
and line style as well as by colour.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ROOT = HERE.parents[2]
INK = "#1a1a2e"
GRID = "#d8d8e0"
BLUE, ORANGE, GREEN, RED, PURPLE = "#1b6ca8", "#e07a3f", "#3fa34d", "#b23a48", "#7b4fa0"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200})
PUB = {"M04": ("Gerchberg-Saxton", "s", "#444444"), "M05": ("adaptive additive", "^", ORANGE), "M06": ("weighted GS", "D", GREEN),
       "M07": ("phase-fixed WGS", "v", PURPLE), "M09": ("direct search", "P", RED)}


def load() -> dict:
    return json.loads((DATA / "b5.json").read_text(encoding="utf-8"))


def grid(ax) -> None:
    ax.grid(True, color=GRID, lw=0.5)


def fig_front(d: dict) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, zoom in zip(axs, (False, True)):
        for k, r in enumerate(d["main"]):
            f = r["front"]
            ax.plot(f["e"], f["u"], "o-", ms=2.2, lw=0.6, color=BLUE, alpha=0.55, label="continuation curve, one seed" if k == 0 else None)
        for name, (lab, mk, col) in PUB.items():
            ax.plot([r["published"][name][0] for r in d["main"]], [r["published"][name][1] for r in d["main"]], mk, ms=5,
                    mfc="white" if lab != "direct search" else col, mec=col, color=col, label=lab)
        grid(ax)
        ax.set_xlabel("efficiency  e")
        ax.set_ylabel("uniformity  u")
    axs[0].set_title("(a) every seed", fontsize=8)
    axs[1].set_xlim(0.785, 0.842)
    axs[1].set_ylim(-0.02, 1.03)
    axs[1].set_title("(b) the efficient end", fontsize=8)
    axs[0].legend(fontsize=6.3, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(HERE / "fig-front.pdf")
    plt.close(fig)


def fig_lambda(d: dict) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    sat = d["analysis"]["lambda_saturation"]["mean"]
    for r in d["main"]:
        f = r["front"]
        axs[0].plot(f["lambda"], f["e"], "o-", ms=2, lw=0.6, color=BLUE, alpha=0.6)
        axs[1].plot(f["lambda"], f["u"], "s--", ms=2, lw=0.6, color=ORANGE, alpha=0.6)
    for ax, lab in zip(axs, ("efficiency  e", "uniformity  u")):
        ax.axvline(sat, color=INK, lw=0.8, ls=":")
        ax.set_xlabel(r"weight  $\lambda$")
        ax.set_ylabel(lab)
        grid(ax)
    axs[0].text(sat + 0.02, axs[0].get_ylim()[0] + 0.1 * (axs[0].get_ylim()[1] - axs[0].get_ylim()[0]), r"$\lambda^\ast$", fontsize=8)
    axs[0].set_title("(a) efficiency", fontsize=8)
    axs[1].set_title("(b) uniformity", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-lambda.pdf")
    plt.close(fig)


def fig_shift(d: dict) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    lam = np.linspace(0, 0.95, 200)
    ratio = 1.0 + lam / (2.0 * (1.0 - lam))
    axs[0].plot(lam, ratio, color=INK, lw=1.2)
    axs[0].axhline(1.0, color=GRID, lw=0.8)
    axs[0].set_ylim(0.9, 6.0)
    axs[0].set_xlabel(r"weight  $\lambda$")
    axs[0].set_ylabel(r"total of the shifted target / $e_0$")
    axs[0].set_title("(a) what the loss asks for", fontsize=8)
    grid(axs[0])
    for k, r in enumerate(d["main"]):
        f = r["front"]
        lm = np.array(f["lambda"])
        lm = np.where(lm < 1.0, lm, np.nan)
        tot = 1.0 + lm / (2.0 * (1.0 - lm))
        axs[1].plot(tot, np.array(f["e"]) / f["e0"], "o-", ms=2, lw=0.6, color=BLUE, alpha=0.6)
    axs[1].plot([1.0, 1.15], [1.0, 1.15], color=INK, lw=0.8, ls="--", label="what is asked")
    axs[1].set_xlim(0.99, 1.2)
    axs[1].set_ylim(0.98, 1.12)
    axs[1].set_xlabel(r"total of the shifted target / $e_0$")
    axs[1].set_ylabel(r"efficiency reached / $e_0$")
    axs[1].set_title("(b) what the hologram reaches", fontsize=8)
    axs[1].legend(fontsize=6.5, frameon=False, loc="upper left")
    grid(axs[1])
    fig.tight_layout()
    fig.savefig(HERE / "fig-shift.pdf")
    plt.close(fig)


def fig_bound(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    xs, ys = [], []
    for r in d["main"]:
        f = r["front"]
        bound = 100.0 * np.sqrt(np.array(f["E"])) * f["e0"] / np.array(f["e"])
        xs += list(bound)
        ys += list(f["sigma"])
    xs, ys = np.array(xs), np.array(ys)
    ax.loglog(xs, ys, "o", ms=2.2, color=BLUE, alpha=0.6, label="continuation points")
    lo, hi = min(xs.min(), ys.min()) * 0.8, max(xs.max(), ys.max()) * 1.2
    ax.plot([lo, hi], [lo, hi], color=INK, lw=0.9, ls="--", label="equality")
    ax.set_xlabel(r"bound  $100\sqrt{E}\,e_0/e$  (percent)")
    ax.set_ylabel(r"measured  $\sigma$  (percent)")
    ax.legend(fontsize=6.8, frameon=False, loc="upper left")
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-bound.pdf")
    plt.close(fig)


def fig_rivals(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    r0, rv = d["main"][0], d["rivals"][0]
    f = r0["front"]
    ax.plot(f["e"], f["u"], "o-", ms=3, lw=1.0, color=BLUE, label="continuation curve")
    for key, mk, col, lab in (("gsw_path", ".", GREEN, "weighted GS, iterates 1 to 100"),
                              ("pfwgs_path", "x", PURPLE, "phase-fixed WGS, iterates 1 to 100"),
                              ("gaa_sweep", "^", ORANGE, "adaptive additive, exponent 0 to 1")):
        p = np.array(rv[key])
        ax.plot(p[:, 0], p[:, 1], mk, ms=4, color=col, label=lab, ls="none")
    ax.set_xlabel("efficiency  e")
    ax.set_ylabel("uniformity  u")
    ax.set_xlim(0.72, 0.845)
    ax.set_ylim(0.0, 1.03)
    ax.legend(fontsize=6.3, frameon=False, loc="lower left")
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-rivals.pdf")
    plt.close(fig)


ABL_LABELS = [("n_lambda_5", "5 values"), ("n_lambda_10", "10 values"), ("n_lambda_40", "40 values"), ("cg_5", "5 steps"),
              ("cg_30", "30 steps"), ("quadratic", "quadratic schedule"), ("target", "target-spaced schedule"),
              ("cold", "cold start"), ("start_gs", "plain GS start"), ("start_random", "random start"), ("start_gsw100", "converged weighted GS start"),
              ("raw_loss", "unscaled loss")]


def fig_ablation(d: dict) -> None:
    ab = d["analysis"]["ablation"]
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    y = np.arange(len(ABL_LABELS))
    for k, (key, lab) in enumerate(ABL_LABELS):
        s = ab[key]["diff"]
        half = (s["ci_hi"] - s["ci_lo"]) / 2.0 if s["n"] > 1 else 0.0
        ax.errorbar(s["mean"], k, xerr=half, fmt="o", color=BLUE, ecolor=INK, capsize=2.5, ms=4, lw=0.9)
    ax.axvline(0, color=INK, lw=0.8, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([lab for _, lab in ABL_LABELS], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("change of the hypervolume against the reference continuation (mean, 95 percent interval)")
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-ablation.pdf")
    plt.close(fig)


def fig_bench(d: dict) -> None:
    st = d["stored"]["geometries"]
    geos = sorted({g["geometry"] for g in st})
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    w = 0.38
    for k, (budget, col, hat) in enumerate(((30, BLUE, ""), (100, ORANGE, "//"))):
        vals = {g["geometry"]: g["margin"] for g in st if g["budget"] == budget}
        ties = all(g["reading"].startswith("tie") for g in st if g["budget"] == budget)
        ax.bar([i + (k - 0.5) * w for i, g in enumerate(geos)], [vals.get(g, np.nan) for g in geos], w, color=col, hatch=hat,
               edgecolor=INK, lw=0.4, alpha=0.55 if ties else 1.0,
               label=f"{budget} iterations" + (" (every cell a tie)" if ties else ""))
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(len(geos)))
    ax.set_xticklabels(geos)
    ax.set_xlabel("benchmark geometry")
    ax.set_ylabel("continuation minus published union\n(hypervolume)")
    ax.legend(fontsize=7, frameon=False)
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-bench.pdf")
    plt.close(fig)


def fig_cost(d: dict) -> None:
    cfg = {"default": (20, 15), "n_lambda_5": (5, 15), "n_lambda_10": (10, 15), "n_lambda_40": (40, 15), "cg_5": (20, 5),
           "cg_30": (20, 30), "quadratic": (20, 15), "target": (20, 15), "cold": (20, 15), "start_gs": (20, 15),
           "start_random": (20, 15), "start_gsw100": (20, 15)}
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    xs, ys = [], []
    for name, (n, k) in cfg.items():
        for r in d["ablation"][name]:
            xs.append(n * k)
            ys.append(r["seconds"])
    xs, ys = np.array(xs, float), np.array(ys, float)
    ax.plot(xs, ys, "o", ms=3, color=BLUE, alpha=0.6, label="one run")
    tm = d["analysis"]["time_model"]
    xx = np.linspace(0, xs.max() * 1.05, 50)
    ax.plot(xx, tm["slope"] * xx + tm["intercept"], color=INK, lw=1.0, ls="--", label="least squares")
    ax.set_xlabel("values of $\\lambda$ times steps per value")
    ax.set_ylabel("seconds (one thread)")
    ax.legend(fontsize=7, frameon=False)
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-cost.pdf")
    plt.close(fig)


def fig_schedule(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    for key, mk, col, lab in (("default", "o", BLUE, "linear"), ("quadratic", "s", ORANGE, "quadratic"),
                              ("target", "^", GREEN, "target-spaced"), ("cold", "x", RED, "cold start, linear")):
        r = d["ablation"][key][0]
        ax.plot(r["e"], r["u"], mk + "-", ms=3, lw=0.7, color=col, label=lab)
    ax.set_xlabel("efficiency  e")
    ax.set_ylabel("uniformity  u")
    ax.set_xlim(0.78, 0.845)
    ax.set_ylim(-0.02, 1.03)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left")
    grid(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-schedule.pdf")
    plt.close(fig)


def join_and(items: list[str]) -> str:
    """``G1``, ``G1 and G2``, ``G3, G4 and G6a``; ``none`` for an empty list."""
    if not items:
        return "none"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def spread_cells() -> None:
    """The spread cells of the benchmark in which the continuation ran: the longest wall-clock row, default parameters, on the ideal
    device and on the device of the benchmark (the continuation has no device model; every hologram is scored against its device).

    Two readings of each cell are kept apart.  The cell reading is the technical report's: the best proposed method of any kind against
    the best published one (``extract_methods.cell_result`` over every row of the cell).  The record of the continuation is its own
    row against the best published row of the cell, by the same rule (``cell_result`` over the published rows plus the continuation's
    row): ``proposed`` is a win, ``published`` a loss, ``tie`` a tie.  The text, the abstract, the title and the table print the record
    of the continuation; the cell reading appears only where it differs and says which proposed method sets it.  The win rule needs at
    least 5 seeds on both sides, interquartile ranges that do not overlap and a gap of at least 0.01 percentage points; a row whose median
    time exceeds ``OVER_BUDGET_FACTOR`` times its budget is never a best and never part of a win.  The continuation is the method B5 of the
    benchmark file; its result in a time row is the knee hologram of a curve that the deadline cuts."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(HERE.parents[1] / "holographic-trap-studio" / "data"))
    import extract_methods as X  # noqa: PLC0415

    res = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    X.require_contract(res, "efficiency-uniformity make_figs.py")
    t_read = max(res["protocol"]["budgets"]["time_s"])
    names = {g["id"]: g["name"]["en"] for g in res["geometries"]}
    devices = (("ideal", "Ideal device", ""), ("device", "Device of the benchmark", "Dev"))
    record: dict[str, list[dict]] = {}
    for dev, _, _ in devices:
        rows = [x for x in res["rows"] if x["budget_kind"] == "time" and x["budget"] == t_read and x["params"] == "default" and x["device"] == dev]
        cells = []
        for g in names:
            cell = [x for x in rows if x["geometry"] == g]
            b5 = next((x for x in cell if x["method"] == "B5"), None)
            if b5 is None:
                continue
            own = X.cell_result([x for x in cell if X.kind_of(x["method"]) == "published"] + [b5])
            kind = {"proposed": "wins", "published": "loses", "tie": "tie"}[own["result"]]
            cells.append({"g": g, "b5": b5, "own": own, "kind": kind, "cell": X.cell_result(cell), "by": {x["method"]: x for x in cell}})
        record[dev] = cells
    L = ["% Generated by figures/make_figs.py from the benchmark results. Do not edit.\n"]

    def mac(name: str, value) -> None:
        L.append(f"\\newcommand{{\\{name}}}{{{value}}}\n")

    mac("spreadBudget", f"{t_read:g}")
    mac("spreadOverFactor", f"{X.OVER_BUDGET_FACTOR:g}")
    for dev, _, tag in devices:
        cells = record[dev]
        wins = [c for c in cells if c["kind"] == "wins"]
        losses = [c for c in cells if c["kind"] == "loses"]
        ties = [c for c in cells if c["kind"] == "tie"]
        mac(f"spread{tag}Cells", len(cells))
        mac(f"spread{tag}Wins", len(wins))
        mac(f"spread{tag}WinList", join_and([c["g"] for c in wins]))
        mac(f"spread{tag}Losses", len(losses))
        mac(f"spread{tag}LossList", join_and([c["g"] for c in losses]))
        mac(f"spread{tag}Ties", len(ties))
        mac(f"spread{tag}TieList", join_and([c["g"] for c in ties]))
        mac(f"spread{tag}OverN", sum(1 for c in cells if X.is_over_budget(c["b5"])))
        # the cell readings of the technical report (best proposed method of any kind), for comparison with the record above
        mac(f"spread{tag}CellWinList", join_and([c["g"] for c in cells if c["cell"]["result"] == "proposed"]))
        mac(f"spread{tag}CellLossList", join_and([c["g"] for c in cells if c["cell"]["result"] == "published"]))
        mac(f"spread{tag}CellTies", sum(1 for c in cells if c["cell"]["result"] == "tie"))
        # the wins and the losses, each with its numbers (a letter per cell, in the order of the geometries)
        for label, group in (("Win", wins), ("Loss", losses)):
            for letter, c in zip("AB", group):
                b5, pub, by = c["b5"], c["own"]["published"], c["by"]
                p = f"spread{tag}{label}{letter}"
                mac(f"{p}Geo", c["g"])
                mac(f"{p}Name", names[c["g"]])
                mac(f"{p}N", b5["n_seeds"])
                mac(f"{p}Sigma", X.sig(b5["rel_std_pct"]["median"]))
                mac(f"{p}Eff", f"{b5['efficiency']['median']:.3f}")
                mac(f"{p}Sec", f"{b5['time_s']['median']:.2f}")
                mac(f"{p}PubName", X.RUN[pub["method"]])
                mac(f"{p}PubN", pub["n_seeds"])
                mac(f"{p}PubSigma", X.sig(pub["rel_std_pct"]["median"]))
                mac(f"{p}PubEff", f"{pub['efficiency']['median']:.3f}")
                w = by.get("M06")
                mac(f"{p}WgsEff", f"{w['efficiency']['median']:.3f}" if w else "n/a")
                mac(f"{p}WgsSigma", X.sig(w["rel_std_pct"]["median"]) if w else "n/a")
                cprop = c["cell"]["proposed"]
                mac(f"{p}CellRead", c["cell"]["result"])
                mac(f"{p}CellBy", X.RUN[cprop["method"]] if cprop else "none")
                mac(f"{p}CellBySigma", X.sig(cprop["rel_std_pct"]["median"]) if cprop else "n/a")
                mac(f"{p}CellByN", cprop["n_seeds"] if cprop else "n/a")
    (HERE / "fig_numbers.tex").write_text("".join(L), encoding="utf-8", newline="\n")
    T = ["\\begin{tabular}{@{}l r r r r l r r r l@{}}\n\\toprule\n",
         "Geometry & $n$ & $\\sigma$ (\\%) & $e$ & $t$ (s) & Best published method & $n$ & $\\sigma$ (\\%) & $e$ & Record \\\\\n"]
    for dev, title, _ in devices:
        T.append(f"\\midrule\n\\multicolumn{{10}}{{@{{}}l}}{{\\textit{{{title}}}}} \\\\\n")
        for c in record[dev]:
            g, b5, pub = c["g"], c["b5"], c["own"]["published"]
            head = f"{g} {names[g]} & {b5['n_seeds']} & {X.sig(b5['rel_std_pct']['median'])} & {b5['efficiency']['median']:.3f} & {b5['time_s']['median']:.2f} & "
            if pub is None:
                T.append(head + "none within budget & & & & tie \\\\\n")
                continue
            T.append(head + f"{X.RUN[pub['method']]} & {pub['n_seeds']} & {X.sig(pub['rel_std_pct']['median'])} & "
                     f"{pub['efficiency']['median']:.3f} & {c['kind']} \\\\\n")
    T.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_spread.tex").write_text("".join(T), encoding="utf-8", newline="\n")
    print("wrote spread_cells")


def main() -> int:
    d = load()
    for fn in (fig_front, fig_lambda, fig_shift, fig_bound, fig_rivals, fig_ablation, fig_bench, fig_cost, fig_schedule):
        fn(d)
        print("wrote", fn.__name__)
    spread_cells()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
