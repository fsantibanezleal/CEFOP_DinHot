#!/usr/bin/env python3
"""Regenerate the figures of the device-aware conjugate-gradient refinement manuscript and the macros of its derived numbers.

Inputs (read only): ``data/beyond.json`` and the ``data/b1_weights_geo_G*.json`` files (written by ``data/measure.py`` and
``data/b1_weights_geo.py``), and the benchmark file ``data/derived/benchmark/results.json`` for the cost in time.

Figures:
  fig-b1.pdf         (a) trap intensities of one hologram on the crosstalk device, phase-fixed WGS and the refinement, sorted;
                     (b) relative standard deviation per seed: the baselines, the refinement without the device model, the
                     refinement with the efficiency-level loss and with the normalized-error loss of Schroff et al.
  fig-b1-model.pdf   (a) transfer function of the crosstalk kernel of the device model; (b) spread of the refinement per outer iteration.
  fig-b1-tradeoff.pdf  efficiency against spread per seed on the crosstalk device.
  fig-schroff.pdf    per seed, the efficiency-level loss against the normalized-error loss on the crosstalk device and on the full device.
  fig-bench.pdf      (a) factor, (b) efficiency ratio at 100 iterations on each geometry of the benchmark (cells of two seeds);
                     (c) spread at the equal wall-clock time with the reading of the win rule.
  fig-ablation.pdf   (a) crosstalk device, (b) full device: the spread of each variant of the refinement per seed.
  fig-geo.pdf        the three forms of the refinement per seed on the four lattices of the benchmark (C08 device).

Macros: ``fig_numbers.tex`` holds the numbers derived from the same files (time ratios, the cost at each budget, the counts of
the geometry comparison) and the check of Proposition 2 on the engine's two cost classes, so the text types none of them.

Run from the repository root after the measurements, with the pipeline environment:
  .venv-pipeline/Scripts/python.exe manuscripts/device-aware-refinement/figures/make_figs.py
Deps: matplotlib, numpy, and the engine of ``data-pipeline`` for the check of the proposition.
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
LIGHT_ORANGE = "#f2b27c"
GEO_LETTER = {"G1": "One", "G2": "Two", "G3": "Three", "G4": "Four", "G6a": "SixA", "G6b": "SixB"}
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200})


def load() -> dict:
    return json.loads((DATA / "beyond.json").read_text(encoding="utf-8"))


def load_geo() -> dict[str, list[dict]]:
    return {g: json.loads((DATA / f"b1_weights_geo_{g}.json").read_text(encoding="utf-8")) for g in ("G1", "G2", "G3", "G4")}


def fig_b1(d: dict) -> None:
    rows = d["bs1_crosstalk"]["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1, 1.35]})
    r0 = rows[0]
    for key, col, lab in (("ratios_M07", ORANGE, "phase-fixed WGS"), ("ratios_B1", BLUE, "device-aware refinement")):
        v = np.sort(np.array(r0[key]))
        axs[0].plot(np.arange(len(v)), v, ".", ms=3.5, color=col, label=lab)
    axs[0].axhline(1.0, color=INK, lw=0.7, ls="--")
    axs[0].set_xlabel("trap, sorted by intensity")
    axs[0].set_ylabel("trap intensity / mean")
    axs[0].set_title("(a) one hologram, seed 1, crosstalk device", fontsize=8)
    axs[0].legend(fontsize=6.8, frameon=False, loc="upper left")
    axs[0].grid(True, color=GRID, lw=0.5)
    series = [("M07_30", ORANGE, "phase-fixed WGS, 30 it.", lambda r: r["baselines"]["M07_30"]),
              ("M07_100", LIGHT_ORANGE, "phase-fixed WGS, 100 it.", lambda r: r["baselines"]["M07_100"]),
              ("M04_30", GRID, "GS, 30 it.", lambda r: r["baselines"]["M04_30"]),
              ("M06_30", PURPLE, "weighted GS, 30 it.", lambda r: r["baselines"]["M06_30"]),
              ("nm", GREEN, "refinement, device model removed", lambda r: r["B1_no_device_model"]),
              ("sc", RED, "refinement, normalized-error loss", lambda r: r["B1_schroff"]),
              ("b1", BLUE, "refinement, efficiency-level loss", lambda r: r["B1"])]
    x = np.arange(len(rows))
    w = 0.115
    for k, (_, col, lab, get) in enumerate(series):
        axs[1].bar(x + (k - 3) * w, [get(r)["sigma"] for r in rows], w, color=col, edgecolor=INK, lw=0.4, label=lab)
    axs[1].set_yscale("log")
    axs[1].set_xticks(x, [f"seed {r['seed']}" for r in rows], fontsize=7)
    axs[1].set_ylabel("relative standard deviation (%)")
    axs[1].set_title("(b) per seed, scored on the device", fontsize=8)
    axs[1].legend(fontsize=5.6, frameon=False, ncol=2, loc="upper center")
    axs[1].set_ylim(1e-2, 2e4)
    fig.tight_layout()
    fig.savefig(HERE / "fig-b1.pdf", bbox_inches="tight")
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
    axs[0].set_xlabel("spatial frequency $k$ (cycles per SLM pixel, upsampled grid)")
    axs[0].set_ylabel("transfer of the phase")
    axs[0].set_title("(a) crosstalk kernel of the device model", fontsize=8)
    axs[0].legend(fontsize=6.8, frameon=False)
    axs[0].grid(True, color=GRID, lw=0.5)
    hist = rows[0]["B1_history_sigma"]
    axs[1].plot(range(1, len(hist) + 1), hist, "o-", color=BLUE, ms=4, lw=1.1, label="refinement after each outer iteration")
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
    spec = (("phase-fixed WGS, 30 iterations", lambda r: r["baselines"]["M07_30"], ORANGE, "s"),
            ("phase-fixed WGS, 100 iterations", lambda r: r["baselines"]["M07_100"], LIGHT_ORANGE, "D"),
            ("refinement, device model removed", lambda r: r["B1_no_device_model"], GREEN, "^"),
            ("refinement, normalized-error loss", lambda r: r["B1_schroff"], RED, "v"),
            ("refinement, efficiency-level loss", lambda r: r["B1"], BLUE, "o"))
    for lab, get, col, mk in spec:
        ax.plot([get(r)["eff"] for r in rows], [get(r)["sigma"] for r in rows], mk, ms=4.5, color=col, mec=INK, mew=0.4, label=lab)
    ax.set_yscale("log")
    ax.set_xlabel("efficiency on the device")
    ax.set_ylabel("relative standard deviation (%)")
    ax.legend(fontsize=6.0, frameon=False, loc="center left")
    ax.grid(True, color=GRID, lw=0.5, which="both")
    fig.tight_layout()
    fig.savefig(HERE / "fig-b1-tradeoff.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_schroff(d: dict) -> None:
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=False)
    for ax, key, title in ((axs[0], "bs1_crosstalk", "(a) crosstalk device"), (axs[1], "bs1_full_device", "(b) full device, 4-bit")):
        rows = d[key]["rows"]
        for r in rows:
            ax.plot([0, 1], [r["B1"]["sigma"], r["B1_schroff"]["sigma"]], "-", color=GRID, lw=1.0, zorder=1)
            ax.plot([0], [r["B1"]["sigma"]], "o", ms=5, color=BLUE, mec=INK, mew=0.4, zorder=2)
            ax.plot([1], [r["B1_schroff"]["sigma"]], "v", ms=5, color=RED, mec=INK, mew=0.4, zorder=2)
        med = d[key]["summary"]["sigma_m07_30"]["median"]
        ax.axhline(med, color=ORANGE, lw=1.0, ls="--", label="phase-fixed WGS, 30 it. (median)")
        ax.set_yscale("log")
        ax.set_xlim(-0.4, 1.4)
        ax.set_xticks([0, 1], ["efficiency-level\nloss", "normalized-error\nloss (Schroff et al.)"], fontsize=7)
        ax.set_ylabel("relative standard deviation (%)")
        ax.set_title(title, fontsize=8)
        ax.grid(True, color=GRID, lw=0.5, which="both")
        ax.legend(fontsize=6.5, frameon=False, loc="center right")
    fig.tight_layout()
    fig.savefig(HERE / "fig-schroff.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_bench(d: dict) -> None:
    dev = d["benchmark_bs1"]["devices"]["device"]
    x = np.arange(len(dev))
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), gridspec_kw={"width_ratios": [1, 1, 1.2]})
    fac = [r["factor"] for r in dev]
    axs[0].bar(x, fac, 0.6, color=[BLUE if f >= 2 else GRID for f in fac], edgecolor=INK, lw=0.5, hatch="///")
    axs[0].axhline(2.0, color=INK, lw=0.8, ls="--")
    axs[0].set_xticks(x, [r["geometry"] for r in dev], fontsize=7)
    axs[0].set_ylabel("factor over phase-fixed WGS")
    axs[0].set_title("(a) factor, 100 it., threshold 2", fontsize=7.5)
    axs[0].grid(True, axis="y", color=GRID, lw=0.5)
    eff = [r["eff_ratio"] for r in dev]
    axs[1].bar(x, eff, 0.6, color=[BLUE if e >= 0.9 else GRID for e in eff], edgecolor=INK, lw=0.5, hatch="///")
    axs[1].axhline(0.9, color=INK, lw=0.8, ls="--")
    axs[1].set_ylim(0.8, 1.1)
    axs[1].set_xticks(x, [r["geometry"] for r in dev], fontsize=7)
    axs[1].set_ylabel("efficiency ratio")
    axs[1].set_title("(b) efficiency ratio, floor 0.9", fontsize=7.5)
    axs[1].grid(True, axis="y", color=GRID, lw=0.5)
    w = 0.36
    sb = [r["time_row"]["sigma_b1"] for r in dev]
    sm = [r["time_row"]["sigma_m07"] for r in dev]
    axs[2].bar(x - w / 2, sm, w, color=ORANGE, edgecolor=INK, lw=0.4, label="phase-fixed WGS")
    axs[2].bar(x + w / 2, sb, w, color=BLUE, edgecolor=INK, lw=0.4, label="refinement")
    for i, r in enumerate(dev):
        mark = {"proposed": "*", "published": "o", "tie": "="}[r["time_row"]["reading"]]
        axs[2].text(i, max(sb[i], sm[i]) * 1.18, mark, ha="center", va="bottom", fontsize=9 if mark == "*" else 8)
    axs[2].set_yscale("log")
    axs[2].set_ylim(2, 400)
    axs[2].set_xticks(x, [r["geometry"] for r in dev], fontsize=7)
    axs[2].set_ylabel("relative standard deviation (%)")
    axs[2].set_title("(c) equal time: * refinement better, = tie", fontsize=7.5)
    axs[2].legend(fontsize=6.2, frameon=False, loc="upper left")
    axs[2].grid(True, axis="y", color=GRID, lw=0.5, which="both")
    fig.tight_layout()
    fig.savefig(HERE / "fig-bench.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_ablation(d: dict) -> None:
    ab = d["ablation"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1))
    marks = ["o", "s", "^", "D", "v"]
    short = {"full": "default", "weights": "weight update on", "no_step": "no phase step", "no_guard": "no safeguard", "no_model": "no device model",
             "steps_1": "1 step", "steps_6": "6 steps", "warm_only": "start only"}
    panels = (("b1_crosstalk", ["full", "weights", "no_step", "no_guard", "no_model", "steps_1", "steps_6", "warm_only"], "(a) crosstalk device"),
              ("b1_full", ["full", "weights", "no_step", "no_guard", "no_model", "warm_only"], "(b) full device, 4-bit"))
    for ax, (key, keys, title) in zip(axs, panels):
        for i, k in enumerate(keys):
            col = BLUE if k == "full" else ORANGE if k == "weights" else INK
            filled = k in ("full", "weights")
            for j, r in enumerate(ab[key]["rows"]):
                ax.plot(i + (j - 2) * 0.07, r[k]["sigma"], marks[j % 5], ms=3.5, color=col, mfc=col if filled else "none", mew=0.7)
        ax.set_yscale("log")
        ax.set_xticks(range(len(keys)), [short[k] for k in keys], rotation=40, ha="right", fontsize=7)
        ax.set_ylabel("relative standard deviation (%)")
        ax.set_title(title + ", one marker per seed", fontsize=8)
        ax.grid(True, color=GRID, lw=0.5, which="both")
    fig.tight_layout()
    fig.savefig(HERE / "fig-ablation.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_geo(geo: dict[str, list[dict]]) -> None:
    fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.8))
    names = {"G1": "G1 square", "G2": "G2 ring", "G3": "G3 random", "G4": "G4 quasi-periodic"}
    cols = (("weights", ORANGE, "o", "weight update on"), ("no_weights", BLUE, "s", "default"), ("schroff", RED, "v", "normalized-error"))
    for ax, g in zip(axs, ("G1", "G2", "G3", "G4")):
        rows = [r for r in geo[g] if r["device"]]
        for r in rows:
            ax.plot([0, 1, 2], [r[k]["sigma"] for k, *_ in cols], "-", color=GRID, lw=0.9, zorder=1)
        for i, (k, col, mk, lab) in enumerate(cols):
            ax.plot([i] * len(rows), [r[k]["sigma"] for r in rows], mk, ms=4.2, color=col, mec=INK, mew=0.4, zorder=2, label=lab)
        ax.set_yscale("log")
        ax.set_xlim(-0.5, 2.5)
        ax.set_xticks([0, 1, 2], ["weights", "default", "norm. error"], rotation=40, ha="right", fontsize=6.5)
        ax.set_title(names[g], fontsize=7.5)
        ax.grid(True, color=GRID, lw=0.5, which="both")
        if g == "G1":
            ax.set_ylabel("relative standard deviation (%)")
    fig.tight_layout()
    fig.savefig(HERE / "fig-geo.pdf", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- derived numbers

def tex_sci(x: float) -> str:
    """A small difference as a LaTeX number: 0 stays 0, anything else is written as a power of ten."""
    if x == 0.0:
        return "0"
    mant, exp = f"{x:.0e}".split("e")
    return f"${mant}\\times10^{{{int(exp)}}}$"


def studio_rule():
    """The win rule of the benchmark, implemented once in the technical report's ``extract_methods.py`` (``cell_result``, ``is_over_budget``)."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(HERE.parents[1] / "holographic-trap-studio" / "data"))
    import extract_methods as X  # noqa: PLC0415

    return X


