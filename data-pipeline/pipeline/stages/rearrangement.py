"""The rearrangement driver of a case (catalog row trace, ``rearrangement``; methods M16 and B2).

A site array (the case's traps, row-major ids) is loaded stochastically (one portable-RNG uniform per site against
``loading_p``, ``cases.library.random_loading``). The empty target sites are matched to the surplus atoms by the Hungarian
method with cost ``d^alpha`` (``core/assign.py``; Lee, Kim and Ahn 2017: ``alpha`` above 1 avoids trespassing). All matched
atoms move in parallel along straight lines in ``steps_per_move`` equal steps; frames are ``FRAME_S`` apart (an assumed
SLM refresh of 1 / 3 ms, a parameter of this driver, not of the case). The hologram of every frame is computed by the
registered method ``mid`` with a phase warm start from the previous frame (phase-continuous), and ``min_transient`` is the
lowest intensity of a moving trap relative to the mean trap over the moving frames, the quantity linear phase interpolation
is judged by (arXiv 2501.01391). Frames: the initial one, the moving ones and the final one.
"""
from __future__ import annotations

import math

import numpy as np

from ..cases import build
from ..cases.library import random_loading
from ..core.assign import assign
from ..model.holo.core.forward import point_trap_fields
from ..model.holo.core.types import Budget, Target
from . import infer

FRAME_S = 0.003
FRAME_ITERATIONS = 10


def plan(rec: dict) -> tuple[list[int], list[tuple[int, int]], list[int]]:
    """``(loaded ids, moves (from_id, to_id), target ids still empty after the moves)``."""
    r = rec["rearrangement"]
    xy = {t["id"]: (t["x_um"], t["y_um"]) for t in rec["target"]["traps"]}
    loaded = set(random_loading(rec))
    targets = set(r["target_ids"])
    empty = sorted(targets - loaded)
    surplus = sorted(loaded - targets)
    k = min(len(empty), len(surplus))
    if k == 0:
        return sorted(loaded), [], empty
    # when atoms are short, the targets nearest to a surplus atom are filled first: rows = the smaller set
    rows, cols, swap = (empty, surplus, False) if len(empty) <= len(surplus) else (surplus, empty, True)
    cost = [[math.dist(xy[a], xy[b]) ** r["alpha"] for b in cols] for a in rows]
    pick = assign(cost)
    pairs = [(cols[j], rows[i]) if not swap else (rows[i], cols[j]) for i, j in enumerate(pick)]
    filled = {to for _, to in pairs}
    return sorted(loaded), sorted(pairs), [t for t in empty if t not in filled]


def run(rec: dict, ctx: dict, mid: str) -> tuple[dict, dict[str, float]]:
    """``(trace rearrangement, case metrics)``."""
    r = rec["rearrangement"]
    sites = {t["id"]: t for t in rec["target"]["traps"]}
    loaded, moves, still_empty = plan(rec)
    steps = r["steps_per_move"] if moves else 1
    n_target = len(r["target_ids"])
    moving_from = {a for a, _ in moves}
    static = [i for i in loaded if i not in moving_from]

    frames, filling, phi, transient = [], [], None, []
    target_set = set(r["target_ids"])
    for s in range(steps + 1):
        mv = []
        for a, b in moves:
            f = s / steps
            mv.append({"from": a, "to": b, "x_um": round(sites[a]["x_um"] + f * (sites[b]["x_um"] - sites[a]["x_um"]), 4) + 0.0,
                       "y_um": round(sites[a]["y_um"] + f * (sites[b]["y_um"] - sites[a]["y_um"]), 4) + 0.0})
        at_goal = s == steps
        occupied = sorted(static + ([b for _, b in moves] if at_goal else []))
        moving = [] if at_goal else mv
        frames.append({"t_s": round(s * FRAME_S, 6), "occupied": occupied, "moving": moving})
        in_target = sum(1 for i in occupied if i in target_set)
        filling.append(round(in_target / n_target, 4))
        # the hologram of this frame: static sites plus the moving traps at their positions (ids = origin sites)
        traps = [dict(sites[i]) for i in static + ([b for _, b in moves] if at_goal else [])]
        traps += [{**sites[m["from"]], "id": m["from"], "x_um": m["x_um"], "y_um": m["y_um"]} for m in moving]
        if not traps:
            continue
        ts = build.trapset_of(traps)
        out = infer.run_method(rec, mid, budget=Budget(30 if phi is None else FRAME_ITERATIONS), init=phi,
                               target=Target.from_traps(ts), ctx=ctx)
        phi = out.phi
        if moving and 0 < s < steps:
            raw = np.abs(point_trap_fields(phi, ctx["setup"], ts)) ** 2
            ids = list(map(int, ts.ids))
            moved = [ids.index(m["from"]) for m in moving]
            transient.append(float(raw[moved].min() / raw.mean()))
    min_t = min(transient) if transient else 1.0
    trace = {"frames": frames[:120], "filling": filling[:120], "min_transient": round(min_t, 4)}
    return trace, {"min_transient": min_t, "final_filling": filling[-1]}


__all__ = ["plan", "run"]
