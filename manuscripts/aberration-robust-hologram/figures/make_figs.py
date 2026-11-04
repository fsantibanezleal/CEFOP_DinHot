#!/usr/bin/env python3
"""Regenerate the figures of the aberration-robust hologram manuscript from ``data/robust.json`` (written by ``data/measure.py``).

  fig-modes.pdf      the eight aberration modes of the design (Noll 4 to 11) on the SLM disc, from the engine's basis.
  fig-design.pdf     (a) the design samples in the plane of two modes: the sixteen deterministic points and 16 random draws
                     against the 200 draws of the evaluation ensemble; (b) the rms wavefront of each draw.
  fig-ecdf.pdf       distribution over the 200 draws of the relative standard deviation, phase-fixed WGS against B4 (seed 1).
  fig-seeds.pdf      (a) ratio of the 95th percentiles per seed with its bootstrap interval; (b) efficiency ratio per seed.
  fig-conv.pdf       (a) the expected cost along the CG iterations; (b) the ratio of the 95th percentiles against the iterations.
  fig-level.pdf      the ratio of the 95th percentiles against the efficiency ratio for each target level.
  fig-ablation.pdf   the ratio of the 95th percentiles of each ablation variant (design samples, modes, amplitude).
  fig-mismatch.pdf   the ratio on ensembles that differ from the design prior (amplitude, extra modes).
  fig-theory.pdf     (a) first-order spread against the measured spread per draw; (b) measured and predicted mean squared spread.
  fig-pointing.pdf   (a) the ratio under pointing errors against the displacement; (b) the curvature of the trap intensity.
  fig-bake.pdf       the relative standard deviation of phase-fixed WGS and of B4 on the cases of the committed bake.

Run from the repository root after the measurement:  python manuscripts/aberration-robust-hologram/figures/make_figs.py
Deps: matplotlib, numpy (the notebook environment); the modes figure also imports the engine's Zernike basis.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

INK = "#1a1a2e"
GRID = "#d8d8e0"
DARK, LIGHT, MID = "#1f3b73", "#e0883a", "#6b6b78"      # dark blue and light orange differ in luminance (readable in grayscale)
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "axes.linewidth": 0.8, "figure.dpi": 200, "pdf.fonttype": 42})


def load() -> dict:
    return json.loads((DATA / "robust.json").read_text(encoding="utf-8"))


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(HERE / name)
    plt.close(fig)


def grid(ax) -> None:
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)


def fig_modes() -> None:
    from pipeline.model.holo.core.geometry import Setup
    from pipeline.model.holo.core.zernike import noll_to_nm, wavefront_waves, zernike_name
    s = Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=128, pitch_m=12.5e-6, pad=2, beam="gaussian")
    fig, axs = plt.subplots(2, 4, figsize=(7.2, 4.2))
    for ax, j in zip(axs.ravel(), range(4, 12)):
        c = np.zeros(21)
        c[j - 1] = 1.0
        w = wavefront_waves(c, s)
        n_, m_ = noll_to_nm(j)
        im = ax.imshow(w, cmap="gray", vmin=-2.5, vmax=2.5, interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"j = {j}\n{zernike_name(j)}\n(n={n_}, m={m_})", fontsize=6)
    fig.colorbar(im, ax=axs, shrink=0.8, label="wavefront for a unit coefficient (waves)")
    fig.savefig(HERE / "fig-modes.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_design(d: dict) -> None:
    from pipeline.model.holo.core.rng import Rng
    sa = d["meta"]["aberration"]
    rng = Rng(d["meta"]["ensemble_seed"])
    n = d["meta"]["ensemble_size"]
    draws = []
    for _ in range(n):
        draws.append(sa * rng.normal_array(8))
        rng.normal_array(100)
        rng.normal_array(100)
    draws = np.array(draws)
    rr = Rng(1001)
    rand16 = np.array([sa * rr.normal_array(8) for _ in range(16)])
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axs[0]
    ax.plot(draws[:, 0], draws[:, 1], ".", ms=3, color=MID, label="evaluation draws (200)")
    ax.plot(rand16[:, 0], rand16[:, 1], "s", ms=4.5, mfc="white", mec=LIGHT, label="16 random draws")
    r = sa * np.sqrt(8)
    pts = [(r, 0), (-r, 0), (0, r), (0, -r)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "D", ms=6, color=DARK, label="sigma points on these modes")
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(sa * np.cos(th), sa * np.sin(th), "-", color=INK, lw=0.8, label="one standard deviation")
    ax.set_xlabel("coefficient of Noll 4, defocus (waves)")
    ax.set_ylabel("coefficient of Noll 5 (waves)")
    ax.set_title("(a) design samples in the plane of two modes", fontsize=8)
    ax.legend(fontsize=6.5, frameon=False, loc="upper left")
    grid(ax)
    ax.set_aspect("equal", adjustable="datalim")
    ax = axs[1]
    rms_draw = np.sqrt((draws**2).sum(axis=1))
    ax.hist(rms_draw, bins=22, color=MID, edgecolor=INK, lw=0.4, label="evaluation draws")
    ax.axvline(sa * np.sqrt(8), color=DARK, lw=1.4, ls="--", label="sigma points (all 16 have this rms)")
    ax.set_xlabel("rms wavefront over Noll 4 to 11 (waves)")
    ax.set_ylabel("draws")
    ax.set_title("(b) the sigma points share one rms", fontsize=8)
    ax.legend(fontsize=6.0, frameon=False, loc="upper right")
    ax.set_ylim(0, 27)
    grid(ax)
    save(fig, "fig-design.pdf")


def fig_ecdf(d: dict) -> None:
    m = d["main"][0]
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    for key, col, ls, lab in (("sig_nominal", LIGHT, "-", "phase-fixed WGS"), ("sig_b4", DARK, "--", "aberration-robust hologram")):
        v = np.sort(np.array(m[key]))
        ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", color=col, ls=ls, lw=1.6, label=lab)
        p95 = np.percentile(v, 95)
        ax.axvline(p95, color=col, lw=0.8, ls=":")
        ax.text(p95, 0.55 if key == "sig_b4" else 0.45, f" p95 {p95:.2f} ", color=INK, fontsize=7, ha="right" if key == "sig_b4" else "left")
    ax.axhline(0.95, color=MID, lw=0.6)
    ax.set_xlabel("relative standard deviation of trap intensities (percent)")
    ax.set_ylabel("fraction of the 200 draws")
    ax.legend(fontsize=7, frameon=False, loc="lower right", bbox_to_anchor=(1.0, 0.0))
    grid(ax)
    save(fig, "fig-ecdf.pdf")


def fig_seeds(d: dict) -> None:
    mains = d["main"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
    x = np.array([m["seed"] for m in mains])
    r = np.array([m["ratio"] for m in mains])
    lo = r - np.array([m["p95_ci"][0] for m in mains])
    hi = np.array([m["p95_ci"][1] for m in mains]) - r
    ax = axs[0]
    ax.errorbar(x, r, yerr=[lo, hi], fmt="o", color=DARK, ms=4.5, capsize=2.5, lw=1.0, label="ratio, 95 percent bootstrap interval over the draws")
    ax.axhline(1.25, color=LIGHT, lw=1.2, ls="--", label="criterion 1.25")
    ax.axhline(statistics.median(r), color=INK, lw=0.8, ls=":", label=f"median over {len(r)} seeds")
    ax.set_xlabel("seed of the holograms")
    ax.set_ylabel("p95 of phase-fixed WGS over p95 of B4")
    ax.set_title("(a) spread ratio per seed", fontsize=8)
    ax.set_xticks(x)
    ax.set_ylim(0.95, 1.85)
    ax.legend(fontsize=6.0, frameon=False, loc="lower right")
    grid(ax)
    ax = axs[1]
    e = np.array([m["eff_ratio"] for m in mains])
    ax.plot(x, e, "s", color=DARK, ms=4.5)
    ax.axhline(0.9, color=LIGHT, lw=1.2, ls="--", label="criterion 0.90")
    ax.set_ylim(0.85, 1.02)
    ax.set_xlabel("seed of the holograms")
    ax.set_ylabel("mean efficiency of B4 over that of WGS")
    ax.set_title("(b) efficiency ratio per seed", fontsize=8)
    ax.set_xticks(x)
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
    grid(ax)
    save(fig, "fig-seeds.pdf")


def abl_stats(d: dict) -> dict:
    by: dict[str, dict] = {}
    for r in d["ablation_runs"]:
        by.setdefault(r["name"], {"ratio": [], "eff": []})
        by[r["name"]]["ratio"].append(r["ratio"])
        by[r["name"]]["eff"].append(r["eff_ratio"])
    three = [m for m in d["main"] if m["seed"] <= 3]
    by["default"] = {"ratio": [m["ratio"] for m in three], "eff": [m["eff_ratio"] for m in three]}
    return by


def fig_conv(d: dict) -> None:
    by = abl_stats(d)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
    ax = axs[0]
    for m, mk, col in zip(d["main"][:3], ("o", "s", "^"), (DARK, LIGHT, MID)):
        ax.semilogy(np.arange(1, len(m["loss"]) + 1), m["loss"], marker=mk, ms=2.8, lw=1.0, color=col, label=f"seed {m['seed']}")
    ax.set_xlabel("conjugate-gradient iteration")
    ax.set_ylabel("expected cost over the 16 sigma points")
    ax.set_title("(a) the optimised cost", fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    grid(ax)
    ax = axs[1]
    names = [("iter5", 5), ("iter10", 10), ("iter20", 20), ("default", 40), ("iter80", 80)]
    its = [n for _, n in names]
    med = [statistics.median(by[k]["ratio"]) for k, _ in names]
    lo = [min(by[k]["ratio"]) for k, _ in names]
    hi = [max(by[k]["ratio"]) for k, _ in names]
    ax.errorbar(its, med, yerr=[np.array(med) - lo, np.array(hi) - med], fmt="o-", color=DARK, capsize=2.5, lw=1.1, ms=4.5)
    ax.axhline(1.25, color=LIGHT, lw=1.2, ls="--", label="criterion 1.25")
    ax.set_xscale("log")
    ax.set_xticks(its)
    ax.set_xticklabels([str(i) for i in its])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("conjugate-gradient iterations")
    ax.set_ylabel("p95 ratio, median and range of 3 seeds")
    ax.set_title("(b) spread ratio against the iterations", fontsize=8)
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    grid(ax)
    save(fig, "fig-conv.pdf")


def fig_level(d: dict) -> None:
    by = abl_stats(d)
    keys = [("level0.8", 0.80), ("level0.85", 0.85), ("default", 0.90), ("level0.937", 0.937), ("level0.95", 0.95), ("level1.0", 1.0)]
    fig, ax = plt.subplots(figsize=(4.6, 3.1))
    xe = [statistics.median(by[k]["eff"]) for k, _ in keys]
    yr = [statistics.median(by[k]["ratio"]) for k, _ in keys]
    ylo = [min(by[k]["ratio"]) for k, _ in keys]
    yhi = [max(by[k]["ratio"]) for k, _ in keys]
    ax.errorbar(xe, yr, yerr=[np.array(yr) - ylo, np.array(yhi) - yr], fmt="o-", color=DARK, capsize=2.5, lw=1.0, ms=4.5)
    for (k, lv), x, y in zip(keys, xe, yr):
        ax.annotate(f"{lv:g}", (x, y), textcoords="offset points", xytext=(5, 5), fontsize=7)
    ax.axhline(1.25, color=LIGHT, lw=1.2, ls="--", label="criterion 1.25")
    ax.axvline(0.90, color=MID, lw=1.0, ls=":", label="efficiency floor 0.90")
    ax.set_xlabel("mean efficiency of B4 over that of WGS")
    ax.set_ylabel("p95 ratio, median and range of 3 seeds")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    grid(ax)
    save(fig, "fig-level.pdf")


def fig_ablation(d: dict) -> None:
    by = abl_stats(d)
    items = [("nominal", "nominal cost, same CG"), ("rand4", "4 random draws"), ("rand8", "8 random draws"), ("rand16", "16 random draws"),
             ("rand32", "32 random draws"), ("adam", "resampled draws, Adam"), ("modes4-4", "mode 4 only"), ("modes4-6", "modes 4 to 6"),
             ("modes4-8", "modes 4 to 8"), ("modes9-11", "modes 9 to 11"), ("prior0.005", "amplitude 0.005"),
             ("prior0.01", "amplitude 0.01"), ("prior0.03", "amplitude 0.03"), ("prior0.04", "amplitude 0.04"),
             ("default", "B4: sigma points, modes 4 to 11, 0.02")]
    med = np.array([statistics.median(by[k]["ratio"]) for k, _ in items])
    lo = med - np.array([min(by[k]["ratio"]) for k, _ in items])
    hi = np.array([max(by[k]["ratio"]) for k, _ in items]) - med
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    y = np.arange(len(items))
    cols = [DARK if k == "default" else MID for k, _ in items]
    ax.barh(y, med, xerr=[lo, hi], color=cols, edgecolor=INK, lw=0.5, capsize=2.5, error_kw={"lw": 0.9})
    ax.axvline(1.25, color=LIGHT, lw=1.3, ls="--", label="criterion 1.25")
    ax.axvline(1.0, color=INK, lw=0.8, ls=":", label="no gain")
    ax.set_yticks(y)
    ax.set_yticklabels([lab for _, lab in items], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("p95 ratio against phase-fixed WGS, median and range of 3 seeds")
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    grid(ax)
    save(fig, "fig-ablation.pdf")


def fig_mismatch(d: dict) -> None:
    rows: dict = {}
    for r in d["mismatch"]:
        for x in r["rows"]:
            rows.setdefault((x["kind"], x["value"]), []).append(x)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axs[0]
    amps = sorted(v for (k, v) in rows if k == "amplitude")
    med = [statistics.median(x["ratio"] for x in rows[("amplitude", a)]) for a in amps]
    lo = [min(x["ratio"] for x in rows[("amplitude", a)]) for a in amps]
    hi = [max(x["ratio"] for x in rows[("amplitude", a)]) for a in amps]
    ax.errorbar(amps, med, yerr=[np.array(med) - lo, np.array(hi) - med], fmt="o-", color=DARK, capsize=2.5, ms=4.5, lw=1.1)
    ax.axvline(d["meta"]["aberration"], color=MID, ls=":", lw=1.0, label="design amplitude")
    ax.axhline(1.25, color=LIGHT, lw=1.2, ls="--", label="criterion 1.25")
    ax.set_xlabel("amplitude of the evaluation ensemble (waves per mode)")
    ax.set_ylabel("p95 ratio, median and range of 3 seeds")
    ax.set_title("(a) ensemble amplitude differs from the design", fontsize=8)
    ax.legend(fontsize=6.5, frameon=False)
    grid(ax)
    ax = axs[1]
    labs = [("amplitude", 0.02, "design prior"), ("modes", "noll 12 to 15 added", "plus Noll 12 to 15"), ("modes", "noll 12 to 21 as well", "plus Noll 12 to 21")]
    xs = np.arange(len(labs))
    mm = [statistics.median(x["ratio"] for x in rows[(k, v)]) for k, v, _ in labs]
    l2 = [min(x["ratio"] for x in rows[(k, v)]) for k, v, _ in labs]
    h2 = [max(x["ratio"] for x in rows[(k, v)]) for k, v, _ in labs]
    ax.bar(xs, mm, yerr=[np.array(mm) - l2, np.array(h2) - mm], color=[DARK, MID, MID], edgecolor=INK, lw=0.5, capsize=2.5)
    ax.axhline(1.25, color=LIGHT, lw=1.2, ls="--")
    ax.set_xticks(xs)
    ax.set_xticklabels([lab for _, _, lab in labs], fontsize=7, rotation=12)
    ax.set_ylabel("p95 ratio")
    ax.set_title("(b) modes outside the design", fontsize=8)
    grid(ax)
    save(fig, "fig-mismatch.pdf")


def fig_theory(d: dict) -> None:
    t = d["theory"][0]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axs[0]
    for name, col, mk, lab in (("nominal", LIGHT, "o", "phase-fixed WGS"), ("b4", DARK, "^", "B4")):
        ax.plot(t[name]["sig"], t[name]["lin"], mk, ms=3, color=col, mfc="none" if name == "nominal" else col, label=lab)
    top = max(max(t["nominal"]["sig"]), max(t["nominal"]["lin"]))
    ax.plot([0, top], [0, top], "-", color=INK, lw=0.8, label="equality")
    ax.set_xlabel("relative standard deviation from the full model (percent)")
    ax.set_ylabel("from the first-order model (percent)")
    ax.set_title("(a) one draw per marker, seed 1", fontsize=8)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    grid(ax)
    ax = axs[1]
    labels = ["measured", "first order", "upper bound"]
    keys = ["measured_mean_sq", "pred_mean_sq", "bound_mean_sq"]
    xs = np.arange(len(keys))
    w = 0.36
    for k, (name, col, hatch, lab) in enumerate((("nominal", LIGHT, "//", "phase-fixed WGS"), ("b4", DARK, "", "B4"))):
        vals = [statistics.median(tt[name][key] for tt in d["theory"]) for key in keys]
        ax.bar(xs + (k - 0.5) * w, vals, w, color=col, hatch=hatch, edgecolor=INK, lw=0.5, label=lab)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("mean squared spread (percent squared)")
    ax.set_ylim(0, 19)
    ax.set_title("(b) mean over draws, median of 3 seeds", fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    grid(ax)
    save(fig, "fig-theory.pdf")


def fig_pointing(d: dict) -> None:
    pt = d["point"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.9), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axs[0]
    bins = [0.05, 0.10, 0.15]
    for key, col, mk, lab in (("ratio_sample", DARK, "o", "pointing and aberration design, Adam"),
                              ("ratio_sigma_design", LIGHT, "s", "aberration design (B4 as released)")):
        med = [statistics.median(r[key] for p in pt for r in p["rows"] if abs(r["bins"] - b) < 1e-9) for b in bins]
        lo = [min(r[key] for p in pt for r in p["rows"] if abs(r["bins"] - b) < 1e-9) for b in bins]
        hi = [max(r[key] for p in pt for r in p["rows"] if abs(r["bins"] - b) < 1e-9) for b in bins]
        ax.errorbar(bins, med, yerr=[np.array(med) - lo, np.array(hi) - med], fmt=mk + "-", color=col, capsize=2.5, ms=4.5, lw=1.1, label=lab)
    po = d["pointonly"]
    for key, col, mk, ls, lab in (("pointing_design_p95", MID, "^", "-.", "displacements alone, 20 steps"),
                                  ("pointing_design_100_p95", INK, "v", ":", "displacements alone, 100 steps")):
        rr = [[r["nominal_p95"] / r[key] for p in po for r in p["rows"] if abs(r["bins"] - b) < 1e-9] for b in bins]
        med = [statistics.median(x) for x in rr]
        ax.errorbar(bins, med, yerr=[np.array(med) - [min(x) for x in rr], [max(x) for x in rr] - np.array(med)], fmt=mk + ls,
                    color=col, capsize=2.5, ms=4.5, lw=1.1, label=lab)
    acc = statistics.median(p["acceptance"]["ratio"] for p in pt)
    ax.plot([0.15], [acc], "D", color=INK, ms=5, label="acceptance configuration (3 steps, 2 draws)")
    ax.axhline(1.25, color=MID, lw=1.0, ls="--", label="criterion of the aberration claim")
    ax.set_xlabel("standard deviation of the trap displacement (focal bins)")
    ax.set_ylabel("p95 ratio, median and range of 3 seeds")
    ax.set_title("(a) joint aberration and pointing ensemble", fontsize=8)
    ax.legend(fontsize=5.6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    grid(ax)
    ax = axs[1]
    cv = [p["curvature"] for p in pt]
    vals = [statistics.median(c["nominal"] for c in cv), statistics.median(c["b4"] for c in cv), cv[0]["aperture"]]
    ax.bar(range(3), vals, color=[LIGHT, DARK, MID], edgecolor=INK, lw=0.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["phase-fixed\nWGS", "B4", "aligned\naperture"], fontsize=7.5)
    ax.set_ylabel("relative curvature (per bin squared)")
    ax.set_title("(b) the spot width fixes the curvature", fontsize=8)
    grid(ax)
    save(fig, "fig-pointing.pdf")


def fig_bake(d: dict) -> None:
    cases = d["bake"]["cases"]
    names = list(cases)
    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    m7 = [statistics.mean(cases[c]["M07.rel_std_pct"]) for c in names]
    b4 = [statistics.mean(cases[c]["B4.rel_std_pct"]) for c in names]
    ax.barh(y - 0.2, m7, 0.38, color=LIGHT, hatch="//", edgecolor=INK, lw=0.5, label="phase-fixed WGS (mean of 3 seeds)")
    ax.barh(y + 0.2, b4, 0.38, color=DARK, edgecolor=INK, lw=0.5, label="aberration-robust hologram (mean of 3 seeds)")
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("_", " ") for c in names], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("relative standard deviation in the committed bake (percent)")
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.18), ncol=1)
    grid(ax)
    save(fig, "fig-bake.pdf")


def main() -> None:
    d = load()
    fig_modes()
    fig_design(d)
    fig_ecdf(d)
    fig_seeds(d)
    fig_conv(d)
    fig_level(d)
    fig_ablation(d)
    fig_mismatch(d)
    fig_theory(d)
    fig_pointing(d)
    fig_bake(d)
    print("figures written to", HERE)


if __name__ == "__main__":
    main()
