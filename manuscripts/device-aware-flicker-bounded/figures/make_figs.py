#!/usr/bin/env python3
"""Regenerate the figures of the B1 and B2 manuscript from ``data/beyond.json`` (written by ``data/measure.py``).

  fig-b1.pdf  (a) trap intensities of one hologram on the crosstalk device, phase-fixed WGS and B1, sorted;
              (b) relative standard deviation per seed for the baselines and for B1 with and without the device model.
  fig-b2.pdf  (a) intensity of the worst moving trap along the 13-frame sequence, B2 and linear phase interpolation;
              (b) minimum transient intensity of the moving traps against the number of frames, per seed.

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


def main() -> int:
    d = load()
    fig_b1(d)
    fig_b2(d)
    print("figures written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
