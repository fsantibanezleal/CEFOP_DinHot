"""Stage 2, feature_extraction: validated params -> feature rows for the surrogate (deterministic)."""
from __future__ import annotations

import math

from ..io.schema import FeatureRow, SIRParams


def run(params_list: list[SIRParams]) -> list[FeatureRow]:
    rows: list[FeatureRow] = []
    for p in params_list:
        r0 = (p.beta / p.gamma) if p.gamma > 0 else math.inf
        rows.append(FeatureRow(
            case_id=p.case_id,
            r0=r0,
            beta=p.beta,
            gamma=p.gamma,
            n_scaled=math.log10(max(1.0, p.N)),
            i0_frac=(p.I0 / p.N) if p.N > 0 else 0.0,
        ))
    return rows
