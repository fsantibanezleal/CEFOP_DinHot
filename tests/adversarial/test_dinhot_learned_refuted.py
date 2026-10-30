"""Learned-model requirements LN-001 to LN-007 (docs/design/features/learned/): each test plants the defect the requirement forbids in the product's code and runs the requirement's own gate in a child pytest (plant_run.py)."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'LN-001': ('tests/learned/test_m17_cgh_net.py::test_the_baseline_answers_while_unreleased', [
        {"target": 'pipeline.model.holo.methods.learned.m17_cgh_net:run', "wrap": "lambda *a, **k: (lambda r: (r.meta.update(provenance='real'), r)[1])(orig(*a, **k))"},
    ]),
    'LN-002': ('tests/learned/test_m17_cgh_net.py::test_geometry_and_target_errors_name_the_requirement', [
        {"target": 'pipeline.model.holo.methods.learned.m17_cgh_net:run', "wrap": "lambda *a, **k: (_ for _ in ()).throw(ValueError('refused'))"},
    ]),
    'LN-003': ('tests/learned/test_m17_cgh_net.py::test_planes_from_traps_renders_three_unit_energy_planes', [
        {"target": 'pipeline.model.holo.methods.learned.m17_cgh_net:planes_from_traps', "wrap": 'lambda *a, **k: orig(*a, **k) * 1.1'},
    ]),
    'LN-004': ('tests/learned/test_b3_warm_start.py::test_the_module_answers_with_the_random_start_while_unreleased', [
        {"target": 'pipeline.model.holo.methods.learned.b3_warm_start:run', "wrap": "lambda *a, **k: (lambda r: (r.meta.update(provenance='real'), r)[1])(orig(*a, **k))"},
    ]),
    'LN-005': ('tests/learned/test_b3_warm_start.py::test_measured_negative_the_two_times_criterion_is_not_met', [
        {"target": 'json:loads', "wrap": "lambda s, *a, **k: (lambda d: (d['metrics']['iterations_to_1pct']['model'].update(median=d['metrics']['iterations_to_1pct']['random']['median'] / 2.0) or d) if isinstance(d, dict) and 'control_without_the_network' in d else d)(orig(s, *a, **k))"},
    ]),
    'LN-006': ('tests/learned/test_m17_cgh_net.py::test_committed_metrics_meet_the_criterion', [
        {"target": 'json:loads', "wrap": "lambda s, *a, **k: (lambda d: (d['slots']['cgh-net']['accuracy_vs_gs'].update(median=0.9) or d) if isinstance(d, dict) and 'slots' in d and 'cgh-net' in d['slots'] else d)(orig(s, *a, **k))"},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('learned'), control=True)


def test_a_baseline_answer_labelled_real_fails_the_provenance_gate(cases):
    """LN-001: the answer of M17 is relabelled `real`: the provenance assertion fails"""
    cases.refuted('LN-001')


def test_an_error_that_does_not_name_the_requirement_fails_the_geometry_gate(cases):
    """LN-002: M17 raises a `ValueError` that names nothing: the test that matches the requirement in the message fails"""
    cases.refuted('LN-002')


def test_planes_that_lose_their_unit_energy_fail_the_encoding_gate(cases):
    """LN-003: the rendered planes are scaled by 1.1: the unit-energy assertion fails"""
    cases.refuted('LN-003')


def test_a_random_start_labelled_real_fails_the_b3_provenance_gate(cases):
    """LN-004: the answer of B3 is relabelled `real`: the provenance assertion fails"""
    cases.refuted('LN-004')


def test_a_recorded_ratio_that_reaches_two_fails_the_measured_negative_gate(cases):
    """LN-005: the recorded iteration medians are read back with the network start twice as fast (a ratio of 2 or more): the measured-negative assertions fail"""
    cases.refuted('LN-005')


def test_a_committed_accuracy_below_one_fails_the_release_gate(cases):
    """LN-006: the committed metrics are read back with a median ratio of 0.9: the release assertion fails"""
    cases.refuted('LN-006')
