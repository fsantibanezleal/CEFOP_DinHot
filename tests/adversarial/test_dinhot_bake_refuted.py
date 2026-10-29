"""Bake requirements BK-001 to BK-017 (docs/design/features/bake/): each planted row wraps a defect around the product's code and runs the requirement's own gate in a child pytest (plant_run.py); the others name a test that plants the defect in its input."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'BK-001': ('tests/test_contract.py::test_adversarial_bad_values_rejected_not_coerced', [
        {"target": 'pipeline.io.contract:validate_records', "wrap": 'lambda raw, *a, **k: orig([], *a, **k)'},
    ]),
    'BK-002': ('tests/test_contract.py::test_missing_field_and_extra_field_rejected', [
        {"target": 'pipeline.io.contract:validate_records', "wrap": 'lambda raw, *a, **k: orig([], *a, **k)'},
    ]),
    'BK-003': ('tests/test_contract.py::test_out_of_field_names_the_bound', [
        {"target": 'pipeline.io.contract:_cross_field', "wrap": 'lambda *a, **k: None'},
    ]),
    'BK-004': ('tests/bake/test_c13.py::test_the_registry_lists_c13_next_to_c03', [
        {"target": 'pipeline.cases.library:CASES', "wrap": 'orig[:-1]'},
    ]),
    'BK-005': ('tests/bake/test_c13.py::test_c13_is_819_traps_on_bins_at_least_five_bins_apart', [
        {"target": 'pipeline.cases.library:CASES', "wrap": "[dataclasses.replace(c, record=dict(c.record, target=dict(c.record['target'], traps=c.record['target']['traps'][:-1]))) if c.id.startswith('C13') else c for c in orig]"},
    ]),
    'BK-017': ('tests/bake/test_c14.py::test_c14_is_the_geometry_of_the_released_model_card', [
        {"target": 'pipeline.cases.library:CASES', "wrap": "[dataclasses.replace(c, record=dict(c.record, setup=dict(c.record['setup'], pad=2))) if c.id.startswith('C14') else c for c in orig]"},
    ]),
    'BK-006': ('tests/test_expect.py::test_a_value_outside_its_range_is_named', [
        {"target": 'pipeline.core.expect:check', "wrap": 'lambda *a, **k: {}'},
    ]),
    'BK-007': ('tests/methods/integration/test_i1_integration.py::test_range_rule_is_the_wider_of_ten_percent_and_the_seed_spread', [
        {"target": 'pipeline.ranges:propose', "wrap": 'lambda *a, **k: [0.0, 0.0]'},
    ]),
    'BK-008': ('tests/bake/test_gates.py::test_lane_gate_decisions_and_budgets', [
        {"target": 'pipeline.core.gate:classify_lane', "wrap": "lambda **k: dict(orig(**k), lane='live', reasons=[])"},
    ]),
    'BK-009': ('tests/bake/test_gates.py::test_adversarial_domain_and_unit_violations', [
        {"target": 'pipeline.core.units:check_case', "wrap": 'lambda *a, **k: []'},
    ]),
    'BK-010': ('tests/bake/test_gates.py::test_a_trace_that_fits_is_not_squeezed_and_one_that_does_not_is_squeezed_or_refused', [
        {"target": 'pipeline.core.trace:fit', "wrap": 'lambda *a, **k: (lambda r: (r[0], r[1] * 100, 0))(orig(*a, **k))'},
    ]),
    'BK-013': ('tests/test_pipeline_smoke.py::test_a_refused_case_is_not_computed', [
        {"target": 'pipeline.pipeline:precompute', "wrap": 'lambda *a, **k: None'},
    ]),
    'BK-014': ('tests/methods/integration/test_i1_integration.py::test_the_atom_stays_in_the_map_and_oscillates_at_the_predicted_frequency', [
        {"target": 'pipeline.stages.dynamics:substeps', "wrap": 'lambda *a, **k: 1'},
    ]),
    'BK-015': ('tests/methods/integration/test_i1_integration.py::test_auto_form_is_fft_on_bins_and_point_off_bins', [
        {"target": 'pipeline.model.holo.methods.baseline.m04_gs:run', "wrap": "lambda *a, **k: orig(*a, **dict(k, form='point'))"},
    ]),
    'BK-016': ('tests/methods/integration/test_i1_integration.py::test_signal_error_agrees_with_the_methods_own_history', [
        {"target": 'pipeline.core.score:signal_error_pct', "wrap": 'lambda *a, **k: orig(*a, **k) * 0.5'},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('bake'), control=True)


def test_a_validator_that_coerces_bad_values_fails_the_ingestion_gate(cases):
    """BK-001: the validator is replaced by one that checks nothing (it reports every record accepted): the rejection assertions fail"""
    cases.refuted('BK-001')


def test_a_validator_that_accepts_a_missing_or_extra_field_fails_the_schema_gate(cases):
    """BK-002: the validator is replaced by one that validates no record: the missing-field and extra-field assertions fail"""
    cases.refuted('BK-002')


def test_a_validator_without_the_cross_field_rules_fails_the_field_gate(cases):
    """BK-003: the cross-field rules are replaced by ones that find nothing: the out-of-field record is accepted and the assertion fails"""
    cases.refuted('BK-003')


def test_a_case_library_without_c13_fails_the_registry_gate(cases):
    """BK-004: the registry is replaced by one that drops its last case: the registry assertion fails"""
    cases.refuted('BK-004')


def test_a_disordered_set_of_the_wrong_size_fails_the_c13_gate(cases):
    """BK-005: the registry's C13 record loses one trap: the count and spacing assertions fail"""
    cases.refuted('BK-005')


