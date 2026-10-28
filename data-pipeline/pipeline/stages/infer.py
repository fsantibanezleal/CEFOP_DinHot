"""Stage 4, infer: run the (research-chosen) engine for a case's params. EXAMPLE = the SIR simulate()."""
from __future__ import annotations

from ..io.schema import SIRParams, SIRResult
from ..model.sir import simulate


def run(params: SIRParams) -> SIRResult:
    return simulate(params)
