#!/usr/bin/env python3
"""Measure the learned warm start (B3) of DinHot: every arm of the ablation on the held-out geometries, the freeze sweep,
the oracle-phase bound and the weight accounting; write ``warm.json``, ``warm_numbers.tex`` and the table files.

The network is the rejected candidate: the checkpoint ``ws-final/ckpt.pt`` of the training run (6000 steps) in the learned
directory of the data root. Nothing is retrained. The held-out file is verified against the sha256 of the committed record
``data/derived/models/warmstart-model-rejected.json`` before anything runs. Every arm runs the engine's M07 (phase-fixed
WGS, point form) from the same ``Rng`` seeds, on the same geometries, with the same budget as the evaluation of the record
(``data-pipeline/pipeline/model/holo/learned/evaluation.py``): seeds 301 to 303, 60 iterations, iterations to 1 percent of
relative standard deviation (budget plus one when never reached), per-geometry median over the seeds.

Arms (start, freeze index n_fix): random n12 (the engine default), random n3 (the early fix alone), network n3 (the
candidate as evaluated), network n12 (the network with the engine's own freeze). Extra: a freeze sweep of the random start
(n_fix 1, 2, 4, 6, 8 on every second generated geometry) and of the network start, an oracle start (phases of a converged
run) and the accounting of the weights of the update (Proposition 3 of the manuscript).

Run from the repository root (needs torch: the GPU environment, only the CPU is used):

    E:/_venvs/CEFOP_DinHot-gpu/Scripts/python.exe manuscripts/learned-warm-start/data/measure.py [--workers 8] [--emit-only]

Deterministic given the checkpoint: every method takes its seed through the portable generator.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

SEEDS = (301, 302, 303)
BUDGET = 60
SWEEP_NFIX = (1, 2, 4, 6, 8)
ORACLE_N = 10
BOOT = 10000
BOOT_SEED = 20261104
DEFAULT_LEARNED = "E:/_Datos/dinhot/learned"
RECORD = ROOT / "data" / "derived" / "models" / "warmstart-model-rejected.json"

_W: dict = {}


def _init(learned: str) -> None:
    import torch
    torch.set_num_threads(1)
    from pipeline.model.holo.learned import heldout, nets
    ck = torch.load(Path(learned) / "checkpoints" / "ws-final" / "ckpt.pt", map_location="cpu", weights_only=False)
    c = ck["cfg"]
    net = nets.SetNet(c["d"], c["heads"], c["layers"], c["ff"])
    net.load_state_dict(ck["net"])
    net.eval()
    gen, bench = heldout.load_warm(Path(learned) / "warmstart-heldout.npz")
    sets = [(f"gen/{i:02d}", a, 256) for i, a in enumerate(gen)] + [(f"bench/{n}", a, p) for n, a, p in bench]
    _W.update(net=net, sets=sets, torch=torch, heldout=heldout, theta={})


def _geom(i: int):
    from pipeline.model.holo.core.types import Target
    from pipeline.model.holo.learned import convert, evaluation as ev
    name, arr, n_pix = _W["sets"][i]
    setup = ev.SETUP256 if n_pix == 256 else _W["heldout"]._bench_setup(n_pix)
    t = np.zeros((1, convert.MAX_TRAPS, 4), np.float32)
    m = np.zeros((1, convert.MAX_TRAPS), np.float32)
    t[0, : len(arr)], m[0, : len(arr)] = arr, 1.0
    ts = convert.input_to_traps(setup, t, m)
    return name, setup, ts, Target.from_traps(ts)


def _theta(i: int, setup, ts) -> np.ndarray:
    if i not in _W["theta"]:
        from pipeline.model.holo.learned import convert
        torch = _W["torch"]
        arr, mask = convert.traps_to_input(setup, ts)
        with torch.no_grad():
            out = _W["net"](torch.as_tensor(arr), torch.as_tensor(mask))
        _W["theta"][i] = out[0, : len(ts)].numpy().astype(np.float64)
    return _W["theta"][i]


def _summ(res) -> dict:
    h = res.history
    return {"rel_std": [x["rel_std"] for x in h], "eff": [x["efficiency"] for x in h], "uni": [x["uniformity"] for x in h]}


def _task(job):
    arm, i, seed, start, n_fix = job
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.types import Budget
    from pipeline.model.holo.methods.baseline import m04_gs, m06_gsw, m07_phase_fixed_wgs as m07
    from pipeline.model.holo.methods.learned import b3_warm_start as b3
    name, setup, ts, tgt = _geom(i)
    if start == "m04":
        return (arm, i, seed, _summ(m04_gs.run(setup, tgt, budget=Budget(BUDGET), rng=Rng(seed), form="point")))
    if start == "m06":
        return (arm, i, seed, _summ(m06_gsw.run(setup, tgt, budget=Budget(BUDGET), rng=Rng(seed), form="point")))
    init = None
    if start == "net":
        init = b3.start_hologram(setup, ts, _theta(i, setup, ts))
    elif start == "oracle":
        ref = m07.run(setup, tgt, budget=Budget(BUDGET), rng=Rng(seed), form="point")
        init = b3.start_hologram(setup, ts, np.angle(ref.fields))
    res = m07.run(setup, tgt, budget=Budget(BUDGET), rng=Rng(seed), init=init, n_fix=n_fix, form="point")
    return (arm, i, seed, _summ(res))


def _weights_task(job):
    """Weight accounting of one run: spread of log g after each update and the per-iteration allowance log(max B / min B)."""
    arm, i, seed, n_fix, oracle = job
    from pipeline.model.holo.core.rng import Rng
    from pipeline.model.holo.core.types import Budget
    from pipeline.model.holo.methods.baseline import _gs, m07_phase_fixed_wgs as m07
    from pipeline.model.holo.methods.baseline._common import amp_targets
    from pipeline.model.holo.methods.learned import b3_warm_start as b3
    name, setup, ts, tgt = _geom(i)
    init = None
    if oracle:
        ref = m07.run(setup, tgt, budget=Budget(BUDGET), rng=Rng(seed), form="point")
        init = b3.start_hologram(setup, ts, np.angle(ref.fields))
    state = {"n_fix": n_fix}
    a = amp_targets(ts)
    log: dict = {"allow": [], "spread": []}

    def rule(st, v, k):
        out = _gs.rule_wgs_fixed(st, v, k)
        if k > 1:
            b = np.maximum(np.abs(v) / a, 1e-300)
            log["allow"].append(float(np.log(b.max() / b.min())))
            lw = np.log(st["w"])
            log["spread"].append(float(lw.max() - lw.min()))
        return out

    res = _gs.run_traps("M07", setup, ts, Budget(BUDGET), Rng(seed), init, "point", rule, state)
    iters = _first_below([x["rel_std"] for x in res.history])
    return (arm, i, seed, {"allow": log["allow"], "spread": log["spread"], "iters": iters})


def _names():
    return [(n, int(len(a)), int(p)) for n, a, p in _W["sets"]]


def _first_below(sig, thr: float = 1.0, cap: int = BUDGET) -> int:
    for k, v in enumerate(sig):
        if v <= thr:
            return k + 1
    return cap + 1


def _med(x):
    return float(np.median(np.asarray(x, dtype=np.float64)))


def _boot_median(vals: np.ndarray, rng) -> list:
    idx = rng.integers(0, len(vals), size=(BOOT, len(vals)))
    m = np.median(vals[idx], axis=1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def _sign_test(a: np.ndarray, b: np.ndarray) -> dict:
    """Exact two-sided sign test of a - b over geometries (ties dropped)."""
    d = a - b
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    n = pos + neg
    k = min(pos, neg)
    p = min(1.0, 2.0 * sum(math.comb(n, j) for j in range(k + 1)) / 2.0**n) if n else 1.0
    return {"a_larger": pos, "b_larger": neg, "ties": int((d == 0).sum()), "p": p}


def _ckpt_info(learned: str) -> dict:
    import torch
    from pipeline.model.holo.learned import nets
    ck = torch.load(Path(learned) / "checkpoints" / "ws-final" / "ckpt.pt", map_location="cpu", weights_only=False)
    c = ck["cfg"]
    net = nets.SetNet(c["d"], c["heads"], c["layers"], c["ff"])
    net.load_state_dict(ck["net"])
    return {"step": int(ck["step"]), "params": int(sum(p.numel() for p in net.parameters())), "cfg": c, "chirp0": float(net.chirp0.detach())}


def compute(learned: str, workers: int, out: Path) -> dict:
    from pipeline.model.holo.learned import heldout
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    sha = heldout.sha256_file(Path(learned) / "warmstart-heldout.npz")
    if sha != rec["candidate"]["heldout_sha256"]:
        raise SystemExit(f"held-out file differs from the record: {sha}")
    t0 = time.time()
    ctx = mp.get_context("spawn")
    n_geo = 66
    sweep_idx = [i for i in range(60) if i % 2 == 0]
    with ctx.Pool(workers, initializer=_init, initargs=(learned,)) as pool:
        jobs = []
        arms = {"R12": ("random", 12), "R3": ("random", 3), "N3": ("net", 3), "N12": ("net", 12)}
        for arm, (st, nf) in arms.items():
            jobs += [(arm, i, s, st, nf) for i in range(n_geo) for s in SEEDS]
        jobs += [("M04", i, s, "m04", 0) for i in range(n_geo) for s in SEEDS]
        jobs += [("M06", i, s, "m06", 0) for i in range(n_geo) for s in SEEDS]
        for nf in SWEEP_NFIX:
            jobs += [(f"R{nf}", i, s, "random", nf) for i in sweep_idx for s in SEEDS]
        for nf in (1, 2, 4, 6, 8):
            jobs += [(f"N{nf}", i, s, "net", nf) for i in sweep_idx for s in SEEDS]
        for nf in (1, 3, 12):
            jobs += [(f"O{nf}", i, 301, "oracle", nf) for i in range(ORACLE_N)]
        raw = pool.map(_task, jobs, chunksize=2)
        wjobs = [(f"W{nf}", i, 301, nf, False) for nf in (3, 12) for i in range(ORACLE_N)]
        wjobs += [(f"WO{nf}", i, 301, nf, True) for nf in (3, 12) for i in range(ORACLE_N)]
        wraw = pool.map(_weights_task, wjobs, chunksize=1)
        names = pool.apply(_names)
    runs: dict = {}
    for arm, i, seed, s in raw:
        runs.setdefault(arm, {})[(i, seed)] = s

    def seeds_of(arm):
        return (301,) if arm[0] == "O" else SEEDS

    def per_geo(arm, geos):
        its, fin, eff, uni = [], [], [], []
        for i in geos:
            rr = [runs[arm][(i, s)] for s in seeds_of(arm)]
            its.append(_med([_first_below(r["rel_std"]) for r in rr]))
            fin.append(_med([r["rel_std"][-1] for r in rr]))
            eff.append(_med([r["eff"][-1] for r in rr]))
            uni.append(_med([r["uni"][-1] for r in rr]))
        return np.array(its), np.array(fin), np.array(eff), np.array(uni)

    def never(arm, geos):
        return float(np.mean([_first_below(runs[arm][(i, s)]["rel_std"]) > BUDGET for i in geos for s in seeds_of(arm)]))

    rng = np.random.default_rng(BOOT_SEED)
    allg = list(range(n_geo))
    res: dict = {"arms": {}, "geometries": names, "seeds": list(SEEDS), "budget": BUDGET, "heldout_sha256": sha}
    for arm in ("R12", "R3", "N3", "N12"):
        its, fin, eff, uni = per_geo(arm, allg)
        res["arms"][arm] = {
            "iters_per_geo": its.tolist(), "final_rel_std_per_geo": fin.tolist(), "final_eff_per_geo": eff.tolist(), "final_uni_per_geo": uni.tolist(),
            "iters_median": _med(its), "iters_q1": float(np.percentile(its, 25)), "iters_q3": float(np.percentile(its, 75)),
            "iters_ci": _boot_median(its, rng), "never_runs": never(arm, allg), "never_geos": int((its > BUDGET).sum()),
            "final_rel_std_median": _med(fin), "final_rel_std_ci": _boot_median(fin, rng),
            "eff_median": _med(eff), "uni_median": _med(uni)}
        tr = np.array([[np.median([runs[arm][(i, s)]["rel_std"][k] for s in SEEDS]) for k in range(BUDGET)] for i in allg])
        res["arms"][arm]["trace_median"] = np.median(tr, axis=0).tolist()
        res["arms"][arm]["trace_q1"] = np.percentile(tr, 25, axis=0).tolist()
        res["arms"][arm]["trace_q3"] = np.percentile(tr, 75, axis=0).tolist()
    A = {k: np.array(v["iters_per_geo"]) for k, v in res["arms"].items()}
    E = {k: np.array(v["final_eff_per_geo"]) for k, v in res["arms"].items()}

    def ratio_ci(num, den):
        idx = rng.integers(0, n_geo, size=(BOOT, n_geo))
        r = np.median(num[idx], axis=1) / np.median(den[idx], axis=1)
        return {"ratio": float(np.median(num) / np.median(den)), "ci": [float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))]}

    res["ratios"] = {"R12_over_N3": ratio_ci(A["R12"], A["N3"]), "R12_over_R3": ratio_ci(A["R12"], A["R3"]),
                     "R3_over_N3": ratio_ci(A["R3"], A["N3"]), "R12_over_N12": ratio_ci(A["R12"], A["N12"])}
    res["sign_tests"] = {"R12_vs_N3": _sign_test(A["R12"], A["N3"]), "R3_vs_N3": _sign_test(A["R3"], A["N3"]),
                         "R12_vs_R3": _sign_test(A["R12"], A["R3"]), "R12_vs_N12": _sign_test(A["R12"], A["N12"])}
    ed = {f"{a}_vs_R12": float(abs(np.median(E[a]) - np.median(E["R12"])) / np.median(E["R12"])) for a in ("R3", "N3", "N12")}
    ed["N3_vs_R3"] = float(abs(np.median(E["N3"]) - np.median(E["R3"])) / np.median(E["R3"]))
    res["eff_rel_diff"] = ed
    refs = {}
    for arm in ("M04", "M06"):
        its, fin, eff, uni = per_geo(arm, allg)
        refs[arm] = {"iters_median": _med(its), "iters_ci": _boot_median(its, rng), "never_runs": never(arm, allg), "final_rel_std_median": _med(fin), "eff_median": _med(eff)}
    res["refs"] = refs
    res["groups"] = {arm: {"gen": _med(A[arm][:60]), "bench": _med(A[arm][60:])} for arm in A}
    sweep = {}
    for key, arm, start in [(str(nf), f"R{nf}", "random") for nf in sorted(set(SWEEP_NFIX) | {3, 12})] + [(f"net{nf}", f"N{nf}", "network") for nf in (1, 2, 3, 4, 6, 8, 12)]:
        its, fin, eff, uni = per_geo(arm, sweep_idx)
        sweep[key] = {"start": start, "n": len(sweep_idx), "iters_median": _med(its), "iters_q3": float(np.percentile(its, 75)),
                      "iters_ci": _boot_median(its, rng), "never_runs": never(arm, sweep_idx),
                      "final_rel_std_median": _med(fin), "eff_median": _med(eff)}
    res["sweep"] = sweep
    orc = {"geometries": [names[i][0] for i in range(ORACLE_N)], "traps": [names[i][1] for i in range(ORACLE_N)], "seed": 301}
    for nf in (1, 3, 12):
        orc[f"O{nf}"] = [float(_first_below(runs[f"O{nf}"][(i, 301)]["rel_std"])) for i in range(ORACLE_N)]
    for arm in ("R12", "R3", "N3"):
        orc[arm] = [float(_first_below(runs[arm][(i, 301)]["rel_std"])) for i in range(ORACLE_N)]
    res["oracle"] = orc
    wsum: dict = {}
    for arm, i, seed, d in wraw:
        wsum.setdefault(arm, []).append({"geometry": names[i][0], "allow": d["allow"], "spread": d["spread"], "iters": d["iters"]})
    out_w = {}
    for arm, lst in wsum.items():
        rows = []
        for d in lst:
            cum = np.cumsum(d["allow"])
            s_star = d["spread"][-1]
            kfloor = int(np.argmax(cum >= s_star)) + 2 if (cum >= s_star).any() else None
            rows.append({"geometry": d["geometry"], "S_final": s_star, "S_at_k": d["spread"][:20], "cum_allow": cum[:20].tolist(),
                         "bound_holds": bool(np.all(np.array(d["spread"]) <= cum + 1e-9)), "k_floor": kfloor, "iters": d["iters"]})
        out_w[arm] = rows
    res["weights"] = out_w
    log = [json.loads(x) for x in (Path(learned) / "checkpoints" / "ws-final" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    res["training"] = {"step": [r["step"] for r in log], "loss": [r["loss"] for r in log],
                       "sig_net_last": [r["sig"][-1] for r in log], "sig_random_last": [r["sig_random"][-1] for r in log],
                       "t": [r["t"] for r in log], "sig_net_first": [r["sig"][0] for r in log], "sig_random_first": [r["sig_random"][0] for r in log], "eff": [r["eff"] for r in log]}
    from pipeline.model.holo.learned import evaluation as _ev
    st = _ev.SETUP256
    res["setup"] = {"n_pix": st.n_pix, "pad": st.pad, "wavelength_nm": st.wavelength_m * 1e9, "focal_mm": st.focal_m * 1e3, "pitch_um": st.pitch_m * 1e6, "na": st.na}
    res["model"] = _ckpt_info(learned)
    res["record"] = {"iters_model": rec["metrics"]["iterations_to_1pct"]["model"], "iters_random": rec["metrics"]["iterations_to_1pct"]["random"],
                     "ratio": rec["ratio_random_over_model_median_iterations"], "eff_diff": rec["final_metrics_relative_difference_of_medians"],
                     "onnx_bytes": rec["candidate"]["onnx_bytes"], "parity": rec["candidate"]["parity_wrapped_abs_diff"]["max"],
                     "control": rec["control_without_the_network"], "config": rec["candidate"]["config"]}
    res["runtime_s"] = time.time() - t0
    res["workers"] = workers
    res["command"] = "E:/_venvs/CEFOP_DinHot-gpu/Scripts/python.exe manuscripts/learned-warm-start/data/measure.py --workers %d" % workers
    out.write_text(json.dumps(res), encoding="utf-8")
    return res


# ------------------------------------------------------------------------------------------------ emit
def g(x, nd=1):
    """Number text without trailing zeros."""
    s = f"{x:.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def emit(d: dict, outdir: Path) -> None:
    A, R, S = d["arms"], d["ratios"], d["sweep"]
    M = []

    def mac(name, val):
        M.append(f"\\newcommand{{\\{name}}}{{{val}}}")

    names = d["geometries"]
    traps = [n[1] for n in names]
    mac("nGeo", len(names)); mac("nGen", 60); mac("nBench", 6)
    mac("nSeeds", len(d["seeds"])); mac("budget", d["budget"])
    mac("trapsMin", min(traps[:60])); mac("trapsMax", max(traps[:60])); mac("trapsMed", int(np.median(traps[:60])))
    mac("benchTrapsMax", max(traps[60:])); mac("benchTrapsMin", min(traps[60:]))
    for arm, key in (("R12", "RTwelve"), ("R3", "RThree"), ("N3", "NThree"), ("N12", "NTwelve")):
        a = A[arm]
        mac(f"it{key}", g(a["iters_median"])); mac(f"it{key}Lo", g(a["iters_ci"][0])); mac(f"it{key}Hi", g(a["iters_ci"][1]))
        mac(f"it{key}Qa", g(a["iters_q1"])); mac(f"it{key}Qb", g(a["iters_q3"]))
        mac(f"never{key}", g(100 * a["never_runs"])); mac(f"neverGeo{key}", a["never_geos"])
        mac(f"fin{key}", f"{a['final_rel_std_median']:.3g}"); mac(f"effm{key}", f"{a['eff_median']:.3f}")
    for k, key in (("R12_over_N3", "RoverN"), ("R12_over_R3", "RoverRThree"), ("R3_over_N3", "RThreeoverN"), ("R12_over_N12", "RoverNTwelve")):
        mac(f"ratio{key}", g(R[k]["ratio"], 2)); mac(f"ratio{key}Lo", g(R[k]["ci"][0], 2)); mac(f"ratio{key}Hi", g(R[k]["ci"][1], 2))
    for k, key in (("R12_vs_N3", "RN"), ("R3_vs_N3", "RThreeN"), ("R12_vs_R3", "RRThree"), ("R12_vs_N12", "RNTwelve")):
        t = d["sign_tests"][k]
        mac(f"signA{key}", t["a_larger"]); mac(f"signB{key}", t["b_larger"]); mac(f"signT{key}", t["ties"]); mac(f"signP{key}", f"{t['p']:.2g}")
    for k, key in (("R3_vs_R12", "RThree"), ("N3_vs_R12", "NThree"), ("N12_vs_R12", "NTwelve"), ("N3_vs_R3", "NThreeRThree")):
        mac(f"effd{key}", g(100 * d["eff_rel_diff"][k]))
    mac("recRatio", g(d["record"]["ratio"], 2)); mac("recEff", g(100 * d["record"]["eff_diff"]["efficiency"])); mac("recUni", g(100 * d["record"]["eff_diff"]["uniformity"]))
    mac("onnxBytes", f"{d['record']['onnx_bytes']:,}".replace(",", "\\,")); mac("parityMax", f"{d['record']['parity']:.1e}".replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}")
    mac("nParams", f"{d['model']['params']:,}".replace(",", "\\,")); mac("trainSteps", d["model"]["step"])
    mac("runtimeMin", g(d["runtime_s"] / 60)); mac("nWorkers", d["workers"])
    for grp in ("gen", "bench"):
        for arm, key in (("R12", "RTwelve"), ("N3", "NThree"), ("R3", "RThree")):
            mac(f"{grp}It{key}", g(d["groups"][arm][grp]))
    wn = {1: "One", 2: "Two", 3: "Three", 4: "Four", 6: "Six", 8: "Eight", 12: "Twelve"}
    for nf in (1, 2, 3, 4, 6, 8, 12):
        s = S[str(nf)]; w = wn[nf]
        mac(f"sw{w}", g(s["iters_median"])); mac(f"sw{w}Never", g(100 * s["never_runs"])); mac(f"sw{w}Fin", f"{s['final_rel_std_median']:.3g}")
    for nf in (1, 2, 3, 4, 6, 8, 12):
        s = S[f"net{nf}"]; w = wn[nf]
        mac(f"swn{w}", g(s["iters_median"])); mac(f"swn{w}Never", g(100 * s["never_runs"])); mac(f"swn{w}Fin", f"{s['final_rel_std_median']:.3g}")
    o = d["oracle"]
    for k, key in (("O1", "OOne"), ("O3", "OThree"), ("O12", "OTwelve"), ("R12", "OR"), ("R3", "ORThree"), ("N3", "ONet")):
        v = np.array(o[k])
        mac(f"{key}Med", g(float(np.median(v)))); mac(f"{key}Min", int(v.min())); mac(f"{key}Max", int(v.max()))
    W = d["weights"]
    for arm, key in (("W12", "wTwelve"), ("W3", "wThree"), ("WO12", "woTwelve"), ("WO3", "woThree")):
        rows = W[arm]
        kf = [r["k_floor"] for r in rows if r["k_floor"] is not None]
        mac(f"{key}Hold", sum(r["bound_holds"] for r in rows)); mac(f"{key}N", len(rows))
        mac(f"{key}SMed", g(float(np.median([r["S_final"] for r in rows])), 2))
        mac(f"{key}KMed", g(float(np.median(kf))) if kf else "none"); mac(f"{key}KMin", min(kf) if kf else "none"); mac(f"{key}KMax", max(kf) if kf else "none")
        mac(f"{key}ItMed", g(float(np.median([r["iters"] for r in rows]))))
    st = d["setup"]
    mac("nPixGen", st["n_pix"]); mac("padGen", st["pad"]); mac("lambdaNm", g(st["wavelength_nm"])); mac("focalMm", g(st["focal_mm"])); mac("pitchUm", g(st["pitch_um"], 1))
    mac("chirpFinal", g(d["model"]["chirp0"], 2))
    kw = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen"}
    for arm, key in (("R12", "RTwelve"), ("R3", "RThree"), ("N3", "NThree"), ("N12", "NTwelve")):
        for k, w in kw.items():
            v = A[arm]["trace_median"][k - 1]
            mac(f"tr{key}{w}", g(v, 2) if v >= 0.1 else f"{v:.2g}")
    for nf in (3, 4, 6, 8, 12):
        s_ = S[str(nf)]
        mac(f"sw{wn[nf]}Ex", g(s_["iters_median"] - nf) if s_["iters_median"] <= d["budget"] else "none")
    r3_ = np.array(A["R3"]["iters_per_geo"]); n3_ = np.array(A["N3"]["iters_per_geo"])
    mac("capRNotN", int(((r3_ > d["budget"]) & (n3_ <= d["budget"])).sum())); mac("capNNotR", int(((n3_ > d["budget"]) & (r3_ <= d["budget"])).sum()))
    mac("capBoth", int(((n3_ > d["budget"]) & (r3_ > d["budget"])).sum()))
    mac("OTwelveGain", g(float(np.median(o["R12"])) - float(np.median(o["O12"]))))
    for arm, key in (("M04", "MFour"), ("M06", "MSix")):
        r_ = d["refs"][arm]
        mac(f"it{key}", g(r_["iters_median"])); mac(f"it{key}Lo", g(r_["iters_ci"][0])); mac(f"it{key}Hi", g(r_["iters_ci"][1]))
        mac(f"never{key}", g(100 * r_["never_runs"])); mac(f"fin{key}", f"{r_['final_rel_std_median']:.3g}"); mac(f"effm{key}", f"{r_['eff_median']:.3f}")
    mac("trainMinutes", g(tr_t / 60) if (tr_t := d["training"]["t"][-1]) else "none")
    tr = d["training"]
    mac("trainFirstLoss", g(tr["loss"][0], 2)); mac("trainLastLoss", g(float(np.mean(tr["loss"][-10:])), 2))
    mac("trainSigNet", g(float(np.median(tr["sig_net_last"][-20:])), 3)); mac("trainSigRand", g(float(np.median(tr["sig_random_last"][-20:])), 3))
    mac("trainSigNetFirst", g(float(np.median(tr["sig_net_first"][-20:]))))
    mac("trainSigRandFirst", g(float(np.median(tr["sig_random_first"][-20:]))))
    rc = d["record"]["control"]["median_and_q3_iterations"]
    mac("ctrlRTwelve", g(rc["random_nfix12"][0])); mac("ctrlRThree", g(rc["random_nfix3"][0])); mac("ctrlNThree", g(rc["model_nfix3"][0]))
    mac("recMedModel", g(d["record"]["iters_model"]["median"])); mac("recMedRandom", g(d["record"]["iters_random"]["median"]))
    (outdir / "warm_numbers.tex").write_text("% Generated by data/measure.py from warm.json. Do not edit.\n" + "\n".join(M) + "\n", encoding="utf-8")

    def row(cells):
        return " & ".join(cells) + " \\\\\n"

    t = "\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n" + row(["Start", "$n_{\\mathrm{fix}}$", "Median it. [95\\% CI]", "Q1--Q3", "Never (\\%)", "Final $\\sigma$ (\\%)", "Efficiency"]) + "\\midrule\n"
    for arm, lab, nf in (("R12", "random (engine default)", 12), ("R3", "random", 3), ("N3", "network (candidate)", 3), ("N12", "network", 12)):
        a = A[arm]
        t += row([lab, str(nf), f"{g(a['iters_median'])} [{g(a['iters_ci'][0])}, {g(a['iters_ci'][1])}]", f"{g(a['iters_q1'])}--{g(a['iters_q3'])}", g(100 * a["never_runs"]), f"{a['final_rel_std_median']:.3g}", f"{a['eff_median']:.3f}"])
    for arm, lab in (("M04", "Gerchberg--Saxton, random start"), ("M06", "weighted GS, random start")):
        r_ = d["refs"][arm]
        t += row([lab, "--", f"{g(r_['iters_median'])} [{g(r_['iters_ci'][0])}, {g(r_['iters_ci'][1])}]", "--", g(100 * r_["never_runs"]), f"{r_['final_rel_std_median']:.3g}", f"{r_['eff_median']:.3f}"])
    (outdir / "tab_main.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

    t = "\\begin{tabular}{@{}lccrrr@{}}\n\\toprule\n" + row(["Arm", "Network start", "Early freeze", "Median it.", "Ratio to the default [95\\% CI]", "Sign test $p$"]) + "\\midrule\n"
    t += row(["engine default", "no", "no", g(A["R12"]["iters_median"]), "1", "--"])
    for lab, ns, ef, arm, key, sk in (("early freeze only", "no", "yes", "R3", "R12_over_R3", "R12_vs_R3"), ("network only", "yes", "no", "N12", "R12_over_N12", "R12_vs_N12"),
                                       ("network and early freeze", "yes", "yes", "N3", "R12_over_N3", "R12_vs_N3")):
        t += row([lab, ns, ef, g(A[arm]["iters_median"]), f"{R[key]['ratio']:.2f} [{R[key]['ci'][0]:.2f}, {R[key]['ci'][1]:.2f}]", f"{d['sign_tests'][sk]['p']:.2g}"])
    (outdir / "tab_ablation.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

    t = "\\begin{tabular}{@{}rrrrrrr@{}}\n\\toprule\n" + row(["$n_{\\mathrm{fix}}$", "Random: median it.", "Never (\\%)", "Final $\\sigma$ (\\%)", "Network: median it.", "Never (\\%)", "Final $\\sigma$ (\\%)"]) + "\\midrule\n"
    for nf in (1, 2, 3, 4, 6, 8, 12):
        s = S[str(nf)]
        nn = S.get(f"net{nf}")
        t += row([str(nf), g(s["iters_median"]), g(100 * s["never_runs"]), f"{s['final_rel_std_median']:.3g}"] + ([g(nn["iters_median"]), g(100 * nn["never_runs"]), f"{nn['final_rel_std_median']:.3g}"] if nn else ["--", "--", "--"]))
    (outdir / "tab_sweep.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

    t = "\\begin{tabular}{@{}lrrrrrr@{}}\n\\toprule\n" + row(["Held-out geometry", "Traps", "Random, 12", "Oracle, 12", "Random, 3", "Oracle, 3", "Oracle, 1"]) + "\\midrule\n"
    for i in range(ORACLE_N):
        t += row([names[i][0].replace("_", "\\_"), str(names[i][1]), g(o["R12"][i]), g(o["O12"][i]), g(o["R3"][i]), g(o["O3"][i]), g(o["O1"][i])])
    (outdir / "tab_oracle.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

    t = "\\begin{tabular}{@{}lrrrr@{}}\n\\toprule\n" + row(["Run (seed 301, ten geometries)", "Median final $S$", "Median $k_{\\mathrm{floor}}$", "Median it. to 1\\%", "Bound holds"]) + "\\midrule\n"
    for arm, lab in (("W12", "random start, $n_{\\mathrm{fix}}=12$"), ("W3", "random start, $n_{\\mathrm{fix}}=3$"), ("WO12", "oracle start, $n_{\\mathrm{fix}}=12$"), ("WO3", "oracle start, $n_{\\mathrm{fix}}=3$")):
        rows = W[arm]
        kf = [r["k_floor"] for r in rows if r["k_floor"] is not None]
        t += row([lab, f"{np.median([r['S_final'] for r in rows]):.2f}", g(float(np.median(kf))) if kf else "--", g(float(np.median([r["iters"] for r in rows]))), f"{sum(r['bound_holds'] for r in rows)} of {len(rows)}"])
    (outdir / "tab_weights.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")

    t = "\\begin{tabular}{@{}lrrll@{}}\n\\toprule\n" + row(["Group", "Geometries", "Traps", "Grid", "Origin"]) + "\\midrule\n"
    t += row(["generated, demanding", "60", f"{min(traps[:60])}--{max(traps[:60])}", "$256^2$, pad 2", "fresh seed; at least 40 traps; the random start needs more than 3 iterations"])
    for n, m_, p in names[60:]:
        t += row([f"benchmark {n.split('/')[1]}", "1", str(m_), f"${p}^2$", "benchmark geometry record"])
    (outdir / "tab_heldout.tex").write_text(t + "\\bottomrule\n\\end{tabular}\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--learned-dir", default=os.environ.get("DINHOT_LEARNED_DIR", DEFAULT_LEARNED))
    ap.add_argument("--emit-only", action="store_true")
    a = ap.parse_args()
    out = HERE / "warm.json"
    d = json.loads(out.read_text(encoding="utf-8")) if a.emit_only else compute(a.learned_dir, a.workers, out)
    emit(d, HERE)
    print("done; run time (s):", round(d["runtime_s"], 1))


if __name__ == "__main__":
    main()
