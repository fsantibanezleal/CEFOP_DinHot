#!/usr/bin/env python3
"""Regenerate the figures of the Pareto-front manuscript from ``data/b5.json`` (written by ``data/measure.py``).

  fig-front.pdf     (a) the fronts of every seed with the points of the published methods; (b) the same, enlarged near the
                    efficient end, with the seed-1 front joined by a line.
  fig-lambda.pdf    efficiency and uniformity along the weight lambda, every seed, with the saturation value of Proposition 1.
  fig-shift.pdf     (a) the total light the shifted target asks for, against lambda; (b) the efficiency reached against that total.
  fig-bound.pdf     the relative standard deviation of every front point against the bound of Proposition 3.
  fig-rivals.pdf    the front of seed 1 against the one-parameter fronts of the published methods on the same task.
  fig-ablation.pdf  the change of the hypervolume of every variant of the ablation, with its 95 percent interval.
  fig-bench.pdf     the stored front of each benchmark geometry against the union of the published points, at 30 and 100 iterations.
  fig-cost.pdf      the seconds of a front against the number of conjugate-gradient iterations it takes.
  fig-schedule.pdf  the efficiency along the front for three schedules of lambda and for the cold start.

Run from the repository root after the measurement:  python manuscripts/efficiency-uniformity-front/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment). Every figure is a vector PDF readable in grayscale: series differ by marker
and line style as well as by colour.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
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
            ax.plot(f["e"], f["u"], "o-", ms=2.2, lw=0.6, color=BLUE, alpha=0.55, label="front, one seed" if k == 0 else None)
        for name, (lab, mk, col) in PUB.items():
            ax.plot([r["published"][name][0] for r in d["main"]], [r["published"][name][1] for r in d["main"]], mk, ms=5,
                    mfc="white" if name != "M09" else col, mec=col, color=col, label=lab)
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
    ax.loglog(xs, ys, "o", ms=2.2, color=BLUE, alpha=0.6, label="front points")
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
    ax.plot(f["e"], f["u"], "o-", ms=3, lw=1.0, color=BLUE, label="front by continuation")
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
    ax.set_xlabel("change of the hypervolume against the reference front (mean, 95 percent interval)")
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
        ax.bar([i + (k - 0.5) * w for i, g in enumerate(geos)], [vals.get(g, np.nan) for g in geos], w, color=col, hatch=hat,
               edgecolor=INK, lw=0.4, label=f"{budget} iterations")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(len(geos)))
    ax.set_xticklabels(geos)
    ax.set_xlabel("benchmark geometry")
    ax.set_ylabel("front minus published union (hypervolume)")
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


def main() -> int:
    d = load()
    for fn in (fig_front, fig_lambda, fig_shift, fig_bound, fig_rivals, fig_ablation, fig_bench, fig_cost, fig_schedule):
        fn(d)
        print("wrote", fn.__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
