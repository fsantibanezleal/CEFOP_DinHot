"""Stage 5, evaluate (the TEST stage): held-out surrogate-vs-engine error. Leakage-safe, the holdout params are
a disjoint synthetic draw, never the training params. Returns R2 + RMSE on the peak-infected fraction (RMSE, not
MAPE: MAPE blows up on the near-zero peak fractions of sub-critical cases and would be misleading)."""
from __future__ import annotations

import numpy as np

from ..io.schema import SIRParams
from ..model.baseline import peak_frac
from ..model.sir import simulate
from .train import predict


def models_used(model: dict | None) -> dict[str, str]:
    """Which model answered, per model slot of the catalog (here only ``surrogate-model``): ``real`` when the released
    bundle did, ``baseline`` when none was valid. The manifest records it beside the metrics (contract case-manifest)."""
    return {"surrogate-model": "baseline" if model is None else "real"}


def run(model: dict | None, holdout_params: list[SIRParams]) -> dict:
    """``model`` None means no released bundle: the analytic baseline answers (model/baseline.py)."""
    preds, truths = [], []
    for p in holdout_params:
        r0 = (p.beta / p.gamma) if p.gamma > 0 else 1e-6
        preds.append(peak_frac(r0) if model is None else predict(model, r0))
        truths.append((simulate(p).peak_I / p.N) if p.N > 0 else 0.0)
    preds, truths = np.array(preds), np.array(truths)
    ss_res = float(np.sum((preds - truths) ** 2))
    ss_tot = float(np.sum((truths - truths.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rmse = float(np.sqrt(np.mean((preds - truths) ** 2)))
    return {
        "surrogate_peakfrac_r2": round(r2, 4),
        "surrogate_peakfrac_rmse": round(rmse, 5),
        "n_holdout": len(holdout_params),
    }
