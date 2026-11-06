#!/usr/bin/env python3
"""Check of the single-trap reference level against the many-trap efficiency, and write ``ceiling_check.json``.

The report calls ``(mean A)^2`` of Eq. (ceiling) the reference level of the single-trap limit and states that it is not a bound
for many traps. This script measures that statement on the engine: the summed trap intensity ``e = sum_m I_m`` is maximized over
all pixel phases (Adam on the closed-form adjoint of the point-trap model, the engine's own ``TrapForward``) for a Gaussian input
beam, for traps on adjacent focal bins, for traps spread over a line and for a 10 x 10 lattice, and compared with ``(mean A)^2``
and with the bound ``e <= 1`` of Bessel's inequality (traps on distinct bins of a unit-norm pupil field). Nothing is proved
here: the numbers are measured, with the seed and the iteration count in the file.

Run from the repository root with the pipeline environment:

    .venv-pipeline/Scripts/python.exe manuscripts/holographic-trap-studio/data/ceiling_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline.model.holo.core.geometry import Setup, focal_bin_m, input_amplitude  # noqa: E402
from pipeline.model.holo.core.rng import Rng  # noqa: E402
from pipeline.model.holo.core.traps import Trap, TrapSet, square_grid  # noqa: E402
from pipeline.model.holo.methods.optim import _common as C  # noqa: E402

ITERATIONS, LR, SEED = 600, 0.05, 1


def setup256() -> Setup:
    return Setup(wavelength_m=0.85e-6, focal_m=0.25, na=0.5, n_imm=1.0, n_pix=256, pitch_m=12.5e-6, pad=2)


def line(setup: Setup, n: int, gap_bins: float) -> TrapSet:
    b = focal_bin_m(setup)      # the traps are in metres
    return TrapSet(Trap(k, (k - (n - 1) / 2.0) * gap_bins * b, 0.0, 0.0) for k in range(n))


def maximise(setup: Setup, traps: TrapSet) -> float:
    fwd = C.TrapForward(setup, traps)

    def fun(phi):
        v, cache = fwd.fields(phi)
        i = np.abs(v) ** 2
        return -float(np.sum(i)), fwd.adjoint(-v, cache), float(np.sum(i))

    phi0 = Rng(SEED).phases(setup.n_pix**2).reshape(setup.n_pix, setup.n_pix)
    res = C.adam_minimize(fun, phi0, ITERATIONS, lr=LR)
    return float(fun(res.x)[2])


def main() -> int:
    s = setup256()
    level = float(np.mean(input_amplitude(s)) ** 2)
    pad = s.pad
    cases = {
        "ten traps on adjacent bins (gap 1 bin of the padded grid)": line(s, 10, 1.0),
        f"ten traps {pad} bins apart": line(s, 10, float(pad)),
        "ten traps eight bins apart (the spacing of the 10 x 10 task)": line(s, 10, 8.0),
        "10 x 10 lattice at eight bins": square_grid(10, 10, 8 * focal_bin_m(s) * 1e6),
        "one trap": line(s, 1, 1.0),
    }
    out = {"schema": "dinhot.manuscript-ceiling-check/v1", "reference_level_mean_A_squared": level, "iterations": ITERATIONS,
           "adam_lr": LR, "seed": SEED, "efficiency_after_maximisation": {}}
    for name, tr in cases.items():
        out["efficiency_after_maximisation"][name] = maximise(s, tr)
        print(f"{name}: e = {out['efficiency_after_maximisation'][name]:.4f} (reference level {level:.4f})")
    (HERE / "ceiling_check.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