def reference_id() -> str:
    """The engine's key of the reference method (phase-fixed WGS) in the benchmark file, read from the engine."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    from pipeline.model.holo.methods.baseline import m07_phase_fixed_wgs  # noqa: PLC0415

    return m07_phase_fixed_wgs.SPEC.id


def check_losses() -> tuple[float, float]:
    """Proposition 2 on the engine's two cost classes: at the phase where the target is set, the efficiency-level loss and the
    normalized-error loss of Schroff et al. have the same value, and their gradients differ by -(2 L / P) grad P (equal traps, default
    steepness). Returns the relative difference of the values and the largest component of gradient difference minus prediction,
    relative to the largest component of the prediction."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "data-pipeline"))
    sys.path.insert(0, str(DATA))
    import measure as M  # noqa: PLC0415
    from pipeline.model.holo.methods.beyond import b1_device_wgs as B1  # noqa: PLC0415
    from pipeline.model.holo.methods.optim import _common as C  # noqa: PLC0415

    setup = M.make_setup(64)
    traps = M.bin_grid(setup, 4, 4, 8)
    rng = np.random.default_rng(3)
    phi = rng.uniform(0.0, 2.0 * np.pi, (64, 64))
    cl = C.TrapCost(setup, traps, M.CROSSTALK_DEVICE, t=2, efficiency=0.9)
    cn = B1.NormalizedErrorCost(setup, traps, M.CROSSTALK_DEVICE, t=2, efficiency=0.9)
    v, cache = cl.fwd.fields(phi)
    p = float(np.sum(np.abs(v) ** 2))
    cl.target = np.full(len(traps), p / len(traps))
    cn.target = cl.target.copy()
    fl, gl, _ = cl.value_grad(phi)
    fn, gn, _ = cn.value_grad(phi)
    grad_p = cl.fwd.adjoint(v, cache)                       # d P / d phi: the adjoint of the unit gradient on every intensity
    pred = -(2.0 * fl / p) * grad_p
    return abs(fn - fl) / fl, float(np.max(np.abs(gn - gl - pred)) / np.max(np.abs(pred)))


