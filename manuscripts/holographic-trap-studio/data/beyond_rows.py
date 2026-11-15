"""Acceptance rows of B1 and B2 for the technical report, read from the measurements of the two companion manuscripts.

``acceptance.py`` measures the published methods, the aberration-robust hologram and the efficiency-uniformity continuation as their gate
tests do. The device-aware refinement is measured by ``manuscripts/device-aware-flicker-bounded/data/measure.py`` into ``beyond.json``
and the flicker-bounded sequence by ``manuscripts/flicker-bounded-sequences/data/measure.py`` into ``flicker.json`` (more seeds than the
gate tests use); this module turns the two files into the two rows of the acceptance table, so that the report states every method with a
measurement and no number is typed. The statistic is the one each companion paper states, and each row names it (review m-5): the
factor as a geometric mean with its 95 percent t interval on the log scale, the transient ratio as a mean with its 95 percent
interval. Standard library only; imported by ``extract.py`` and ``extract_methods.py``.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEYOND = HERE.parents[1] / "device-aware-flicker-bounded" / "data" / "beyond.json"
FLICKER = HERE.parents[1] / "flicker-bounded-sequences" / "data" / "flicker.json"
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def _geo(values: list[float]) -> tuple[float, float, float]:
    """Geometric mean of positive ratios with the two-sided 95 percent t interval on the log scale (the companion paper's statistic)."""
    logs = [math.log(v) for v in values]
    n = len(logs)
    mean = statistics.fmean(logs)
    half = T95.get(n - 1, 1.96) * statistics.stdev(logs) / math.sqrt(n) if n > 1 else float("nan")
    return math.exp(mean), math.exp(mean - half), math.exp(mean + half)


def _mean_ci(s: dict, nd: int) -> str:
    return f"{s['mean']:.{nd}f} (95 percent interval {s['ci_lo']:.{nd}f} to {s['ci_hi']:.{nd}f})"


def rows() -> list[dict]:
    d = json.loads(BEYOND.read_text(encoding="utf-8"))
    fl = json.loads(FLICKER.read_text(encoding="utf-8"))

    def factor(key: str) -> tuple[float, float, float, int]:
        rr = d[key]["rows"]
        g = _geo([min(r["baselines"]["M07_30"]["sigma"], r["baselines"]["M07_100"]["sigma"]) / r["B1"]["sigma"] for r in rr])
        return (*g, len(rr))

    gx, lx, hx, n1 = factor("bs1_crosstalk")
    gf, lf, hf, n2 = factor("bs1_full_device")
    x, f = d["bs1_crosstalk"]["summary"], d["bs1_full_device"]["summary"]
    b1 = (f"crosstalk device, 10 x 10 task: the spread of the device-aware refinement at its default (no weight update) has median "
          f"{x['sigma_b1']['median']:.3f} percent against {x['sigma_m07_100']['median']:.2f} for phase-fixed weighted GS at 100 iterations; "
          f"the factor over the better of the two phase-fixed runs is a geometric mean of {gx:.1f} (95 percent interval {lx:.1f} to {hx:.1f}) "
          f"at a median {x['eff_ratio']['median']:.3f} of its efficiency; 4-bit device with fill 0.85: spread {f['sigma_b1']['median']:.3f} "
          f"against {f['sigma_m07_100']['median']:.2f}, a factor of {gf:.1f} ({lf:.1f} to {hf:.1f}) at a median {f['eff_ratio']['median']:.3f} "
          f"of its efficiency; the statistic is the companion manuscript's (geometric mean of the per-seed factor with its 95 percent "
          f"interval), {n1} and {n2} seeds")
    s13 = fl["accept_summary"]["13"]
    b, l = s13["b2"]["transient_min_ratio"], s13["lpi"]["transient_min_ratio"]
    b2 = (f"4 x 4 lattice, two columns moved by four bins in 13 frames: lowest transient intensity of a moving trap "
          f"{_mean_ci(b, 3)} of its mean against {_mean_ci(l, 3)} for linear phase interpolation; the statistic is the companion "
          f"manuscript's (mean over seeds with its 95 percent interval), {b['n']} seeds")
    src1 = "manuscripts/device-aware-flicker-bounded/data/measure.py (beyond.json)"
    src2 = "manuscripts/flicker-bounded-sequences/data/measure.py (flicker.json)"
    return [{"id": "B1", "text": b1, "seeds": f"{n1} and {n2}", "source": src1, "numbers": x},
            {"id": "B2", "text": b2, "seeds": str(b["n"]), "source": src2, "numbers": s13}]
