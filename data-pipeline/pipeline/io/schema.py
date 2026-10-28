"""Typed objects passed between pipeline stages, the inter-stage contract. Plain dataclasses."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SIRParams:
    """One validated operating point (EXAMPLE domain: an SIR epidemic)."""
    case_id: str
    beta: float        # 1/day, effective contact rate
    gamma: float       # 1/day, recovery rate
    N: float           # population
    I0: float          # initial infected
    days: int = 160    # horizon


@dataclass(frozen=True)
class FeatureRow:
    """Derived features for the surrogate (feature_extraction stage)."""
    case_id: str
    r0: float          # beta / gamma (basic reproduction number)
    beta: float
    gamma: float
    n_scaled: float    # log10(N)
    i0_frac: float     # I0 / N


@dataclass(frozen=True)
class SIRResult:
    """The engine output for one case (infer stage), the raw, undecimated trajectory + scalars."""
    case_id: str
    t: list[float]
    S: list[float]
    I: list[float]
    R: list[float]
    peak_I: float
    t_peak: float
    attack_rate: float
