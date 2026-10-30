"""Stage 2, feature_extraction: the derived geometry of a validated record (deterministic, no engine run).

``describe`` gives the quantities the gates reason about in the units of the question: trap count, extent in micrometres,
the smallest spacing in focal bins and the fraction of the unaliased half-field the farthest trap uses."""
from __future__ import annotations

import math

from ..io.contract import bin_um, half_field_um

EDGE_FRACTION = 0.85
MAX_PAIRS_TRAPS = 1100


def describe(rec: dict) -> dict:
    s = rec["setup"]
    if rec["target"]["kind"] != "traps":
        return {"n_traps": 0, "extent_um": 0.0, "min_spacing_bins": None, "fov_fraction": 0.0}
    traps = rec["target"]["traps"]
    extent = max(max(abs(t["x_um"]), abs(t["y_um"])) for t in traps)
    dmin = None
    if 1 < len(traps) <= MAX_PAIRS_TRAPS:
        dmin = min(math.dist((a["x_um"], a["y_um"], a["z_um"]), (b["x_um"], b["y_um"], b["z_um"])) for k, a in enumerate(traps) for b in traps[:k])
    return {"n_traps": len(traps), "extent_um": extent,
            "min_spacing_bins": None if dmin is None else dmin / bin_um(s), "fov_fraction": extent / half_field_um(s)}


def flags(rec: dict) -> list[dict[str, str]]:
    f = describe(rec)
    if f["fov_fraction"] >= EDGE_FRACTION:
        return [{"case_id": rec["case_id"], "flag": f"traps use {100 * f['fov_fraction']:.0f} percent of the unaliased field "
                                                    f"of view (the edge is {100 * EDGE_FRACTION:.0f} percent)"}]
    return []
