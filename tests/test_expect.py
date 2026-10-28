"""Expected ranges (core/expect.py): a baked value outside its case's range fails the bake, with its name."""
import pytest

from pipeline import registry
from pipeline.core.expect import ExpectationError, check
from pipeline.io.schema import SIRResult
from pipeline.stages import infer


def _result(peak: float, t_peak: float, attack: float) -> SIRResult:
    return SIRResult(case_id="x", t=[0.0], S=[0.0], I=[0.0], R=[0.0], peak_I=peak, t_peak=t_peak, attack_rate=attack)


def test_every_registered_case_meets_its_declared_range():
    for case in registry.list_cases():
        ranges = check(case.id, case.expect, infer.run(case.params))
        assert ranges, case.id


def test_a_value_outside_its_range_is_named():
    with pytest.raises(ExpectationError, match=r"attack_rate=0\.75 outside \[0\.9, 0\.95\]"):
        check("EX", {"attack_rate": (0.9, 0.95)}, _result(10.0, 20.0, 0.75))


def test_adversarial_a_case_without_expectations_or_with_an_unknown_metric_fails():
    with pytest.raises(ExpectationError, match="no expected range"):
        check("EX", {}, _result(1.0, 1.0, 0.1))
    with pytest.raises(ExpectationError, match="unknown expected metric 'peak'"):
        check("EX", {"peak": (0.0, 1.0)}, _result(1.0, 1.0, 0.1))
