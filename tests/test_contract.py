"""CONTRACT 1 (ingestion) tests: good data validates; bad data is rejected with a reason; outliers are flagged."""
from pipeline.io.contract import validate_rows


def test_good_rows_accepted():
    rep = validate_rows([{"case_id": "a", "beta": "0.5", "gamma": "0.2", "N": "1000", "I0": "10"}])
    assert rep.ok and len(rep.accepted) == 1 and not rep.rejected


def test_adversarial_bad_rows_rejected_not_coerced():
    rows = [
        {"case_id": "nan", "beta": "nan", "gamma": "0.2", "N": "1000", "I0": "10"},      # NaN
        {"case_id": "neg", "beta": "-1", "gamma": "0.2", "N": "1000", "I0": "10"},        # out of range
        {"case_id": "i0gtN", "beta": "0.5", "gamma": "0.2", "N": "100", "I0": "500"},     # I0 > N
        {"case_id": "missing", "beta": "0.5", "gamma": "0.2", "N": "1000"},               # missing I0
        {"case_id": "text", "beta": "fast", "gamma": "0.2", "N": "1000", "I0": "10"},     # non-numeric
    ]
    rep = validate_rows(rows)
    assert len(rep.accepted) == 0
    assert len(rep.rejected) == len(rows)
    assert all("reason" in r for r in rep.rejected)


def test_outlier_flagged_but_accepted():
    rep = validate_rows([{"case_id": "hot", "beta": "4.5", "gamma": "0.2", "N": "1000", "I0": "1"}])  # R0=22.5>20
    assert rep.ok and rep.flagged and "R0" in rep.flagged[0]["flag"]
