"""Expected ranges (core/expect.py): a baked value outside its range fails the bake, naming the case, the method and the metric."""
import pytest

from pipeline.core.expect import ExpectationError, check, parse_key

ROWS = {"M04": {"efficiency": 0.9, "uniformity": 0.6, "rel_std_pct": 20.0, "zero_order": 0.01, "ghost": 0.05, "iterations": 30.0},
        "M06": {"efficiency": 0.92, "uniformity": 0.99, "rel_std_pct": 1.0, "zero_order": 0.01, "ghost": 0.05, "iterations": 30.0}}


def test_in_range_returns_the_ranges_for_the_manifest():
    out = check("C", {"efficiency": (0.8, 1.0), "M04.uniformity": (0.5, 0.7), "feedback_final_rel_std_pct": (0, 3)}, ROWS, "M06",
                {"feedback_final_rel_std_pct": 1.4})
    assert out == {"efficiency": [0.8, 1.0], "M04.uniformity": [0.5, 0.7], "feedback_final_rel_std_pct": [0.0, 3.0]}


def test_a_value_outside_its_range_is_named():
    with pytest.raises(ExpectationError, match=r"C02: method M04 uniformity=0\.6 outside \[0\.9, 1\.0\]"):
        check("C02", {"M04.uniformity": (0.9, 1.0)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match=r"method M06 efficiency=0\.92 outside \[0\.95, 1\.0\]"):
        check("C02", {"efficiency": (0.95, 1.0)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match=r"case metric fc_ratio=1\.5 outside"):
        check("C01", {"fc_ratio": (0.8, 1.2)}, ROWS, "M06", {"fc_ratio": 1.5})


def test_every_violation_is_listed():
    with pytest.raises(ExpectationError) as e:
        check("C", {"efficiency": (0.0, 0.1), "rel_std_pct": (50, 60)}, ROWS, "M06")
    assert "efficiency" in str(e.value) and "rel_std_pct" in str(e.value)


def test_adversarial_missing_declarations_unknown_keys_and_unmeasured_metrics_fail():
    with pytest.raises(ExpectationError, match="no expected range"):
        check("C", {}, ROWS, "M06")
    with pytest.raises(ExpectationError, match="unknown expected metric 'peak'"):
        check("C", {"peak": (0, 1)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match="empty range"):
        check("C", {"efficiency": (1.0, 0.5)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match="did not measure"):
        check("C", {"fc_ratio": (0, 2)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match="method M12 efficiency: the method did not run"):
        check("C", {"M12.efficiency": (0, 1)}, ROWS, "M06")
    with pytest.raises(ExpectationError, match="no method prefix"):
        parse_key("M04.fc_ratio")
