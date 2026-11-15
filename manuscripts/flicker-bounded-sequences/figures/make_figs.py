#!/usr/bin/env python3
"""Figures of the paper ``manuscripts/flicker-bounded-sequences``: every curve and marker is read from ``data/flicker.json``
(written by ``data/measure.py``); the only computed curves are the closed forms of the theory section (sinc^2 and the frame
count), drawn from the formulas of the paper with the step bound read from the same file.

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/flicker-bounded-sequences/figures/make_figs.py

Writes fig-theory, fig-curves, fig-frames, fig-steps, fig-bound, fig-long, fig-seconds and fig-ablation (PDF, vector).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE.parent / "data" / "flicker.json").read_text(encoding="utf-8"))

METHODS = ("b2", "lpi", "kim5", "kim10")
LABEL = {"b2": "flicker-bounded sequence", "lpi": "linear phase interpolation",
         "kim5": "per-frame GS, phase induction, 5 it.", "kim10": "per-frame GS, phase induction, 10 it."}
COLOR = {"b2": "#1b4f9c", "lpi": "#6b6b6b", "kim5": "#d9631e", "kim10": "#2a8f5a"}
MARK = {"b2": "o", "lpi": "s", "kim5": "^", "kim10": "v"}
LINE = {"b2": "-", "lpi": "--", "kim5": "-.", "kim10": ":"}

plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "figure.dpi": 150, "pdf.fonttype": 42, "axes.titlelocation": "left",
})


def save(fig, name: str) -> None:
    fig.savefig(HERE / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def sinc2_half(delta):
    x = np.asarray(delta) / 2.0
    return np.sinc(x) ** 2          # numpy sinc is sin(pi x) / (pi x)


def fig_theory() -> None:
    claim = DATA["long"]["claim_step_fu"]
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9))
    d = np.linspace(0, 1.2, 400)
    ax[0].plot(d, sinc2_half(d), color="#333333", lw=1.4, label=r"$\mathrm{sinc}^2(\delta/2)$, single trap")
    ax[0].axhline(0.9, color="#888888", ls=":", lw=1)
    ax[0].axvline(claim, color=COLOR["b2"], ls="--", lw=1, label=f"step bound {claim:g} Fourier units")
    pts = [("acceptance, 13 frames", DATA["accept"]["bound"]["peak_step_fu"], DATA["accept_summary"]["13"]["b2"]["transient_min_ratio"]["median"]),
           ("12-bin move", DATA["long"]["moves"]["12"]["peak_step_fu"], float(np.median([r["b2"]["transient_min_ratio"] for r in DATA["long"]["moves"]["12"]["rows"]]))),
           ("20-bin move", DATA["long"]["moves"]["20"]["peak_step_fu"], float(np.median([r["b2"]["transient_min_ratio"] for r in DATA["long"]["moves"]["20"]["rows"]]))),
           ("sort, 137 frames", DATA["c10"]["peak_step_fu"], float(np.median([r["bound"]["b2"]["transient_min_ratio"] for r in DATA["c10"]["rows"]]))),
           ("sort, 25 frames", DATA["c10"]["peak_step_equal"], float(np.median([r["equal"]["b2"]["transient_min_ratio"] for r in DATA["c10"]["rows"]])))]
    marks = ["o", "s", "D", "^", "v"]
    for (lab, x, y), m in zip(pts, marks):
        ax[0].plot([x], [y], m, color=COLOR["b2"], ms=5.5, mfc="white", mew=1.4, label=f"{lab}: median {y:.2f}")
    ax[0].set_xlabel("shift between two frames, $\\delta$ (Fourier units)")
    ax[0].set_ylabel("intensity read half way, fraction of frame")
    ax[0].set_title("(a) closed form and measured medians")
    ax[0].set_ylim(0.2, 1.03)
    ax[0].legend(loc="lower left", frameon=False, fontsize=6.6)
    L = np.linspace(0.2, 16, 200)
    f0 = DATA["long"]["default_frames"]
    ax[1].plot(L, np.maximum(f0, np.ceil(15 / 8 * L / claim) + 1), color=COLOR["b2"], lw=1.4, drawstyle="steps-post", label="frames $F(L)$ of the bound")
    used = DATA["figures"]["frames_vs_move"]
    for u, m in zip(used, marks):
        ax[1].plot([u["fourier_units"]], [u["frames_used"]], m, color="#222222", ms=5.5, mfc="white", mew=1.3, label=f"{u['move']}: {u['frames_used']} frames used")
    ax[1].set_xlabel("length of the longest move, $L$ (Fourier units)")
    ax[1].set_ylabel("frames")
    ax[1].set_title("(b) frames the bound requires")
    ax[1].legend(loc="upper left", frameon=False, fontsize=6.8)
    fig.tight_layout()
    save(fig, "fig-theory")


def fig_curves() -> None:
    cur = DATA["figures"]["transient_curves"]
    order = ("b2", "lpi", "kim5", "kim10")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.6), sharex=True, sharey=True)
    top = 1.05 * max(max(cur[m]["curve"]) for m in order)
    for ax, m, tag in zip(axes.ravel(), order, "abcd"):
        c = np.asarray(cur[m]["curve"])
        sub = cur[m]["substeps"]
        t = np.arange(len(c)) / sub
        ax.plot(t, c, color=COLOR[m], lw=1.3)
        ax.plot(t[::sub], c[::sub], MARK[m], color=COLOR[m], ms=3.8)
        ax.axhline(0.9, color="#888888", ls=":", lw=1)
        ax.set_title(f"({tag}) {LABEL[m]}")
        ax.set_ylim(0.0, top)
        ax.text(0.98, 0.04, f"lowest {c.min():.2f}", transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color=COLOR[m])
    for ax in axes[1]:
        ax.set_xlabel("frame index")
    for ax in axes[:, 0]:
        ax.set_ylabel("intensity / mean over frames")
    fig.tight_layout()
    save(fig, "fig-curves")


def fig_frames() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    off = {"b2": -0.9, "lpi": -0.3, "kim5": 0.3, "kim10": 0.9}
    for m in METHODS:
        rows = DATA["figures"]["ratio_vs_frames"][m]
        x = np.array([r["frames"] for r in rows], float)
        o = np.argsort(x)
        x = x[o]
        y = np.array([rows[i]["transient_min_ratio"] for i in o])
        lo = np.array([rows[i]["min"] for i in o])
        hi = np.array([rows[i]["max"] for i in o])
        ax.errorbar(x + off[m], y, yerr=[y - lo, hi - y], fmt=MARK[m] + LINE[m], color=COLOR[m], ms=5, lw=1.2, capsize=2.5, label=LABEL[m])
    ax.axhline(0.9, color="#888888", ls=":", lw=1)
    ax.axvline(DATA["accept"]["bound"]["frames_bound"], color="#444444", ls="--", lw=1)
    ax.text(DATA["accept"]["bound"]["frames_bound"] + 0.3, 0.12, "frames of the bound", fontsize=7.5, rotation=90, va="bottom")
    ax.set_xlabel("number of frames")
    ax.set_ylabel("transient minimum ratio of the moving traps")
    ax.set_xticks([7, 13, 25])
    ax.set_ylim(0.0, 1.02)
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout()
    save(fig, "fig-frames")


def fig_steps() -> None:
    steps = DATA["figures"]["phase_steps"]
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    rng = np.random.default_rng(0)
    for i, m in enumerate(METHODS):
        v = np.asarray(steps[m])
        x = i + (rng.random(len(v)) - 0.5) * 0.3
        ax.plot(x, v, MARK[m], color=COLOR[m], ms=5.5, mfc="white", mew=1.3)
        ax.hlines(np.median(v), i - 0.28, i + 0.28, color=COLOR[m], lw=2.2)
        ax.text(i + 0.31, np.median(v), f"median {np.median(v):.2f}", ha="left", va="center", fontsize=7.2, color=COLOR[m])
    ax.set_xticks(range(len(METHODS)))
    ax.set_xticklabels(["flicker-bounded\nsequence", "linear phase\ninterpolation", "per-frame GS\n5 iterations", "per-frame GS\n10 iterations"])
    ax.set_ylabel("largest phase step between frames (rad)")
    ax.set_ylim(0, max(max(v) for v in steps.values()) * 1.12)
    ax.set_xlim(-0.5, len(METHODS) - 0.1)
    fig.tight_layout()
    save(fig, "fig-steps")


def fig_bound() -> None:
    fv = DATA["figures"]["frames_vs_move"]
    claim = DATA["long"]["claim_step_fu"]
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    x = np.arange(len(fv))
    ax.bar(x - 0.2, [r["frames_bound"] for r in fv], 0.38, color="#c9d6ea", edgecolor="#1b4f9c", label="frames of the bound")
    ax.bar(x + 0.2, [r["frames_used"] for r in fv], 0.38, color="#1b4f9c", label="frames used")
    ax.set_xticks(x)
    ax.set_xticklabels([r["move"] for r in fv])
    ax.set_ylabel("frames")
    ax.set_ylim(0, 200)
    ax2 = ax.twinx()
    ax2.plot(x, [r["peak_step_fu"] for r in fv], "D", color="#d9631e", ms=6, mfc="white", mew=1.4, label="peak shift per frame")
    ax2.axhline(claim, color="#d9631e", ls="--", lw=1, label="step bound")
    ax2.set_ylabel("peak shift per frame (Fourier units)", color="#d9631e")
    ax2.set_ylim(0, 0.4)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=7.2, ncol=2)
    fig.tight_layout()
    save(fig, "fig-bound")


def fig_long() -> None:
    ls = DATA["figures"]["long_and_sort"]
    eq = {r["seed"]: r["equal"] for r in DATA["c10"]["rows"]}
    panels = [("(a) 12-bin move, %d frames" % DATA["long"]["moves"]["12"]["frames"], ls["12"]),
              ("(b) 20-bin move, %d frames" % DATA["long"]["moves"]["20"]["frames"], ls["20"]),
              ("(c) sort, %d frames" % DATA["c10"]["frames_bound"], ls["c10"]),
              ("(d) sort, %d frames" % DATA["c10"]["equal_frames"],
               [{"seed": s, **{m: eq[s][m]["transient_min_ratio"] for m in METHODS}} for s in sorted(eq)])]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), sharey=True)
    for ax, (title, rows) in zip(axes.ravel(), panels):
        seeds = [r["seed"] for r in rows]
        for m in METHODS:
            ax.plot(seeds, [r[m] for r in rows], MARK[m] + LINE[m], color=COLOR[m], ms=4.5, lw=1.0, label=LABEL[m])
        ax.axhline(0.9, color="#888888", ls=":", lw=1)
        ax.set_title(title)
        ax.set_xticks(seeds)
    for ax in axes[1]:
        ax.set_xlabel("seed")
    for ax in axes[:, 0]:
        ax.set_ylabel("transient minimum ratio")
    axes[0, 0].set_ylim(-0.02, 1.02)
    axes[0, 0].legend(loc="lower left", frameon=False, fontsize=6.6)
    fig.tight_layout()
    save(fig, "fig-long")
    # facts used in the text about panel (d): both per-frame sequences are above the sequence and above linear interpolation on every seed
    rows = panels[3][1]
    assert all(min(r["kim5"], r["kim10"]) > max(r["b2"], r["lpi"]) for r in rows), "text claim about panel (d) no longer holds"


def fig_seconds() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    for m in METHODS:
        rows = sorted(DATA["figures"]["seconds"][m], key=lambda r: r["frames"])
        ax.plot([r["frames"] for r in rows], [r["seconds"] for r in rows], MARK[m] + LINE[m], color=COLOR[m], ms=5, lw=1.2, label=LABEL[m])
    ax.set_xlabel("number of frames")
    ax.set_ylabel("seconds per sequence (median)")
    ax.set_xticks([7, 13, 25])
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    save(fig, "fig-seconds")


def fig_ablation() -> None:
    ab = DATA["figures"]["ablation"]
    names = {"full": "all components", "no_lock": "no trajectory\nlock", "no_opt": "no per-frame\noptimization", "iters_1": "1 iteration\nper frame",
             "iters_3": "3 iterations\nper frame", "linear": "linear time\nprofile"}
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    for i, k in enumerate(names):
        v = np.asarray(ab[k])
        x = i + (np.arange(len(v)) - (len(v) - 1) / 2) * 0.07
        ax.plot(x, v, "o", color=COLOR["b2"], ms=5, mfc="white", mew=1.3)
        ax.hlines(np.median(v), i - 0.3, i + 0.3, color=COLOR["b2"], lw=2.2)
        ax.text(i + 0.33, np.median(v), f"{np.median(v):.2f}", fontsize=7.5, va="center", color=COLOR["b2"])
    ax.axhline(0.9, color="#888888", ls=":", lw=1)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(list(names.values()), fontsize=7.5)
    ax.set_ylabel("transient minimum ratio of the moving traps")
    ax.set_ylim(0.55, 1.02)
    ax.set_xlim(-0.6, len(names) - 0.4)
    fig.tight_layout()
    save(fig, "fig-ablation")


if __name__ == "__main__":
    fig_theory()
    fig_curves()
    fig_frames()
    fig_steps()
    fig_bound()
    fig_long()
    fig_seconds()
    fig_ablation()
