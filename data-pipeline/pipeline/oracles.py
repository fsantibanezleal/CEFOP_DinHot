"""Oracles: independent solutions the engine and the notebooks are checked against.

An oracle shares no code with the engine's integrator (``pipeline/model/``): it solves the closed relation the model must
agree with, so a disagreement is a finding about one of the two. The notebooks import it, as they import every method
(CAOS_MANAGE ``conventions/product-notebooks.md`` section 1); none defines its own copy.

Final size of an epidemic (Kermack and McKendrick 1927; Miller 2012, https://doi.org/10.1007/s11538-012-9749-6): the
fraction ``z`` ever infected solves ``1 - z = (1 - i0) exp(-R0 z)``, which for a vanishing initial infection is
``z = 1 - exp(-R0 z)``. It does not depend on the time course, only on ``R0`` (and ``i0``).
"""
from __future__ import annotations

import math


def final_size(r0: float, i0: float = 0.0, tolerance: float = 1e-12, trace: list[float] | None = None, max_iterations: int = 100_000) -> float:
    """The fraction ever infected: the fixed point of ``z -> 1 - (1 - i0) exp(-R0 z)`` found from ``z = 1``.

    ``i0`` is the initial infected fraction (0 for the relation ``z = 1 - exp(-R0 z)``). The iteration stops when two
    consecutive values differ by less than ``tolerance``; ``trace``, when given, receives every iterate. For ``R0`` at or
    below 1 and ``i0 = 0`` the only solution is zero, which the iteration approaches.
    """
    z = 1.0
    for _ in range(max_iterations):
        z_next = 1.0 - (1.0 - i0) * math.exp(-r0 * z)
        if trace is not None:
            trace.append(z_next)
        if abs(z_next - z) < tolerance:
            return z_next
        z = z_next
    return z
