"""CONTRACT 1, ingestion (raw -> pipeline). The *bring-your-own-data* gate.

Declares the required schema (columns, units, ranges) of an input parameter table and an EXPLICIT outlier policy.
A dataset is ACCEPTED iff it passes; bad rows are REJECTED with a reason (never silently coerced); plausible-but-
suspicious rows are FLAGGED (accepted, but the manifest records the flag). This is what lets the product be applied
to NEW data instead of only replaying baked cases. Documented in data/README.md.

EXAMPLE schema = an SIR parameterization. Replace the columns/ranges/policy with your product's real data contract
(e.g. a vibration record: fs, channel, load, window length, dropouts; or a PSD CSV: sieve apertures, %-passing).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .schema import SIRParams

REQUIRED_COLUMNS: tuple[str, ...] = ("case_id", "beta", "gamma", "N", "I0")

# name -> (min, max, unit). Physically/operationally plausible ranges; outside => REJECT.
RANGES: dict[str, tuple[float, float, str]] = {
    "beta": (1e-6, 5.0, "1/day (effective contact rate)"),
    "gamma": (1e-6, 2.0, "1/day (recovery rate)"),
    "N": (1.0, 1e9, "individuals (population)"),
    "I0": (0.0, 1e9, "individuals (initial infected)"),
}
R0_FLAG_MAX = 20.0  # R0 above this is implausible for the example domain => FLAG (not reject)
DEFAULT_DAYS = 160


@dataclass
class ContractReport:
    accepted: list[SIRParams]
    rejected: list[dict[str, Any]]
    flagged: list[dict[str, Any]]

    @property
    def ok(self) -> bool:
        return len(self.accepted) > 0

    def summary(self) -> str:
        return f"{len(self.accepted)} accepted, {len(self.rejected)} rejected, {len(self.flagged)} flagged"


def validate_rows(raw_rows: list[dict[str, Any]]) -> ContractReport:
    """Apply CONTRACT 1 to raw rows (e.g. from a CSV). Pure; deterministic; no I/O."""
    accepted: list[SIRParams] = []
    rejected: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []

    for i, row in enumerate(raw_rows):
        cid = str(row.get("case_id", f"row{i}"))
        missing = [c for c in REQUIRED_COLUMNS if c not in row or row[c] in (None, "")]
        if missing:
            rejected.append({"row": i, "case_id": cid, "reason": f"missing/empty columns: {missing}"})
            continue
        try:
            vals = {k: float(row[k]) for k in ("beta", "gamma", "N", "I0")}
        except (TypeError, ValueError):
            rejected.append({"row": i, "case_id": cid, "reason": "non-numeric value in beta/gamma/N/I0"})
            continue
        if any(math.isnan(v) or math.isinf(v) for v in vals.values()):
            rejected.append({"row": i, "case_id": cid, "reason": "NaN/Inf value"})
            continue
        bad: list[str] = []
        for name, (lo, hi, _unit) in RANGES.items():
            if not (lo <= vals[name] <= hi):
                bad.append(f"{name}={vals[name]:g} out of [{lo:g},{hi:g}]")
        if vals["I0"] > vals["N"]:
            bad.append(f"I0={vals['I0']:g} > N={vals['N']:g}")
        if bad:
            rejected.append({"row": i, "case_id": cid, "reason": "; ".join(bad)})
            continue
        r0 = vals["beta"] / vals["gamma"] if vals["gamma"] > 0 else math.inf
        if r0 > R0_FLAG_MAX:
            flagged.append({"case_id": cid, "flag": f"R0={r0:.1f} > {R0_FLAG_MAX:g} (implausibly high)"})
        try:
            days = int(float(row.get("days") or DEFAULT_DAYS))
        except (TypeError, ValueError):
            days = DEFAULT_DAYS
        accepted.append(SIRParams(case_id=cid, beta=vals["beta"], gamma=vals["gamma"],
                                  N=vals["N"], I0=vals["I0"], days=max(1, days)))
    return ContractReport(accepted=accepted, rejected=rejected, flagged=flagged)
