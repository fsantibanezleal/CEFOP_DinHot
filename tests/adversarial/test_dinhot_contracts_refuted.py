"""Contract requirements planted by the product (docs/design/features/contracts/): each test wraps a defect around the readiness rules and runs the requirement's own gate in a child pytest (plant_run.py)."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'CT-012': ('tests/contracts/test_readiness.py::test_state_training_without_a_released_model_and_with_a_marker', [
        {"target": 'pipeline.core.readiness:_rule', "wrap": "lambda *a, **k: dict(orig(*a, **k), state='available')"},
    ]),
    'CT-013': ('tests/contracts/test_readiness.py::test_released_model_baseline_bake_and_marker_rules', [
        {"target": 'pipeline.core.readiness:_rule', "wrap": "lambda *a, **k: dict(orig(*a, **k), state='available')"},
    ]),
    'CT-031': ('tests/contracts/test_readiness.py::test_released_model_baseline_bake_and_marker_rules', [
        {"target": 'pipeline.core.readiness:_rule', "wrap": "lambda *a, **k: dict(orig(*a, **k), provenance='real')"},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('contracts'), control=True)


def test_a_baseline_that_is_not_marked_as_training_fails_the_state_gate(cases):
    """CT-012: the rules are replaced by ones that answer available for every row: the slot is no longer training and the state assertion fails"""
    cases.refuted('CT-012')


def test_a_marker_that_changes_nothing_fails_the_training_gate(cases):
    """CT-013: the rules are replaced by ones that answer available for every row: the marker no longer changes the state and the assertion fails"""
    cases.refuted('CT-013')


def test_a_baseline_bake_stamped_real_fails_the_provenance_gate(cases):
    """CT-031: the rules are replaced by ones that stamp every row real: a baseline bake is no longer told apart from a model and the provenance assertion fails"""
    cases.refuted('CT-031')
