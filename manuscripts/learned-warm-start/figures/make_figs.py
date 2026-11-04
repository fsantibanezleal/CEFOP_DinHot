#!/usr/bin/env python3
"""Regenerate the figures of the learned-warm-start manuscript from ``data/warm.json`` (written by ``data/measure.py``).

  fig-method.pdf    the pipeline: trap list, set network, trap phases, superposition start, phase-fixed WGS with the freeze index.
  fig-training.pdf  (a) training loss; (b) spread after the last unrolled iteration, network against random phases, per logged step.
  fig-ablation.pdf  (a) median iterations to 1 percent of the four arms with the bootstrap interval; (b) share of runs that never reach it.
  fig-ecdf.pdf      empirical distribution of the iterations to 1 percent over the 66 held-out geometries, four arms.
  fig-traces.pdf    median trap-intensity spread along the 60 iterations, four arms, with the interquartile band.
  fig-sweep.pdf     median iterations and share that never converge against the freeze index, random and network start.
  fig-oracle.pdf    iterations to 1 percent on ten geometries from a random start and from the phases of a converged run.
  fig-weights.pdf   spread of log g after each update against the cumulative allowance (Proposition 3), ten geometries.
  fig-paired.pdf    per geometry, iterations of the network start against the random start with the same freeze index, and against the default.

Run from the repository root after the measurement:  python manuscripts/learned-warm-start/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment). Grayscale-safe: each series differs in marker, line style and luminance.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
INK = "#1a1a2e"
GRID = "#d8d8e0"
# luminance-separated colours: dark blue, orange, mid green, light grey-purple
COL = {"R12": "#111111", "R3": "#c8641e", "N3": "#1b6ca8", "N12": "#7a9e3a"}
LAB = {"R12": "random start, $n_{fix}$=12 (default)", "R3": "random start, $n_{fix}$=3", "N3": "network start, $n_{fix}$=3", "N12": "network start, $n_{fix}$=12"}
MK = {"R12": "o", "R3": "s", "N3": "^", "N12": "D"}
LS = {"R12": "-", "R3": "--", "N3": "-.", "N12": ":"}
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200})


def load() -> dict:
    return json.loads((DATA / "warm.json").read_text(encoding="utf-8"))


def style(ax):
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)


def fig_method() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    ax.set_xlim(0, 100), ax.set_ylim(0, 34), ax.axis("off")
    boxes = [(1, "trap list\n$(x_m,y_m,z_m,w_m)$\n$M\\leq1024$ and mask", "#f0f0f0"),
             (21, "set network\n(two attention blocks,\nwidth 64, 4 heads)", "#cfd8e6"),
             (41, "trap phases\n$\\theta_m\\in(-\\pi,\\pi]$", "#f0f0f0"),
             (59, "superposition start\n$\\phi^{(0)}=\\arg\\sum_m\\sqrt{w_m}e^{i(\\Delta^m+\\theta_m)}$", "#f0f0f0"),
             (81, "phase-fixed WGS\n$g_0=1$, freeze at\n$n_{fix}$", "#e6d8cf")]
    for x, txt, fc in boxes:
        w = 17 if x != 59 else 20
        ax.add_patch(FancyBboxPatch((x, 9), w, 16, boxstyle="round,pad=0.4", fc=fc, ec=INK, lw=0.8))
        ax.text(x + w / 2, 17, txt, ha="center", va="center", fontsize=7.2)
    for x0, x1 in ((18.6, 20.4), (38.6, 40.4), (58.4, 58.6), (79.6, 80.4)):
        ax.annotate("", xy=(x1, 17), xytext=(x0, 17), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9))
    ax.text(50, 3.5, "training: unrolled phase-fixed WGS, loss $=$ mean of $\\log(\\sigma_k^2+0.01)$ over the iterations (no labels)", ha="center", fontsize=7.4)
    ax.text(50, 30.5, "the weights $g$ of the update are not an output of the network: they restart at 1", ha="center", fontsize=7.4, style="italic")
    fig.savefig(HERE / "fig-method.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_training(d: dict) -> None:
    t = d["training"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    st = np.array(t["step"])
    axs[0].plot(st, t["loss"], color="#888888", lw=0.5, label="batch loss")
    k = 10
    sm = np.convolve(t["loss"], np.ones(k) / k, mode="valid")
    axs[0].plot(st[k - 1:], sm, color=COL["N3"], lw=1.6, label=f"mean of {k} logs")
    axs[0].set_xlabel("training step"), axs[0].set_ylabel("loss (mean of log($\\sigma^2$+0.01))"), axs[0].legend(frameon=False, fontsize=7)
    style(axs[0])
    axs[1].semilogy(st, t["sig_random_last"], color=COL["R3"], lw=0.8, ls="--", label="random phases")
    axs[1].semilogy(st, t["sig_net_last"], color=COL["N3"], lw=0.8, label="network phases")
    axs[1].set_xlabel("training step"), axs[1].set_ylabel("median spread after 10 iterations (%)"), axs[1].legend(frameon=False, fontsize=7)
    style(axs[1])
    axs[0].set_title("(a)", loc="left", fontsize=8), axs[1].set_title("(b)", loc="left", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-training.pdf")
    plt.close(fig)


def fig_ablation(d: dict) -> None:
    A = d["arms"]
    order = ["R12", "R3", "N12", "N3"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    x = np.arange(len(order))
    med = [A[a]["iters_median"] for a in order]
    lo = [A[a]["iters_median"] - A[a]["iters_ci"][0] for a in order]
    hi = [A[a]["iters_ci"][1] - A[a]["iters_median"] for a in order]
    axs[0].bar(x, med, color=[COL[a] for a in order], edgecolor=INK, hatch="", width=0.6)
    axs[0].errorbar(x, med, yerr=[lo, hi], fmt="none", ecolor=INK, capsize=3, lw=1.0)
    axs[0].set_xticks(x, ["random\n$n_{fix}$=12", "random\n$n_{fix}$=3", "network\n$n_{fix}$=12", "network\n$n_{fix}$=3"], fontsize=7)
    axs[0].set_ylabel("median iterations to 1 % (95 % CI)")
    style(axs[0])
    nv = [100 * A[a]["never_runs"] for a in order]
    axs[1].bar(x, nv, color=[COL[a] for a in order], edgecolor=INK, width=0.6)
    axs[1].set_xticks(x, ["random\n$n_{fix}$=12", "random\n$n_{fix}$=3", "network\n$n_{fix}$=12", "network\n$n_{fix}$=3"], fontsize=7)
    axs[1].set_ylabel("runs never reaching 1 % (%)")
    style(axs[1])
    axs[0].set_title("(a)", loc="left", fontsize=8), axs[1].set_title("(b)", loc="left", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-ablation.pdf")
    plt.close(fig)


def fig_ecdf(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for a in ("R12", "R3", "N12", "N3"):
        v = np.sort(np.array(d["arms"][a]["iters_per_geo"]))
        ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=COL[a], ls=LS[a], lw=1.5, label=LAB[a])
    ax.axvline(d["budget"] + 0.5, color=INK, lw=0.6, ls=":")
    ax.set_xlabel("iterations to 1 % (61 = never within 60)"), ax.set_ylabel("share of the 66 geometries")
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    style(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-ecdf.pdf")
    plt.close(fig)


def fig_traces(d: dict) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    k = np.arange(1, d["budget"] + 1)
    for a in ("R12", "R3", "N12", "N3"):
        r = d["arms"][a]
        ax.fill_between(k, r["trace_q1"], r["trace_q3"], color=COL[a], alpha=0.10, lw=0)
        ax.semilogy(k, r["trace_median"], color=COL[a], ls=LS[a], lw=1.5, label=LAB[a])
    ax.axhline(1.0, color=INK, lw=0.7, ls=":")
    ax.set_xlabel("iteration"), ax.set_ylabel("trap-intensity spread $\\sigma$ (%)")
    ax.set_ylim(1e-4, 1e2)
    ax.legend(frameon=False, fontsize=6.5)
    style(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-traces.pdf")
    plt.close(fig)


def fig_sweep(d: dict) -> None:
    S = d["sweep"]
    nfs = [1, 2, 3, 4, 6, 8, 12]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    axs[0].errorbar(nfs, [S[str(n)]["iters_median"] for n in nfs], yerr=[[S[str(n)]["iters_median"] - S[str(n)]["iters_ci"][0] for n in nfs], [S[str(n)]["iters_ci"][1] - S[str(n)]["iters_median"] for n in nfs]],
                    color=COL["R3"], marker="s", ls="--", capsize=2, lw=1.2, label="random start")
    nn = [n for n in nfs if f"net{n}" in S]
    axs[0].errorbar(nn, [S[f"net{n}"]["iters_median"] for n in nn], yerr=[[S[f"net{n}"]["iters_median"] - S[f"net{n}"]["iters_ci"][0] for n in nn], [S[f"net{n}"]["iters_ci"][1] - S[f"net{n}"]["iters_median"] for n in nn]],
                    color=COL["N3"], marker="^", ls="-.", capsize=2, lw=1.2, label="network start")
    axs[0].set_xlabel("freeze index $n_{fix}$"), axs[0].set_ylabel("median iterations to 1 %"), axs[0].legend(frameon=False, fontsize=7)
    style(axs[0])
    axs[1].plot(nfs, [100 * S[str(n)]["never_runs"] for n in nfs], color=COL["R3"], marker="s", ls="--", lw=1.2, label="random start")
    axs[1].plot(nn, [100 * S[f"net{n}"]["never_runs"] for n in nn], color=COL["N3"], marker="^", ls="-.", lw=1.2, label="network start")
    axs[1].set_xlabel("freeze index $n_{fix}$"), axs[1].set_ylabel("runs that never reach 1 % (%)"), axs[1].legend(frameon=False, fontsize=7)
    style(axs[1])
    axs[0].set_title("(a)", loc="left", fontsize=8), axs[1].set_title("(b)", loc="left", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-sweep.pdf")
    plt.close(fig)


def fig_oracle(d: dict) -> None:
    o = d["oracle"]
    n = len(o["R12"])
    x = np.arange(n)
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    w = 0.16
    for j, (k, lab, col, hatch) in enumerate((("R12", "random, $n_{fix}$=12", "#111111", ""), ("O12", "oracle, $n_{fix}$=12", "#777777", "//"), ("R3", "random, $n_{fix}$=3", "#c8641e", ""),
                                               ("O3", "oracle, $n_{fix}$=3", "#e9b48a", "\\\\"), ("O1", "oracle, $n_{fix}$=1", "#1b6ca8", "xx"))):
        ax.bar(x + (j - 2) * w, o[k], w, color=col, edgecolor=INK, hatch=hatch, lw=0.5, label=lab)
    ax.set_xticks(x, [g.split("/")[1] for g in o["geometries"]], fontsize=7)
    ax.set_xlabel("held-out geometry (seed 301)"), ax.set_ylabel("iterations to 1 %")
    ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper left")
    ax.set_ylim(0, max(max(o[k]) for k in ("R12", "O12", "R3", "O3", "O1")) * 1.35)
    style(ax)
    fig.tight_layout()
    fig.savefig(HERE / "fig-oracle.pdf")
    plt.close(fig)


def fig_weights(d: dict) -> None:
    W = d["weights"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    for ax, arm, title in ((axs[0], "W12", "random start, $n_{fix}$=12"), (axs[1], "WO12", "oracle start, $n_{fix}$=12")):
        for i, r in enumerate(W[arm]):
            k = np.arange(2, 2 + len(r["S_at_k"]))
            ax.plot(k, r["cum_allow"], color="#999999", lw=0.7, ls="--", label="cumulative allowance $\\sum s_j$" if i == 0 else None)
            ax.plot(k, r["S_at_k"], color=COL["N3"], lw=1.0, label="spread $S_k$ of $\\log g$" if i == 0 else None)
        ax.set_xlabel("iteration $k$"), ax.set_title(title, fontsize=8)
        style(ax)
    axs[0].set_ylabel("log-spread")
    axs[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(HERE / "fig-weights.pdf")
    plt.close(fig)


def fig_paired(d: dict) -> None:
    A = d["arms"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    cap = d["budget"] + 1
    jit = np.random.default_rng(3).uniform(-0.25, 0.25, (2, len(A["N3"]["iters_per_geo"])))
    nets = np.array(A["N3"]["iters_per_geo"])
    for ax, other, lab, j in ((axs[0], "R3", "random start, $n_{fix}$=3", 0), (axs[1], "R12", "random start, $n_{fix}$=12 (default)", 1)):
        y = np.array(A[other]["iters_per_geo"])
        gen = np.arange(len(nets)) < 60
        ax.scatter(y[gen] + jit[j][gen], nets[gen] + jit[j][gen][::-1], s=14, marker="o", facecolor="none", edgecolor=COL["N3"], lw=0.8, label="generated")
        ax.scatter(y[~gen], nets[~gen], s=26, marker="^", color="#111111", label="benchmark")
        ax.plot([0.5, cap + 2], [0.5, cap + 2], color=INK, lw=0.7, ls=":")
        ax.set_xscale("log"), ax.set_yscale("log")
        ax.set_xlabel(f"iterations, {lab}"), ax.set_ylabel("iterations, network start, $n_{fix}$=3")
        style(ax)
    axs[0].legend(frameon=False, fontsize=7)
    axs[0].set_title("(a)", loc="left", fontsize=8), axs[1].set_title("(b)", loc="left", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-paired.pdf")
    plt.close(fig)


def main() -> None:
    d = load()
    fig_method()
    fig_training(d)
    fig_ablation(d)
    fig_ecdf(d)
    fig_traces(d)
    fig_sweep(d)
    fig_oracle(d)
    fig_weights(d)
    fig_paired(d)
    print("figures written to", HERE)


if __name__ == "__main__":
    main()
