"""The numeric expectations of a case, checked at bake time.

An expectation written only as prose can be wrong for months without anyone noticing: the template's own
epidemic case promised "an attack rate between 0.7 and 0.9" while its engine produced 0.924 (found
2026-10-04). Every case therefore states its expected range for named result metrics; the bake fails on a value
outside its range, and the manifest carries the ranges so the web can judge a live run against them too.
"""
from __future__ import annotations

from ..io.schema import SIRResult

METRICS = ("peak_I", "t_peak", "attack_rate")


class ExpectationError(ValueError):
    """A baked result fell outside the range its case declares."""


def metric_values(result: SIRResult) -> dict[str, float]:
    return {"peak_I": result.peak_I, "t_peak": result.t_peak, "attack_rate": result.attack_rate}


def check(case_id: str, expect: dict[str, tuple[float, float]], result: SIRResult) -> dict[str, list[float]]:
    """Return the ranges as written to the manifest; raise ExpectationError naming every metric out of range."""
    if not expect:
        raise ExpectationError(f"{case_id}: no expected range declared (every case states what a reader should see)")
    values = metric_values(result)
    ranges: dict[str, list[float]] = {}
    bad: list[str] = []
    for name in sorted(expect):
        if name not in values:
            raise ExpectationError(f"{case_id}: unknown expected metric {name!r} (known: {', '.join(METRICS)})")
        lo, hi = expect[name]
        if lo > hi:
            raise ExpectationError(f"{case_id}: empty range for {name}: [{lo}, {hi}]")
        ranges[name] = [float(lo), float(hi)]
        v = values[name]
        if not lo <= v <= hi:
            bad.append(f"{name}={v:.6g} outside [{lo}, {hi}]")
    if bad:
        raise ExpectationError(f"{case_id}: " + "; ".join(bad))
    return ranges
