"""Baseline of the surrogate model slot (catalog row surrogate-model): the analytic SIR peak fraction, needing no
trained bundle. From the first integral S + I - (1/R0) ln S = const with S0 = 1 and I0 near 0, the infected fraction
peaks when S = 1/R0 at ``1 - (1 + ln R0) / R0``; for R0 <= 1 there is no outbreak and the peak fraction is 0.

It answers whenever no valid released bundle exists (``stages.train.load_released`` returns None), and it is the
other side of the swap test: both predictors map r0 = beta / gamma (> 0) to a peak fraction in [0, 1]."""
from __future__ import annotations

import math
from typing import Any


def peak_frac(r0: float) -> float:
    """Peak infected fraction peak_I / N for the basic reproduction number ``r0``; 0.0 for r0 <= 1 and for a
    non-finite or non-positive r0."""
    if not math.isfinite(r0) or r0 <= 1.0:
        return 0.0
    return max(0.0, 1.0 - (1.0 + math.log(r0)) / r0)


BASIS = ["1", "r0", "ln(r0)", "1/r0"]


def is_valid_bundle(obj: Any) -> bool:
    """The rules of docs/contracts/schemas/surrogate-model.schema.json (stdlib, so the readiness check needs no
    numpy), plus finite coefficients: kind ``linear-lstsq``, the basis exactly ``BASIS``, four numbers, no other key.
    stages/train.py re-exports it."""
    if not isinstance(obj, dict) or set(obj) != {"kind", "basis", "coeffs"}:
        return False
    if obj["kind"] != "linear-lstsq" or obj["basis"] != BASIS:
        return False
    coeffs = obj["coeffs"]
    return (isinstance(coeffs, list) and len(coeffs) == len(BASIS)
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) for c in coeffs))
