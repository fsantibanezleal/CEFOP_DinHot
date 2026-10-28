"""The camera feedback loop of a case (catalog row trace, ``feedback``; methods M12 and the Kim variant of C03).

Closed-loop weighted GS on the emulated camera (``core/camera.py``, an emulation whose errors are the record's
``feedback.camera`` parameters): measure the trap intensities, then multiply each trap's target weight by
``1 / (1 - G (1 - I_m / mean(I)))`` (Nogrette et al. 2014, https://arxiv.org/abs/1402.5329, the rescaling
``I' = mean(I) / (1 - G (1 - I / mean(I)))`` read as a factor on the current target; this reading is UNVERIFIED against the
paper's text beyond the formula), and run the case's weight-aware method again from the previous phase. The curve reported
per step is the *measured* spread (relative standard deviation of the camera readings divided by the target weights, in
percent), the quantity Nogrette plot, and the true efficiency of the hologram.
"""
from __future__ import annotations

import numpy as np

from ..cases import build
from ..core import score as scoring
from ..io.schema import MethodOutcome
from ..model.holo.core import metrics
from ..model.holo.core.camera import EmulatedCamera
from ..model.holo.core.types import Budget, Target
from . import infer

STEP_ITERATIONS = 10        # method iterations per feedback step (warm start from the previous phase)
MIN_DENOMINATOR = 0.1       # keeps the factor finite for gains above 1


def run(rec: dict, ctx: dict, mid: str, first: MethodOutcome) -> dict:
    """``{"steps": [{step, rel_std_pct, efficiency}, ...]}`` for the record's feedback block, from ``first`` (step 0)."""
    fb = rec["feedback"]
    cam = fb["camera"]
    camera = EmulatedCamera(rec["seed"], gain_rms=cam["gain_rms"], noise_rms=cam["noise_rms"], blur_bins=cam["blur_bins"],
                            rolloff=False)
    setup, device = ctx["setup"], ctx["device"]
    base = build.traps_of(rec)
    ab = build.aberration_phase(rec, setup)
    ids = [int(i) for i in base.ids]
    w0 = {i: float(w) for i, w in zip(ids, base.weight)}
    weights = dict(w0)
    phi = first.phi
    steps = []
    for k in range(fb["steps"] + 1):
        e = scoring.focal_field(phi, setup, device, ab, rec["seed"])
        measured = camera.measure(e, setup, base)
        rel = measured / np.array([weights_of(w0, ids)]).ravel()
        steps.append({"step": k, "rel_std_pct": round(metrics.rel_std(rel), 4),
                      "efficiency": round(scoring.score(rec, phi, setup=setup, device=device)["efficiency"], 5)})
        if k == fb["steps"]:
            break
        mean = float(rel.mean())
        factor = 1.0 / np.maximum(1.0 - fb["gain"] * (1.0 - rel / mean), MIN_DENOMINATOR)
        new = {i: weights[i] * float(f) for i, f in zip(ids, factor)}
        norm = np.mean(list(w0.values())) / np.mean(list(new.values()))
        weights = {i: v * norm for i, v in new.items()}
        target = Target.from_traps(build.trapset_of(rec["target"]["traps"], weights))
        out = infer.run_method(rec, mid, budget=Budget(STEP_ITERATIONS), init=phi, target=target, ctx=ctx)
        phi = out.phi
    return {"steps": steps}


def weights_of(w0: dict[int, float], ids: list[int]) -> list[float]:
    return [w0[i] for i in ids]


def case_metrics(trace_feedback: dict) -> dict[str, float]:
    s = trace_feedback["steps"]
    return {"feedback_initial_rel_std_pct": s[0]["rel_std_pct"], "feedback_final_rel_std_pct": s[-1]["rel_std_pct"]}
