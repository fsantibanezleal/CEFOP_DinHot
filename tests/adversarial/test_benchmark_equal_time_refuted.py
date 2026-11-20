"""Benchmark requirements BM-008 to BM-016 (docs/design/features/benchmark/): each planted row wraps a defect around the engine, the
protocol or the report's extract script and runs the requirement's own gate in a child pytest, which must then fail (and pass
without the plant)."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

H = 'tests/methods/beyond/test_equal_time.py'
B = 'tests/bake/test_benchmark_equal_time.py'
W = 'tests/test_benchmark_win_rule.py'
DROP = 'lambda *a, **k: orig(*a, **dict(k, deadline=None))'

TABLE = {
    'BM-008': (H + '::test_weighted_gs_with_an_expired_deadline_returns_one_iteration_and_never_raises', [
        {"target": 'pipeline.model.holo.methods.optim._gs_family:weighted_gs', "wrap": DROP},
    ]),
    'BM-009': (H + '::test_b1_deadline_inside_the_warm_start_returns_the_warm_iterate', [
        {"target": 'pipeline.model.holo.methods.beyond.b1_device_wgs:weighted_gs', "wrap": DROP},
    ]),
    'BM-010': (H + '::test_weighted_gs_evaluations_equal_the_independent_count', [
        {"target": 'pipeline.model.holo.core.forward:count_evaluation', "wrap": 'lambda n=1: None'},
    ]),
    'BM-011': (B + '::test_b2_is_not_in_the_static_ladder_and_its_docstring_says_why', [
        {"target": 'pipeline.benchmark.protocol:LADDER', "wrap": "orig + ['B2']"},
    ]),
    'BM-012': (B + '::test_seed_rule_time_and_converged_rows_run_five_seeds_iteration_rows_keep_the_group_budget', [
        {"target": 'pipeline.benchmark.protocol:MIN_BOUNDED_SEEDS', "wrap": '2'},
    ]),
    'BM-013': (B + '::test_g6_is_two_geometries_with_their_own_targets_and_every_seed_runs_both', [
        {"target": 'pipeline.benchmark.geometries:record', "wrap": "lambda g, *a, **k: orig('G6a' if g == 'G6b' else g, *a, **k)"},
    ]),
    'BM-014': (B + '::test_every_row_records_evaluations_and_the_document_validates', [
        {"target": 'pipeline.benchmark.protocol:_row', "wrap": "lambda *a, **k: {x: y for x, y in orig(*a, **k).items() if x != 'evaluations'}"},
    ], True),
    'BM-015': (W + '::test_must_refute_no_win_with_four_seeds_overlap_or_a_0009_difference', [
        {"target": 'extract_methods:WIN_MIN_SEEDS', "wrap": '1'},
        {"target": 'extract_methods:WIN_MIN_DIFF_PCT', "wrap": '0.0'},
    ]),
    'BM-016': (W + '::test_a_1x_file_is_refused_naming_the_contract_version', [
        {"target": 'extract_methods:require_contract', "wrap": 'lambda *a, **k: None'},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('benchmark-equal-time'), control=True)


def test_adversarial_a_deadline_dropped_from_weighted_gs_runs_all_its_iterations(cases):
    """BM-008: the deadline is dropped on its way into weighted_gs: a deadline already past still runs every requested iteration and the assertion fails"""
    cases.refuted('BM-008')


def test_adversarial_a_warm_start_without_the_deadline_overruns_a_time_row(cases):
    """BM-009: the warm start of B1 is given no deadline: a deadline inside the warm start still runs the 40 warm iterations and the assertion fails"""
    cases.refuted('BM-009')


def test_adversarial_a_counter_that_counts_nothing_disagrees_with_the_independent_count(cases):
    """BM-010: the evaluation counter is replaced by one that counts nothing: it no longer equals the independent count of the transforms and the assertion fails"""
    cases.refuted('BM-010')


def test_adversarial_a_ladder_that_holds_b2_fails_the_static_gate(cases):
    """BM-011: B2 is appended to the static ladder: the gate that searches the ladder for it fails"""
    cases.refuted('BM-011')


def test_adversarial_a_seed_floor_of_two_for_time_rows_fails_the_seed_gate(cases):
    """BM-012: the floor of bounded seeds is lowered to two: the gate that reads the floor and the rows fails"""
    cases.refuted('BM-012')


def test_adversarial_a_g6_that_pools_the_two_targets_fails_the_geometry_gate(cases):
    """BM-013: the disordered geometry is drawn as the lattice: the two targets are no longer different and the assertion fails"""
    cases.refuted('BM-013')


def test_adversarial_a_row_without_evaluations_fails_the_contract_gate(cases):
    """BM-014: every row is written without evaluations: the schema of contract 2.0.0 refuses the document and the assertion fails"""
    cases.refuted('BM-014')


def test_adversarial_a_win_rule_without_its_floors_grants_a_win_it_should_not(cases):
    """BM-015: the seed floor is lowered to 1 and the point floor to 0: the cells with 4 seeds, with a 0.009 point difference and with touching ranges become wins and the assertion fails"""
    cases.refuted('BM-015')


def test_adversarial_a_reader_that_accepts_a_1x_file_fails_the_refusal_gate(cases):
    """BM-016: the contract check of the extract scripts is replaced by one that accepts everything: the 1.x document is no longer refused and the assertion fails"""
    cases.refuted('BM-016')