def write_numbers(d: dict, geo: dict[str, list[dict]]) -> None:
    L = ["% Generated by figures/make_figs.py from data/beyond.json, data/b1_weights_geo_G*.json and the benchmark results. Do not edit.\n"]

    def mac(name: str, value) -> None:
        L.append(f"\\newcommand{{\\{name}}}{{{value}}}\n")

    sm = d["bs1_crosstalk"]["summary"]
    smf = d["bs1_full_device"]["summary"]
    mac("timeRatioX", f"{sm['seconds_b1']['median'] / sm['seconds_m07_100']['median']:.0f}")
    mac("timeRatioF", f"{smf['seconds_b1']['median'] / smf['seconds_m07_100']['median']:.0f}")
    # equal-time medians per geometry (the win rule's rows)
    for x in d["benchmark_bs1"]["devices"]["device"]:
        g = GEO_LETTER[x["geometry"]]
        mac(f"benchTimeSigRefGeo{g}", f"{x['time_row']['sigma_b1']:.1f}")
        mac(f"benchTimeSigMsevenGeo{g}", f"{x['time_row']['sigma_m07']:.1f}")
    # cost in time at each budget, from the benchmark's own rows
    res = json.loads((ROOT / "data" / "derived" / "benchmark" / "results.json").read_text(encoding="utf-8"))
    def row(method: str, geometry: str, budget: int) -> dict:
        return next(x for x in res["rows"] if x["method"] == method and x["geometry"] == geometry and x["device"] == "device"
                    and x["budget_kind"] == "iterations" and x["budget"] == budget and x["params"] == "default")
    geos = list(GEO_LETTER)
    for budget, name in ((10, "Ten"), (100, "Hundred")):
        ref = [row("B1", g, budget)["time_s"]["median"] for g in geos]
        m07 = [row(reference_id(), g, budget)["time_s"]["median"] for g in geos]
        mac(f"bench{name}SecRefMin", f"{min(ref):.0f}")
        mac(f"bench{name}SecRefMax", f"{max(ref):.0f}")
        mac(f"bench{name}SecMsevenMin", f"{min(m07):.2f}")
        mac(f"bench{name}SecMsevenMax", f"{max(m07):.2f}")
    def trow(method: str, geometry: str) -> dict:
        return next(x for x in res["rows"] if x["method"] == method and x["geometry"] == geometry and x["device"] == "device"
                    and x["budget_kind"] == "time" and x["budget"] == 1.0 and x["params"] == "default")
    its1 = [trow("B1", g)["iterations"]["median"] for g in geos]
    over1 = [trow("B1", g)["time_s"]["median"] - 1.0 for g in geos]
    mac("benchOneSecItersMin", f"{min(its1):.0f}")
    mac("benchOneSecItersMax", f"{max(its1):.0f}")
    mac("benchOneSecOverrunMin", f"{min(over1):.2f}")
    mac("benchOneSecOverrunMax", f"{max(over1):.2f}")
    # the reading of the rows of the device at the time budget against every method of the cell (the technical report's reading),
    # and the rule that sets a row aside when it exceeds its budget (``extract_methods.OVER_BUDGET_FACTOR``)
    X = studio_rule()
    mac("benchOverFactor", f"{X.OVER_BUDGET_FACTOR:g}")
    mac("benchOneSecTimeMax", f"{max(trow('B1', g)['time_s']['median'] for g in geos):.2f}")
    mac("benchOneSecOverN", sum(1 for g in geos if X.is_over_budget(trow("B1", g))))
    trows = [x for x in res["rows"] if x["budget_kind"] == "time" and x["budget"] == 1.0 and x["params"] == "default" and x["device"] == "device"]
    reads = {g: X.cell_result([x for x in trows if x["geometry"] == g]) for g in geos}
    ref_wins = [g for g in geos if reads[g]["result"] == "proposed" and reads[g]["proposed"]["method"] == "B1"]
    pub_wins = [g for g in geos if reads[g]["result"] == "published"]
    mac("benchAllRefWins", len(ref_wins))
    mac("benchAllRefWinList", " and ".join(ref_wins))
    mac("benchAllRefWinMinN", min(min(reads[g]["published"]["n_seeds"], reads[g]["proposed"]["n_seeds"]) for g in ref_wins))
    mac("benchAllPubWins", len(pub_wins))
    mac("benchAllPubWinList", " and ".join(pub_wins))
    mac("benchAllTies", sum(1 for g in geos if reads[g]["result"] == "tie"))
    if pub_wins:   # the first geometry where a published method is read as better than the best proposed one
        c = reads[pub_wins[0]]
        mac("benchAllPubName", c["published"]["method"] and X.RUN[c["published"]["method"]])
        mac("benchAllPubN", c["published"]["n_seeds"])
        mac("benchAllPubSigma", X.sig(c["published"]["rel_std_pct"]["median"]))
        mac("benchAllPubRefN", c["proposed"]["n_seeds"])
        mac("benchAllPubRefSigma", X.sig(c["proposed"]["rel_std_pct"]["median"]))
    same = sum(1 for g in geos if abs(row("B1", g, 10)["rel_std_pct"]["median"] - row("B1", g, 100)["rel_std_pct"]["median"]) < 1e-6
               and abs(row("B1", g, 30)["rel_std_pct"]["median"] - row("B1", g, 100)["rel_std_pct"]["median"]) < 1e-6)
    mac("benchBudgetSameCells", same)
    mac("benchBudgetCells", len(geos))
    g1_10, g1_100 = row("B1", "G1", 10), row("B1", "G1", 100)
    mac("benchGOneIters", f"{g1_100['iterations']['median']:.0f}")
    mac("benchGOneEvalTen", f"{g1_10['evaluations']['median']:.0f}")
    mac("benchGOneEvalHundred", f"{g1_100['evaluations']['median']:.0f}")
    mac("benchGOneSecTen", f"{g1_10['time_s']['median']:.0f}")
    mac("benchGOneSecHundred", f"{g1_100['time_s']['median']:.0f}")
    # quasi-periodic lattice: the seeds on which the three forms return the same spread on the device
    rows4 = [r for r in geo["G4"] if r["device"]]
    mac("geoDSameSeeds", sum(1 for r in rows4 if abs(r["weights"]["sigma"] - r["no_weights"]["sigma"]) < 1e-9
                             and abs(r["no_weights"]["sigma"] - r["schroff"]["sigma"]) < 1e-9))
    vdiff, gdiff = check_losses()
    mac("lossValueDiff", tex_sci(vdiff))
    mac("lossGradDiff", tex_sci(gdiff))
    (HERE / "fig_numbers.tex").write_text("".join(L), encoding="utf-8", newline="\n")


