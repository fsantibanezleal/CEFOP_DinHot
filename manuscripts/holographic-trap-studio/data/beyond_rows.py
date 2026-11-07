"""Acceptance rows of B1 and B2 for the technical report, read from the measurements of the companion manuscript.

``acceptance.py`` measures M01 to M19, B4 and B5 as their gate tests do. B1 and B2 are measured by
``manuscripts/device-aware-flicker-bounded/data/measure.py`` into ``beyond.json`` (more seeds than the gate tests use), and this
module turns that file into the two rows of the acceptance table, so that the report states every method with a measurement and
no number is typed. Standard library only; imported by ``extract.py`` and ``extract_methods.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEYOND = HERE.parents[1] / "device-aware-flicker-bounded" / "data" / "beyond.json"


def _iv(s: dict, nd: int) -> str:
    """``median [min, max]`` of a summary block of beyond.json."""
    return f"{s['median']:.{nd}f} [{s['min']:.{nd}f}, {s['max']:.{nd}f}]"


def rows() -> list[dict]:
    d = json.loads(BEYOND.read_text(encoding="utf-8"))
    x, f = d["bs1_crosstalk"]["summary"], d["bs1_full_device"]["summary"]
    n1, n2 = x["sigma_b1"]["n"], f["sigma_b1"]["n"]
    b1 = (f"crosstalk device, 10 x 10 task: relative standard deviation {_iv(x['sigma_b1'], 2)} percent against "
          f"{_iv(x['sigma_m07_100'], 2)} for M07 at 100 iterations (a factor {_iv(x['sigma_ratio'], 0)}) at {_iv(x['eff_ratio'], 3)} "
          f"of its efficiency; 4-bit device with fill 0.85: {_iv(f['sigma_b1'], 2)} against {_iv(f['sigma_m07_100'], 2)} "
          f"(a factor {_iv(f['sigma_ratio'], 1)}) at {_iv(f['eff_ratio'], 3)} of its efficiency; taken from the companion manuscript's "
          f"beyond.json, {n1} and {n2} seeds")
    s13 = d["bs2"]["summary"]["13"]
    b2 = (f"4 x 4 lattice, two columns moved by four bins in 13 frames: lowest transient intensity of a moving trap "
          f"{_iv(s13['b2_min'], 3)} of its mean against {_iv(s13['lpi_min'], 3)} for linear phase interpolation; largest per-frame "
          f"spread {_iv(s13['b2_sigma_frame_max'], 2)} against {_iv(s13['lpi_sigma_frame_max'], 1)} percent; taken from the companion "
          f"manuscript's beyond.json, {s13['b2_min']['n']} seeds")
    src = "manuscripts/device-aware-flicker-bounded/data/measure.py (beyond.json)"
    return [{"id": "B1", "text": b1, "seeds": f"{n1} and {n2}", "source": src, "numbers": x},
            {"id": "B2", "text": b2, "seeds": str(s13["b2_min"]["n"]), "source": src, "numbers": s13}]
