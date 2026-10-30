"""Typed objects passed between pipeline stages, the inter-stage contract. Plain dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MethodOutcome:
    """One method run on one case: the final phase, the trace-form history, the independent score and the timing.

    ``score`` is ``core.score`` output (final metrics, per-trap intensities, the focal field). ``seconds`` is the wall
    clock of the run and never reaches a manifest (ADR-0054); it feeds the lane gate and the benchmark.
    """

    method: str
    spec_lane: str
    phi: np.ndarray
    history: list
    score: dict
    iterations: int
    converged: bool
    seconds: float
    meta: dict = field(default_factory=dict)


@dataclass
class MethodFailure:
    """A method that raised on a case (it is recorded in the manifest flags; the bake fails unless the case drops it)."""

    method: str
    error: str
