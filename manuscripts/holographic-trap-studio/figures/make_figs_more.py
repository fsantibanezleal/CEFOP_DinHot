#!/usr/bin/env python3
"""The second set of figures of the DinHot technical report, from the COMMITTED artifacts and formulas (called by ``make_figs.py``).

  fig-dataflow.pdf     the data flow of the build: source cases, the two contracts, the stages, the artifacts and the three lanes.
  fig-convergence.pdf  relative standard deviation against iteration from the baked traces: C02 (ideal device) and C08 (device).
  fig-device.pdf       the device model: crosstalk kernel, quantization efficiency and pixel-aperture envelope, from the formulas.
  fig-geometry.pdf     the spread by geometry: every method at 100 iterations, ideal and C08 device (benchmark medians).
  fig-pareto.pdf       the stored efficiency-uniformity fronts of the benchmark against the single points of published methods.
  fig-nfix.pdf         phase-fixed weighted GS: minimum spread against the freeze index, and iterations to 0.5 percent against M06.

Run from the repository root:  python manuscripts/holographic-trap-studio/figures/make_figs.py   (it calls this module)
Deps: matplotlib, numpy.
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
    spec = [("C02_grid_feedback", ["M04", "M05", "M06", "M07", "M11"], "C02: ideal device, 100 traps"),
            ("C08_device_limited", ["M04", "M06", "M07", "M10", "M13", "B1"], "C08: crosstalk device, 4-bit phase")]
    cols = {"M04": GREEN, "M05": "#8a8a8a", "M06": ORANGE, "M07": BLUE, "M11": PURPLE, "M10": "#555555", "M13": RED, "B1": "#000000"}
    marks = {"M04": "o", "M05": "s", "M06": "^", "M07": "v", "M11": "D", "M10": "x", "M13": "P", "B1": "*"}
    for ax, (case, methods, title) in zip(axs, spec):
        t = _load(DER / case / "trace.json")
        for m in methods:
            if m not in t["methods"]:
                continue
            h = t["methods"][m]["history"]
            x = [r["iteration"] for r in h]
            y = [max(r["rel_std_pct"], 1e-4) for r in h]
            ax.plot(x, y, color=cols[m], marker=marks[m], markevery=max(1, len(x) // 6), ms=3.5, lw=1.0, label=m)
        ax.set_yscale("log")
        ax.set_xlabel("iteration")
        ax.set_title(title, fontsize=8)
        ax.grid(True, color=GRID, lw=0.5)
        ax.legend(fontsize=6, ncol=2, frameon=False)
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
    fig, axs = plt.subplots(2, 3, figsize=(7.4, 4.2))
    marks = {"M04": ("o", GREEN), "M05": ("s", "#8a8a8a"), "M06": ("^", ORANGE), "M09": ("D", PURPLE)}
    for ax, fr in zip(axs.flat, b["pareto"]):
        pts = sorted(fr["points"], key=lambda p: p["lambda"])
        ax.plot([p["efficiency"] for p in pts], [p["uniformity"] for p in pts], color=BLUE, marker=".", ms=4, lw=1.0, label="front")
        for m, (mk, col) in marks.items():
            cell = [x for x in b["rows"] if x["method"] == m and x["geometry"] == fr["geometry"] and x["device"] == "ideal"
                    and x["budget_kind"] == "iterations" and x["budget"] == 100 and x["params"] == "default"]
            if cell:
                ax.scatter(cell[0]["efficiency"]["median"], cell[0]["uniformity"]["median"], marker=mk, color=col, s=16, label=m, zorder=3)
        ax.set_title(fr["geometry"], fontsize=8)
        ax.grid(True, color=GRID, lw=0.5)
        ax.tick_params(labelsize=6.5)
    for ax in axs[1]:
        ax.set_xlabel("efficiency")
    for ax in axs[:, 0]:
        ax.set_ylabel("uniformity")
    axs[0, 0].legend(fontsize=5.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(HERE / "fig-pareto.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_nfix() -> None:
    acc = {r["id"]: r["numbers"] for r in _load(DATA / "acceptance.json")["rows"]}
    sweep = acc["M07"]["n_fix_sweep_min_rel_std_150"]
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.5))
    ns = [int(k) for k in sweep]
    axs[0].plot(ns, [max(v, 1e-3) for v in sweep.values()], color=BLUE, marker="o", ms=4, lw=1.1)
    axs[0].axhline(0.5, color=RED, ls="--", lw=0.9)
    axs[0].text(ns[0], 0.6, "0.5 percent", color=RED, fontsize=6.5)
    axs[0].set_yscale("log")
    axs[0].set_xlabel("freeze index $N$")
    axs[0].set_ylabel("minimum $\\sigma$ in 150 iterations (%)")
    axs[0].set_title("(a) the source value stalls on this grid", fontsize=8)
    i7, i6 = acc["M07"]["iterations_m07"], acc["M07"]["iterations_m06"]
    w = 0.35
    xs = np.arange(len(i7))
    axs[1].bar(xs - w / 2, i6, w, color=ORANGE, label="M06")
    axs[1].bar(xs + w / 2, i7, w, color=BLUE, label="M07, N = 60")
    axs[1].set_xticks(xs, [f"seed {k + 1}" for k in xs])
    axs[1].set_ylabel("iterations to 0.5 percent")
    axs[1].set_title("(b) $50\\times30$ array", fontsize=8)
    axs[1].legend(fontsize=6.5, frameon=False)
    for a in axs:
        a.grid(True, color=GRID, lw=0.5)
    fig.tight_layout()
    fig.savefig(HERE / "fig-nfix.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
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
