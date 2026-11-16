#!/usr/bin/env python3
"""B1 at its default, with its weight update and with the loss of Schroff et al. on the lattices of the benchmark, on the ideal model and the C08 device.

Every cell is the benchmark's own record (``pipeline.benchmark.geometries.record``) run through ``stages.infer.run_method``
and scored by ``core/score.py`` against its device, as the benchmark does, at a budget of 10 outer iterations and for the
seeds 0 to 4 (five, the floor of the win rule). The three variants differ only in ``B1.run(weights=..., loss=...)``: ``no_weights`` is the
default of 0.02.004, ``weights`` is the weight update on (the 0.02.003 form) and ``schroff`` is the normalized-error loss of Schroff et al.
2023, the closest published method, through the same warm start, device model, conjugate gradient and safeguard. One geometry takes about half an hour, so the
geometries run as separate processes:

    python manuscripts/device-aware-flicker-bounded/data/b1_weights_geo.py run G1      # one per geometry, G1 to G4
    python manuscripts/device-aware-flicker-bounded/data/b1_weights_geo.py write       # table and macros from the JSON files

``run`` writes ``b1_weights_geo_<G>.json``; ``write`` reads them and writes ``tab_abl_b1_geo.tex`` and ``b1geo_numbers.tex``.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

GEOS = ("G1", "G2", "G3", "G4")
SEEDS = (0, 1, 2, 3, 4)
ITERATIONS = 10
VARIANTS = (("weights", {"weights": True}), ("no_weights", {"weights": False}),
            ("schroff", {"weights": False, "loss": "normalized-error"}))
LETTERS = {"G1": "A", "G2": "B", "G3": "C", "G4": "D"}


def run(geometry: str) -> None:
    from pipeline.benchmark import geometries as G  # noqa: PLC0415
    from pipeline.model.holo.core.types import Budget  # noqa: PLC0415
    from pipeline.stages import infer  # noqa: PLC0415

    rows = []
    for device in (False, True):
        for seed in SEEDS:
            rec = G.record(geometry, device=device, seed=seed, reduced=False)
            ctx = infer.case_context(rec)
            row = {"geometry": geometry, "device": device, "seed": seed, "iterations": ITERATIONS}
            for label, extra in VARIANTS:
                t0 = time.perf_counter()
                out = infer.run_method(rec, "B1", budget=Budget(ITERATIONS), extra=extra, ctx=ctx)
                row[label] = {"sigma": out.score["rel_std_pct"], "eff": out.score["efficiency"],
                              "u": out.score["uniformity"], "s": time.perf_counter() - t0}
            rows.append(row)
            print(geometry, "device" if device else "ideal", seed,
                  f"weights {row['weights']['sigma']:.3f}/{row['weights']['eff']:.3f}",
                  f"no weights {row['no_weights']['sigma']:.3f}/{row['no_weights']['eff']:.3f}",
                  f"Schroff {row['schroff']['sigma']:.3f}/{row['schroff']['eff']:.3f}", flush=True)
    (HERE / f"b1_weights_geo_{geometry}.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


def _fmt(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}"


def write() -> None:
    from pipeline.benchmark import geometries as G  # noqa: PLC0415

    rows = [r for g in GEOS for r in json.loads((HERE / f"b1_weights_geo_{g}.json").read_text(encoding="utf-8"))]
    lines = [r"\begin{tabular}{@{}l r r r r r r r r@{}}", r"\toprule",
             r"Geometry & $\sigma$ with weights (\%) & $\sigma$ default (\%) & $\sigma$ Schroff (\%) & $e$ with & $e$ default & $e$ Schroff & "
             r"seeds default below weights & seeds default below Schroff\\",
             r"\midrule"]
    macros = ["% Device-aware WGS with and without the weight update on the benchmark lattices, C08 device (data/b1_weights_geo.py).\n"]
    for g in GEOS:
        sel = [r for r in rows if r["geometry"] == g and r["device"]]
        med = {k: {f: statistics.median(r[k][f] for r in sel) for f in ("sigma", "eff")} for k, _ in VARIANTS}
        lower = sum(r["no_weights"]["sigma"] < r["weights"]["sigma"] - 1e-9 for r in sel)
        lower_s = sum(r["no_weights"]["sigma"] < r["schroff"]["sigma"] - 1e-9 for r in sel)
        name = G.GEOMETRIES[g][0]["en"]
        lines.append(f"{g}, {name} & {_fmt(med['weights']['sigma'])} & {_fmt(med['no_weights']['sigma'])} & {_fmt(med['schroff']['sigma'])} & "
                     f"{_fmt(med['weights']['eff'], 3)} & {_fmt(med['no_weights']['eff'], 3)} & {_fmt(med['schroff']['eff'], 3)} & "
                     f"{lower} of {len(sel)} & {lower_s} of {len(sel)}\\\\")
        L = LETTERS[g]
        for k, tag in (("weights", "W"), ("no_weights", "N"), ("schroff", "S")):
            macros.append(f"\\newcommand{{\\geo{L}{tag}Sig}}{{{_fmt(med[k]['sigma'])}}}\n")
            macros.append(f"\\newcommand{{\\geo{L}{tag}Eff}}{{{_fmt(med[k]['eff'], 3)}}}\n")
        macros.append(f"\\newcommand{{\\geo{L}Lower}}{{{lower}}}\n")
        macros.append(f"\\newcommand{{\\geo{L}LowerSchroff}}{{{lower_s}}}\n")
        macros.append(f"\\newcommand{{\\geo{L}Seeds}}{{{len(sel)}}}\n")
        ideal = [r for r in rows if r["geometry"] == g and not r["device"]]
        macros.append(f"\\newcommand{{\\geo{L}IdealMax}}{{{_fmt(max(max(r[k]['sigma'] for k, _ in VARIANTS) for r in ideal), 3)}}}\n")
    lines += [r"\bottomrule", r"\end{tabular}"]
    macros.append(f"\\newcommand{{\\geoSeeds}}{{{len(SEEDS)}}}\n\\newcommand{{\\geoIters}}{{{ITERATIONS}}}\n")
    (HERE / "tab_abl_b1_geo.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (HERE / "b1geo_numbers.tex").write_text("".join(macros), encoding="utf-8")
    print("wrote tab_abl_b1_geo.tex and b1geo_numbers.tex")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        run(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "write":
        write()
    else:
        sys.exit(__doc__)
