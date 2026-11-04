#!/usr/bin/env python3
"""Regenerate the figures of the B1 and B2 manuscript from ``data/beyond.json`` (written by ``data/measure.py``).

  fig-b1.pdf  (a) trap intensities of one hologram on the crosstalk device, phase-fixed WGS and B1, sorted;
              (b) relative standard deviation per seed for the baselines and for B1 with and without the device model.
  fig-b2.pdf  (a) intensity of the worst moving trap along the 13-frame sequence, B2 and linear phase interpolation;
              (b) minimum transient intensity of the moving traps against the number of frames, per seed.
  fig-b1-model.pdf     (a) transfer function of the crosstalk kernel of the device model; (b) spread of B1 per outer iteration.
  fig-b1-tradeoff.pdf  efficiency against spread per seed for the baselines and B1 on the crosstalk device.
  fig-bench.pdf        factor and efficiency ratio of B1 over phase-fixed WGS on each geometry of the studio's benchmark.
  fig-ablation.pdf     (a) spread of each B1 variant per seed; (b) minimum transient ratio of each B2 variant per seed.
  fig-b2-theory.pdf    (a) closed-form intensity of a trap read half way between two shifted frames; (b) frames a move needs.
  fig-b2-long.pdf      minimum transient ratio of B2 and linear phase interpolation on the long moves, per seed.

Run from the repository root after the measurement:  python manuscripts/device-aware-flicker-bounded/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment).
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


def load() -> dict:
    return json.loads((DATA / "beyond.json").read_text(encoding="utf-8"))


def fig_b1(d: dict) -> None:
    rows = d["bs1_crosstalk"]["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1, 1.25]})
    r0 = rows[0]
    for key, col, lab in (("ratios_M07", ORANGE, "phase-fixed WGS (M07)"), ("ratios_B1", BLUE, "device-aware WGS (B1)")):
        v = np.sort(np.array(r0[key]))
        axs[0].plot(np.arange(len(v)), v, ".", ms=3.5, color=col, label=lab)
    axs[0].axhline(1.0, color=INK, lw=0.7, ls="--")
    axs[0].set_xlabel("trap, sorted by intensity")
    axs[0].set_ylabel("trap intensity / mean")
    axs[0].set_title("(a) one hologram, seed 1, crosstalk device", fontsize=8)
    axs[0].legend(fontsize=6.8, frameon=False, loc="upper left")
    axs[0].grid(True, color=GRID, lw=0.5)
    series = [("M07_30", ORANGE, "M07, 30 it."), ("M07_100", "#f2b27c", "M07, 100 it."),
              ("M04_30", GRID, "GS (M04)"), ("M06_30", PURPLE, "WGS (M06)")]
    x = np.arange(len(rows))
    w = 0.14
    for k, (key, col, lab) in enumerate(series):
        axs[1].bar(x + (k - 2) * w, [r["baselines"][key]["sigma"] for r in rows], w, color=col, edgecolor=INK, lw=0.4, label=lab)
    axs[1].bar(x + 2 * w, [r["B1_no_device_model"]["sigma"] for r in rows], w, color=GREEN, edgecolor=INK, lw=0.4, label="B1, device model removed")
    axs[1].bar(x + 3 * w, [r["B1"]["sigma"] for r in rows], w, color=BLUE, edgecolor=INK, lw=0.4, label="B1")
    axs[1].set_yscale("log")
    axs[1].set_xticks(x, [f"seed {r['seed']}" for r in rows], fontsize=7)
    axs[1].set_ylabel("relative standard deviation (%)")
    axs[1].set_title("(b) per seed, scored on the device", fontsize=8)
    axs[1].legend(fontsize=6, frameon=False, ncol=2, loc="upper center")
    axs[1].set_ylim(5e-2, 5e3)
    fig.tight_layout()
    fig.savefig(HERE / "fig-b1.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_b2(d: dict) -> None:
    runs = d["bs2"]["runs"]
    r0 = next(r for r in runs if "curve_b2" in r)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw={"width_ratios": [1.3, 1]})
    for key, col, lab in (("curve_lpi", ORANGE, "linear phase interpolation"), ("curve_b2", BLUE, "flicker-bounded sequence (B2)")):
        c = np.array(r0[key])
        axs[0].plot(np.linspace(0, r0["frames"] - 1, len(c)), c, color=col, lw=1.1, label=lab)
    axs[0].axhline(0.9, color=INK, lw=0.7, ls=":")
    axs[0].set_xlabel("frame index (sub-frames between frames)")
    axs[0].set_ylabel("trap intensity / its frame mean")
    axs[0].set_title("(a) lowest moving trap, seed 1, 13 frames", fontsize=8)
    axs[0].legend(fontsize=6.8, frameon=False, loc="lower center")
    axs[0].grid(True, color=GRID, lw=0.5)
    frames = sorted({r["frames"] for r in runs})
    for i, f in enumerate(frames):
        sel = [r for r in runs if r["frames"] == f]
        axs[1].plot([i - 0.12] * len(sel), [r["lpi_min"] for r in sel], "o", ms=3.5, color=ORANGE, label="LPI" if i == 0 else None)
        axs[1].plot([i + 0.12] * len(sel), [r["b2_min"] for r in sel], "s", ms=3.5, color=BLUE, label="B2" if i == 0 else None)
    axs[1].axhline(0.9, color=INK, lw=0.7, ls=":")
    axs[1].set_xticks(range(len(frames)), [str(f) for f in frames])
    axs[1].set_xlabel("frames in the sequence")
    axs[1].set_ylabel("minimum transient intensity ratio")
    axs[1].set_title("(b) every seed", fontsize=8)
    axs[1].legend(fontsize=7, frameon=False)
    axs[1].grid(True, color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-b2.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_b1_model(d: dict) -> None:
    dev = d["bs1_crosstalk"]["device"]
    sig_k, q = dev["crosstalk"]
    rows = d["bs1_crosstalk"]["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    k = np.linspace(0, 1.5, 300)
    axs[0].plot(k, np.exp(-(k**q) / sig_k**q), color=BLUE, lw=1.3, label="transfer function, $k_y=0$")
    axs[0].plot(k, np.exp(-(2 * k**q) / sig_k**q), color=ORANGE, lw=1.3, ls="--", label="diagonal, $k_x=k_y$")
    axs[0].axhline(np.exp(-1), color=INK, lw=0.6, ls=":")
    axs[0].set_xlabel("spatial frequency $k$ (model units)")
    axs[0].set_ylabel("transfer of the phase")
    axs[0].set_title("(a) crosstalk kernel of the device model", fontsize=8)
    axs[0].legend(fontsize=6.8, frameon=False)
    axs[0].grid(True, color=GRID, lw=0.5)
    hist = rows[0]["B1_history_sigma"]
    axs[1].plot(range(1, len(hist) + 1), hist, "o-", color=BLUE, ms=4, lw=1.1, label="B1 after each outer iteration")
    axs[1].axhline(rows[0]["baselines"]["M07_30"]["sigma"], color=ORANGE, lw=1.0, ls="--", label="phase-fixed WGS, 30 iterations")
    axs[1].axhline(rows[0]["baselines"]["M07_100"]["sigma"], color=INK, lw=0.8, ls=":", label="phase-fixed WGS, 100 iterations")
    axs[1].set_yscale("log")
    axs[1].set_xticks(range(1, len(hist) + 1))
    axs[1].set_xlabel("outer iteration")
    axs[1].set_ylabel("relative standard deviation (%)")
    axs[1].set_title("(b) spread on the device, seed 1", fontsize=8)
    axs[1].legend(fontsize=6.5, frameon=False, loc="center right")
    axs[1].grid(True, color=GRID, lw=0.5, which="both")
    fig.tight_layout()
    fig.savefig(HERE / "fig-b1-model.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_b1_tradeoff(d: dict) -> None:
    rows = d["bs1_crosstalk"]["rows"]
    fig, ax = plt.subplots(figsize=(3.6, 2.9))
    spec = (("M07, 30 iterations", lambda r: r["baselines"]["M07_30"], ORANGE, "s"),
            ("M07, 100 iterations", lambda r: r["baselines"]["M07_100"], "#f2b27c", "D"),
            ("B1, device model removed", lambda r: r["B1_no_device_model"], GREEN, "^"),
            ("B1", lambda r: r["B1"], BLUE, "o"))
    for lab, get, col, mk in spec:
        ax.plot([get(r)["eff"] for r in rows], [get(r)["sigma"] for r in rows], mk, ms=4.5, color=col, mec=INK, mew=0.4, label=lab)
    ax.set_yscale("log")
    ax.set_xlabel("efficiency on the device")
    ax.set_ylabel("relative standard deviation (%)")
    ax.legend(fontsize=6.5, frameon=False, loc="center left")
    ax.grid(True, color=GRID, lw=0.5, which="both")
    fig.tight_layout()
    fig.savefig(HERE / "fig-b1-tradeoff.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_bench(d: dict) -> None:
    dev = d["benchmark_bs1"]["devices"]["device"]
    x = np.arange(len(dev))
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    fac = [r["factor"] for r in dev]
    axs[0].bar(x, fac, 0.6, color=[BLUE if f >= 2 else GRID for f in fac], edgecolor=INK, lw=0.5)
    axs[0].axhline(2.0, color=INK, lw=0.8, ls="--")
    axs[0].set_xticks(x, [r["geometry"] for r in dev])
    axs[0].set_ylabel("factor over phase-fixed WGS")
    axs[0].set_title("(a) spread factor, threshold 2", fontsize=8)
    axs[0].grid(True, axis="y", color=GRID, lw=0.5)
    eff = [r["eff_ratio"] for r in dev]
    axs[1].bar(x, eff, 0.6, color=[BLUE if e >= 0.9 else GRID for e in eff], edgecolor=INK, lw=0.5)
    axs[1].axhline(0.9, color=INK, lw=0.8, ls="--")
    axs[1].set_ylim(0.8, 1.1)
    axs[1].set_xticks(x, [r["geometry"] for r in dev])
    axs[1].set_ylabel("efficiency ratio to phase-fixed WGS")
    axs[1].set_title("(b) efficiency ratio, floor 0.9", fontsize=8)
    axs[1].grid(True, axis="y", color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-bench.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_ablation(d: dict) -> None:
    ab = d["ablation"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1))
    marks = ["o", "s", "^", "D", "v"]
    keys = ["full", "no_weights", "no_step", "no_guard", "no_model", "steps_1", "steps_6", "warm_only"]
    short = {"full": "all", "no_weights": "no weights", "no_step": "no phase step", "no_guard": "no safeguard", "no_model": "no model",
             "steps_1": "1 step", "steps_6": "6 steps", "warm_only": "start only"}
    for i, k in enumerate(keys):
        for j, r in enumerate(ab["b1_crosstalk"]["rows"]):
            hl = k == "full"
            axs[0].plot(i + (j - 2) * 0.07, r[k]["sigma"], marks[j % 5], ms=3.5, color=BLUE if hl else INK, mfc=BLUE if hl else "none", mew=0.7)
    axs[0].set_yscale("log")
    axs[0].set_xticks(range(len(keys)), [short[k] for k in keys], rotation=40, ha="right", fontsize=7)
    axs[0].set_ylabel("relative standard deviation (%)")
    axs[0].set_title("(a) B1 variants, one marker per seed", fontsize=8)
    axs[0].grid(True, color=GRID, lw=0.5, which="both")
    keys2 = ["full", "no_lock", "no_opt", "iters_1", "iters_3", "linear"]
    short2 = {"full": "all", "no_lock": "no lock", "no_opt": "no optimization", "iters_1": "1 iteration", "iters_3": "3 iterations",
              "linear": "linear profile"}
    for i, k in enumerate(keys2):
        for j, r in enumerate(ab["b2"]["rows"]):
            hl = k == "full"
            axs[1].plot(i + (j - 2) * 0.07, r[k]["min"], marks[j % 5], ms=3.5, color=BLUE if hl else INK, mfc=BLUE if hl else "none", mew=0.7)
    axs[1].axhline(0.9, color=INK, lw=0.7, ls=":")
    axs[1].set_xticks(range(len(keys2)), [short2[k] for k in keys2], rotation=40, ha="right", fontsize=7)
    axs[1].set_ylabel("minimum transient intensity ratio")
    axs[1].set_title("(b) B2 variants, one marker per seed", fontsize=8)
    axs[1].grid(True, color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-ablation.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_b2_theory(d: dict) -> None:
    sc = d["bs2_scope"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8))
    delta = np.linspace(0, 1.0, 300)
    axs[0].plot(delta, np.sinc(delta / 2) ** 2, color=BLUE, lw=1.3)
    axs[0].axhline(0.9, color=INK, lw=0.7, ls=":")
    axs[0].axvline(sc["claim_step_fu"], color=ORANGE, lw=1.0, ls="--", label="step bound of the claim")
    axs[0].axvline(sc["acceptance_peak_step"], color=GREEN, lw=1.0, ls="-.", label="peak step of the acceptance task")
    axs[0].set_xlabel(r"shift between two frames $\delta$ (Fourier units)")
    axs[0].set_ylabel(r"intensity read half way, $\mathrm{sinc}^2(\delta/2)$")
    axs[0].set_title("(a) closed form of the blend model", fontsize=8)
    axs[0].legend(fontsize=6.5, frameon=False, loc="lower left")
    axs[0].grid(True, color=GRID, lw=0.5)
    jerk = 15.0 / 8.0
    length = np.linspace(0.5, 16, 200)
    axs[1].plot(length, np.maximum(13, np.ceil(jerk * length / sc["claim_step_fu"] - 1e-9) + 1), color=BLUE, lw=1.3)
    pts = [("acceptance", 2.0, sc["acceptance_frames_for_move"]), ("12 bins", sc["long"]["12"]["fourier_units"], sc["long"]["12"]["frames"]),
           ("20 bins", sc["long"]["20"]["fourier_units"], sc["long"]["20"]["frames"]), ("C10", sc["c10"]["fourier_units"], sc["c10"]["frames"])]
    for (lab, x, y), mk in zip(pts, ["o", "s", "^", "D"]):
        axs[1].plot([x], [y], mk, ms=5, color=ORANGE, mec=INK, mew=0.5)
        axs[1].annotate(lab, (x, y), textcoords="offset points", xytext=(-5, 5), fontsize=6.5, ha="right")
    axs[1].set_xlabel("longest move (Fourier units)")
    axs[1].set_ylabel("frames")
    axs[1].set_title("(b) frames needed for the step bound", fontsize=8)
    axs[1].grid(True, color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-b2-theory.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_b2_long(d: dict) -> None:
    sc = d["bs2_scope"]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True)
    for ax, key, tag in zip(axs[:2], ("12", "20"), "ab"):
        rows = sc["long"][key]["rows"]
        x = np.arange(len(rows))
        ax.plot(x - 0.1, [r["lpi_enough"] for r in rows], "o", ms=4, color=ORANGE, mec=INK, mew=0.4, label="linear phase interpolation")
        ax.plot(x + 0.1, [r["enough"] for r in rows], "s", ms=4, color=BLUE, mec=INK, mew=0.4, label="B2")
        ax.axhline(0.9, color=INK, lw=0.7, ls=":")
        ax.set_xticks(x, [str(r["seed"]) for r in rows], fontsize=7)
        ax.set_xlabel("seed")
        ax.set_title(f"({tag}) lattice, {sc['long'][key]['bins']} bins, {sc['long'][key]['frames']} frames", fontsize=7.5)
        ax.grid(True, color=GRID, lw=0.5)
    c = sc["c10"]["rows"]
    x = np.arange(len(c))
    axs[2].plot(x - 0.15, [r["lpi_enough"] for r in c], "o", ms=4, color=ORANGE, mec=INK, mew=0.4)
    axs[2].plot(x - 0.05, [r["b2_enough"] for r in c], "s", ms=4, color=BLUE, mec=INK, mew=0.4)
    axs[2].plot(x + 0.05, [r["lpi_equal"] for r in c], "o", ms=4, color="white", mec=ORANGE, mew=0.9)
    axs[2].plot(x + 0.15, [r["b2_equal"] for r in c], "s", ms=4, color="white", mec=BLUE, mew=0.9)
    axs[2].axhline(0.9, color=INK, lw=0.7, ls=":")
    axs[2].set_xticks(x, [str(r["seed"]) for r in c], fontsize=7)
    axs[2].set_xlabel("seed")
    axs[2].set_title(f"(c) C10, {sc['c10']['frames']} frames (filled), 25 (open)", fontsize=7.5)
    axs[2].grid(True, color=GRID, lw=0.5)
    axs[0].set_ylabel("lowest moving trap, ratio to its mean")
    axs[0].legend(fontsize=6.2, frameon=False, loc="center left")
    fig.tight_layout()
    fig.savefig(HERE / "fig-b2-long.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    d = load()
    fig_b1(d)
    fig_b2(d)
    fig_b1_model(d)
    fig_b1_tradeoff(d)
    fig_bench(d)
    fig_b2_theory(d)
    fig_b2_long(d)
    if "ablation" in d:
        fig_ablation(d)
    print("figures written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