def write_bench_table(d: dict) -> None:
    """The benchmark rows of the paper as a compact table (``tab_bench_read.tex``): the same cells as ``data/tab_bench.tex`` without
    the plain GS and weighted GS times, with short headers so that it prints at a readable size."""
    bb = d["benchmark_bs1"]
    head = ["Geometry", "Traps", "$n$", "\\shortstack[r]{$\\sigma$ phase-fixed\\\\WGS (\\%)}", "\\shortstack[r]{$\\sigma$ refinement\\\\(\\%)}",
            "Factor", "$e$ ratio", "\\shortstack[r]{$t$ phase-fixed\\\\WGS (s)}", "\\shortstack[r]{$t$ refinement\\\\(s)}",
            f"$n$ at {bb['time_budget_s']:g}~s", "\\shortstack[l]{Reading at\\\\equal time}", "\\shortstack[l]{Both\\\\thresholds}"]
    L = ["\\begin{tabular}{@{}l r r r r r r r r r l l@{}}\n\\toprule\n", " & ".join(head) + " \\\\\n\\midrule\n"]

    def t(x: float) -> str:
        return f"{x:.3g}" if x < 100 else f"{x:.0f}"

    for x in bb["devices"]["device"]:
        ok = x["factor"] >= 2 and x["eff_ratio"] >= 0.9
        s = x["seconds"]
        cells = [f"{x['geometry']} {x['name']}", str(x["n_traps"]), f"{x['n_seeds_b1']}, {x['n_seeds_m07']}",
                 f"{x['sigma_m07']:.2f} ({x['sigma_m07_iqr'][0]:.2f} to {x['sigma_m07_iqr'][1]:.2f})",
                 f"{x['sigma_b1']:.2f} ({x['sigma_b1_iqr'][0]:.2f} to {x['sigma_b1_iqr'][1]:.2f})",
                 f"{x['factor']:.2f}", f"{x['eff_ratio']:.3f}", t(s[reference_id()]), t(s["B1"]),
                 f"{x['time_row']['n_b1']}, {x['time_row']['n_m07']}", x["time_row"]["reading"], "yes" if ok else "no"]
        L.append(" & ".join(cells) + " \\\\\n")
    L.append("\\bottomrule\n\\end{tabular}\n")
    (HERE / "tab_bench_read.tex").write_text("".join(L), encoding="utf-8", newline="\n")


def main() -> int:
    d = load()
    geo = load_geo()
    write_bench_table(d)
    fig_b1(d)
    fig_b1_model(d)
    fig_b1_tradeoff(d)
    fig_schroff(d)
    fig_bench(d)
    fig_ablation(d)
    fig_geo(geo)
    write_numbers(d, geo)
    print("figures and fig_numbers.tex written to", HERE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
