"""The numeric expectations of a case, checked at bake time.

An expectation written only as prose can be wrong for months without anyone noticing: the template's own epidemic case
promised "an attack rate between 0.7 and 0.9" while its engine produced 0.924 (found 2026-10-04). Every case therefore
states its expected range for named result metrics; the bake fails on a value outside its range, naming the case, the
method and the metric, and the manifest carries the ranges so the web can judge a live run against them too.

A key of ``expect`` (``[low, high]`` as the params-record schema says) is one of:

- ``<metric>``: a method metric of the case's reference method (``efficiency``, ``uniformity``, ``rel_std_pct``,
  ``zero_order``, ``ghost``, ``iterations``), or a case metric (below);
- ``<method>.<metric>``: a method metric of that method (for example ``M04.uniformity``), which must be among the case's
  methods.

Case metrics are measured by the bake's drivers: ``feedback_initial_rel_std_pct`` and ``feedback_final_rel_std_pct`` (the
camera loop, percent), ``fc_ratio`` (fitted over input corner frequency of the bead, or fitted over expected trap
frequency ratio of the atom), ``boltzmann_tv`` (total variation between the position histogram and the Boltzmann law),
``min_transient`` (lowest intensity of a moving trap relative to the mean) and ``final_filling`` (the last filling).

Stdlib only: contract 1 imports ``METRICS`` and ``parse_key``.
"""
from __future__ import annotations

import re

METHOD_METRICS = ("efficiency", "uniformity", "rel_std_pct", "zero_order", "ghost", "iterations")
CASE_METRICS = ("feedback_initial_rel_std_pct", "feedback_final_rel_std_pct", "fc_ratio", "boltzmann_tv",
                "min_transient", "final_filling")
METRICS = METHOD_METRICS + CASE_METRICS
_KEY = re.compile(r"^(?:(M[0-9]{2}|B[0-9])\.)?([a-z_]+)$")


class ExpectationError(ValueError):
    """A baked result fell outside the range its case declares, or the declaration is not usable."""


def parse_key(key: str) -> tuple[str | None, str]:
    """``(method or None, metric)`` of an expectation key; ``ExpectationError`` for a key that is neither form."""
    m = _KEY.match(key)
    if not m or m.group(2) not in METRICS:
        raise ExpectationError(f"unknown expected metric {key!r} (known: {', '.join(METRICS)}; or <method>.<metric>)")
    if m.group(1) is not None and m.group(2) in CASE_METRICS:
        raise ExpectationError(f"{key!r}: a case metric has no method prefix")
    return m.group(1), m.group(2)


def check(
    case_id: str,
    expect: dict[str, tuple[float, float]] | dict[str, list[float]],
    method_metrics: dict[str, dict[str, float]],
    reference: str,
    case_metrics: dict[str, float] | None = None,
) -> dict[str, list[float]]:
    """Return the ranges as written to the manifest; raise ``ExpectationError`` naming every value out of range.

    ``method_metrics`` is ``{method: {metric: value}}`` for the methods that ran; ``reference`` is the case's reference
    method; ``case_metrics`` holds the drivers' case metrics (a declared case metric the bake did not measure fails).
    """
    if not expect:
        raise ExpectationError(f"{case_id}: no expected range declared (every case states what a reader should see)")
    case_metrics = case_metrics or {}
    ranges: dict[str, list[float]] = {}
    bad: list[str] = []
    for key in sorted(expect):
        method, metric = parse_key(key)
        lo, hi = expect[key]
        if lo > hi:
            raise ExpectationError(f"{case_id}: empty range for {key}: [{lo}, {hi}]")
        ranges[key] = [float(lo), float(hi)]
        if metric in CASE_METRICS:
            who, value = "case", case_metrics.get(metric)
            if value is None:
                bad.append(f"{key}: the bake did not measure this case metric")
                continue
        else:
            who = method or reference
            row = method_metrics.get(who)
            if row is None:
                bad.append(f"method {who} {metric}: the method did not run")
                continue
            value = row[metric]
        if not lo <= value <= hi:
            bad.append(f"method {who} {metric}={value:.6g} outside [{lo}, {hi}]" if who != "case"
                       else f"case metric {metric}={value:.6g} outside [{lo}, {hi}]")
    if bad:
        raise ExpectationError(f"{case_id}: " + "; ".join(bad))
    return ranges
