#!/usr/bin/env python3
"""Regenerate the figures of the DinHot technical report from the COMMITTED artifacts.

  fig-pipeline.pdf  the computation chain of a case (schematic, no data).
  fig-cases.pdf     relative standard deviation of the trap intensities, every method on every point-trap case (baked).
  fig-maps.pdf      phase mask and focal intensity of the phase-fixed WGS on C02, and of B1 on the device-limited C08.
  fig-feedback.pdf  emulated camera feedback: relative standard deviation against step, four cases.
  fig-learned.pdf   the learned models: cgh-net ratio by target kind, and the warm-start control.
  fig-bench.pdf     the benchmark: relative standard deviation at 100 iterations, every method on every geometry, ideal and C08.

Run from the repository root after ``data/extract.py``:  python manuscripts/holographic-trap-studio/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment has both; the pipeline environment has no matplotlib).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ROOT = HERE.parents[2]
DER = ROOT / "data" / "derived"

INK = "#1a1a2e"
GRID = "#d8d8e0"
BLUE, ORANGE, GREEN, RED, PURPLE = "#1b6ca8", "#e07a3f", "#3fa34d", "#b23a48", "#7b4fa0"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200})


def studio() -> dict:
    return json.loads((DATA / "studio.json").read_text(encoding="utf-8"))


def fig_pipeline() -> None:
    n_rows = len(studio()["ladder"])
    fig, ax = plt.subplots(figsize=(7.2, 2.1))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    boxes = [(1, "Case\nsetup, device,\ntarget, seed", BLUE), (21, f"Method\n({n_rows} methods)\nphase $\\phi_j$", ORANGE),
             (41, "Device\nquantizer, crosstalk,\nfill factor", PURPLE), (61, "Focal field\nFFT form,\npoint-trap form", GREEN),
             (81, "Metrics\n$e$, $u$, $\\sigma$,\nfeedback, bead", RED)]
    for x, label, col in boxes:
        ax.add_patch(FancyBboxPatch((x, 7), 17, 16, boxstyle="round,pad=0.4,rounding_size=1.2", fc="white", ec=col, lw=1.4))
        ax.text(x + 8.5, 15, label, ha="center", va="center", fontsize=7.6)
    for x in (18.8, 38.8, 58.8, 78.8):
        ax.annotate("", xy=(x + 2.4, 15), xytext=(x - 0.4, 15), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))
    ax.text(50, 2.2, "the same chain runs offline in Python (reference) and live in the browser (TypeScript port)",
            ha="center", fontsize=7.4, style="italic")
    fig.savefig(HERE / "fig-pipeline.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_cases() -> None:
    d = studio()
    cases = [c for c in d["cases"] if c["status"] == "baked" and c["target_kind"] == "traps"]
    methods = sorted({m for c in cases for m in c["methods"]}, key=lambda m: (m[0] != "M", m))
    grid = np.full((len(methods), len(cases)), np.nan)
    for j, c in enumerate(cases):
        for i, m in enumerate(methods):
            if m in c["methods"]:
                grid[i, j] = max(c["methods"][m]["rel_std_pct"], 1e-3)
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    im = ax.imshow(np.ma.masked_invalid(grid), aspect="auto", cmap="viridis_r", norm=LogNorm(vmin=1e-3, vmax=1e3))
    ax.set_xticks(range(len(cases)), [c["short"] for c in cases])
    ax.set_yticks(range(len(methods)), methods)
    ax.xaxis.tick_top()
    for i in range(len(methods)):
        for j in range(len(cases)):
            v = grid[i, j]
            if np.isfinite(v):
                txt = f"{v:.2g}" if v >= 0.01 else "<0.01"
                ax.text(j, i, txt, ha="center", va="center", fontsize=5.6, color="white" if v > 5 else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("relative standard deviation of the trap intensities (%)")
    ax.set_xlabel("case (blank: the method did not run on that case)")
    ax.xaxis.set_label_position("top")
    fig.savefig(HERE / "fig-cases.pdf", bbox_inches="tight")
    plt.close(fig)


def _u8(b64: str, n: int) -> np.ndarray:
    return np.frombuffer(base64.b64decode(b64), dtype=np.uint8).reshape(n, n)


def fig_maps() -> None:
    t2 = json.loads((DER / "C02_grid_feedback" / "trace.json").read_text(encoding="utf-8"))
    t8 = json.loads((DER / "C08_device_limited" / "trace.json").read_text(encoding="utf-8"))
    ph = _u8(t2["reference"]["phase_u8"], t2["grid"]["n_pix"]).astype(float) * 2 * np.pi / 256
    f2, f8 = t2["reference"]["focal"], t8["reference"]["focal"]
    m2 = _u8(f2["intensity_db_u8"], f2["size"]).astype(float)
    m8 = _u8(f8["intensity_db_u8"], f8["size"]).astype(float)
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    a = axs[0].imshow(ph, cmap="twilight", vmin=0, vmax=2 * np.pi)
    axs[0].set_title(f"(a) phase mask, {t2['reference']['method']}, C02", fontsize=8)
    fig.colorbar(a, ax=axs[0], fraction=0.046, pad=0.02, ticks=[0, np.pi, 2 * np.pi]).ax.set_yticklabels(["0", "$\\pi$", "$2\\pi$"])
    for ax, m, f, name, lab in ((axs[1], m2, f2, "C02", f"(b) focal intensity, {t2['reference']['method']}, C02"),
                                (axs[2], m8, f8, "C08", f"(c) focal intensity, {t8['reference']['method']}, C08")):
        ext = f["size"] * f["bin_um"] / 2
        im = ax.imshow(m / 255.0 * (-f["db_floor"]) + f["db_floor"], cmap="magma", vmin=f["db_floor"], vmax=0,
                       extent=(-ext, ext, ext, -ext))
        ax.set_title(lab, fontsize=8)
        ax.set_xlabel("x ($\\mu$m)")
    axs[1].set_ylabel("y ($\\mu$m)")
    fig.colorbar(im, ax=axs[2], fraction=0.046, pad=0.02).set_label("dB relative to the mean trap")
    for ax in axs[:1]:
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(HERE / "fig-maps.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_feedback() -> None:
    d = studio()
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for short, col in (("C01", BLUE), ("C02", ORANGE), ("C03", GREEN), ("C13", RED)):
        c = next(x for x in d["cases"] if x["short"] == short)
        steps = c["feedback"]
        ax.plot([s["step"] for s in steps], [s["sigma"] for s in steps], "o-", ms=3, lw=1.2, color=col,
                label=f"{short}, {c['n_traps']} traps")
    ax.set_yscale("log")
    ax.set_xlabel("feedback step")
    ax.set_ylabel("relative standard deviation (%)")
    ax.grid(True, color=GRID, lw=0.5)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "fig-feedback.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_learned() -> None:
    d = studio()["models"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw={"width_ratios": [1.5, 1]})
    kinds = d["cgh_net"]["ratio_by_kind"]
    order = ["lattice", "random", "mixed", "ring", "G5_lattice", "M19_three_plane"]
    labels = ["lattice", "random", "mixed", "ring", "5x5x3\nlattice", "5x5\nthree-plane"]
    vals = [kinds[k] for k in order]
    x = np.arange(len(order) + 2)
    axs[0].bar(x[:-2], vals, color=BLUE)
    axs[0].bar(x[-2], d["cgh_net"]["ratio"]["median"], color=GREEN)
    axs[0].bar(x[-1], d["cgh_net_2d"]["ratio"]["median"], color=RED)
    axs[0].axhline(1.0, color=INK, lw=0.8, ls="--")
    axs[0].set_xticks(x, labels + [f"all {d['cgh_net']['held_out_n']}\n(3 planes)", f"2D run\n({d['cgh_net_2d']['held_out_n']})"],
                      fontsize=6.6)
    axs[0].set_ylim(0.9, 1.22)
    axs[0].set_ylabel("accuracy ratio, network / baseline\nat equal wall-clock")
    axs[0].set_title("(a) cgh-net: volume (blue, green) and plane (red)", fontsize=8)
    ctl = d["warmstart"]["control"]
    names = ["random start\nfreeze 12", "random start\nfreeze 3", "network start\nfreeze 3"]
    meds = [ctl["random_nfix12"][0], ctl["random_nfix3"][0], ctl["model_nfix3"][0]]
    axs[1].bar(range(3), meds, color=[GRID, ORANGE, PURPLE], edgecolor=INK, lw=0.6)
    never = d["warmstart"]["control_never"]
    for i, k in enumerate(("random_nfix12", "random_nfix3", "model_nfix3")):
        axs[1].text(i, meds[i] + 0.5, f"{meds[i]:g}\n({100 * never[k]:.0f}% never)", ha="center", fontsize=6.6)
    axs[1].set_xticks(range(3), names, fontsize=6.6)
    axs[1].set_ylim(0, 26)
    axs[1].set_ylabel("median iterations to 1 percent")
    axs[1].set_title("(b) warm start: control subset", fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "fig-learned.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_bench() -> None:
    b = studio()["benchmark"]
    grid = b["grid_100"]
    geos = [g["id"] for g in b["geometries"]]
    methods = sorted({k.split("/")[0] for k in grid}, key=lambda m: (m.startswith("B"), m))
    label = {m: m for m in methods}
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 5.4), sharey=True)
    for ax, device, title in ((axs[0], "ideal", "(a) ideal device"), (axs[1], "device", "(b) C08 device")):
        z = np.full((len(methods), len(geos)), np.nan)
        for i, m in enumerate(methods):
            for j, g in enumerate(geos):
                v = grid.get(f"{m}/{g}/{device}")
                if v is not None:
                    z[i, j] = max(v, 1e-3)
        im = ax.imshow(np.ma.masked_invalid(z), aspect="auto", cmap="viridis_r", norm=LogNorm(vmin=1e-3, vmax=1e3))
        ax.set_xticks(range(len(geos)), geos)
        ax.set_title(title, fontsize=8)
        for i in range(len(methods)):
            for j in range(len(geos)):
                v = z[i, j]
                if np.isfinite(v):
                    txt = "<.001" if v <= 1e-3 else (f"{v:.0f}" if v >= 100 else f"{v:.2g}")
                    ax.text(j, i, txt, ha="center", va="center", fontsize=5.2,
                            color="white" if v > 5 else INK)
    axs[0].set_yticks(range(len(methods)), [label[m] for m in methods])
    cb = fig.colorbar(im, ax=axs, fraction=0.03, pad=0.02)
    cb.set_label("relative standard deviation at 100 iterations (%), median over the seeds")
    fig.text(0.42, 0.02, "geometry (blank: the method does not run there, or no device row)", ha="center", fontsize=7.4)
    fig.savefig(HERE / "fig-bench.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    fig_pipeline()
    fig_cases()
    fig_maps()
    fig_feedback()
    fig_learned()
    fig_bench()
    print("figures written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