def test_an_expectation_check_that_accepts_everything_fails_the_range_gate(cases):
    """BK-006: the expectation check is replaced by one that accepts every value: the out-of-range assertion fails"""
    cases.refuted('BK-006')


def test_a_range_rule_that_ignores_the_spread_fails_the_measurement_gate(cases):
    """BK-007: the range rule is replaced by one that returns a zero-width range: the rule assertion fails"""
    cases.refuted('BK-007')


def test_a_lane_gate_that_always_says_live_fails_the_lane_gate(cases):
    """BK-008: the classifier is replaced by one that answers live for any case: the slow and the oversized cases are no longer sent to precompute and the assertion fails"""
    cases.refuted('BK-008')


def test_a_units_gate_that_finds_nothing_fails_the_units_gate(cases):
    """BK-009: the units check is replaced by one that finds no problem: every planted unit violation goes unseen and the assertions fail"""
    cases.refuted('BK-009')


def test_a_trace_fitter_that_never_squeezes_fails_the_trace_budget_gate(cases):
    """BK-010: the fitter is replaced by one that reports the first step and a size over the budget as fitting: the budget assertion fails"""
    cases.refuted('BK-010')


def test_a_pipeline_that_computes_a_refused_case_fails_the_refusal_gate(cases):
    """BK-013: the precompute entry point is replaced by one that returns without raising: a refused case is no longer refused and the assertion fails"""
    cases.refuted('BK-013')


def test_a_driver_with_a_single_substep_fails_the_atom_oracle_gate(cases):
    """BK-014: the number of substeps is forced to 1 (omega dt above 2, velocity Verlet unstable): the atom leaves the map and the oracle assertions fail"""
    cases.refuted('BK-014')


def test_a_form_selector_that_never_picks_the_fft_form_fails_the_form_gate(cases):
    """BK-015: the form of every method is forced to the point-trap form: the on-bin assertion fails"""
    cases.refuted('BK-015')


def test_a_score_that_ignores_the_shape_fails_the_signal_region_gate(cases):
    """BK-016: the signal error is scaled by one half: the agreement with the method's own history fails"""
    cases.refuted('BK-016')


def test_a_c14_off_the_model_geometry_fails_the_c14_gate(cases):
    """BK-017: the registry's C14 record is given padding 2: the card-geometry assertion fails"""
    cases.refuted('BK-017')
