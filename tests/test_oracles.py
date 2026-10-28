"""The final-size oracle (data-pipeline/pipeline/oracles.py): the solver of z = 1 - exp(-R0 z) that the notebooks import.

It is an oracle by design, so it shares no code with the engine's integrator (pipeline/model/): the tests pin it to the
relation itself, solved here by bisection, and read its source for any import of the engine."""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

from pipeline import oracles  # noqa: E402


def bisect(f, lo: float, hi: float) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


@pytest.mark.parametrize("r0", [1.2, 2.0, 2.75, 6.0])
def test_the_solution_satisfies_the_final_size_relation(r0: float) -> None:
    z = oracles.final_size(r0)
    assert abs(z - (1.0 - math.exp(-r0 * z))) < 1e-10
    assert abs(z - bisect(lambda x: x - (1.0 - math.exp(-r0 * x)), 1e-9, 1.0)) < 1e-9


def test_the_known_values() -> None:
    assert round(oracles.final_size(2.75), 6) == 0.920437
    assert round(oracles.final_size(6.0), 6) == 0.997484


@pytest.mark.parametrize("r0", [0.0, 0.5, 0.72])
def test_no_epidemic_below_the_threshold(r0: float) -> None:
    assert oracles.final_size(r0) < 1e-6


@pytest.mark.parametrize("r0,i0", [(2.75, 1e-3), (6.0, 5e-4), (1.2, 1e-3)])
def test_the_relation_with_an_initial_infection(r0: float, i0: float) -> None:
    z = oracles.final_size(r0, i0, tolerance=1e-13)
    assert abs((1.0 - z) - (1.0 - i0) * math.exp(-r0 * z)) < 1e-10


def test_the_trace_records_every_iteration() -> None:
    trace: list[float] = []
    z = oracles.final_size(2.75, trace=trace)
    assert len(trace) == 18 and trace[-1] == z and trace[0] == pytest.approx(1.0 - math.exp(-2.75))


def test_the_oracle_shares_no_code_with_the_engine() -> None:
    tree = ast.parse((ROOT / "data-pipeline" / "pipeline" / "oracles.py").read_text(encoding="utf-8"))
    imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("model" in m or m.startswith("pipeline") for m in imported), imported
