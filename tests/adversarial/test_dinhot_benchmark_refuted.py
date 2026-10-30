"""Benchmark requirements BM-001 to BM-007 (docs/design/features/benchmark/): each planted row wraps a defect around the protocol and runs the requirement's own gate in a child pytest of its own (the benchmark fixture is built under the plant)."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'BM-001': ('tests/bake/test_benchmark.py::test_every_budget_kind_is_reported_per_group', [
        {"target": 'pipeline.benchmark.protocol:_row', "wrap": 'lambda *a, **k: dict(orig(*a, **k), n_seeds=1)'},
    ], True),
    'BM-002': ('tests/bake/test_benchmark.py::test_cells_that_cannot_run_are_listed_with_a_reason_and_absent_from_rows', [
        {"target": 'pipeline.benchmark.protocol:device_skip_reason', "wrap": 'lambda *a, **k: None'},
    ], True),
    'BM-004': ('tests/bake/test_benchmark.py::test_tuning_uses_the_same_number_of_runs_for_every_method', [
        {"target": 'pipeline.benchmark.protocol:tuning_grid', "wrap": 'lambda mid, *a, **k: (lambda g: g[:2] if g else g)(orig(mid, *a, **k))'},
    ], True),
    'BM-005': ('tests/bake/test_benchmark.py::test_resume_skips_finished_groups', [
        {"target": 'pipeline.benchmark.protocol:_load_done', "wrap": 'lambda *a, **k: ([], [])'},
    ], True),
    'BM-006': ('tests/bake/test_benchmark.py::test_results_validate_and_are_in_units', [
        {"target": 'pipeline.benchmark.protocol:_stat', "wrap": 'lambda values, *a, **k: dict(orig(values, *a, **k), median=1.5)'},
    ], True),
    'BM-007': ('tests/bake/test_benchmark.py::test_pool_workers_give_the_same_rows', [
        {"target": 'pipeline.benchmark.protocol:run_group', "wrap": "lambda task: (lambda g: dict(g, rows=[dict(r, efficiency=dict(r['efficiency'], median=r['efficiency']['median'] * 0.9)) for r in g['rows']]))(orig(task))"},
    ], True),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('benchmark'), control=True)


def test_a_benchmark_that_drops_a_seed_fails_the_budget_gate(cases):
    """BM-001: each row is written with one seed fewer than the run's: the seed-count assertion fails"""
    cases.refuted('BM-001')


def test_a_protocol_that_skips_nothing_fails_the_skipped_cells_gate(cases):
    """BM-002: the device skip rule is replaced by one that skips nothing: the multi-plane device cell is no longer listed and the assertions fail"""
    cases.refuted('BM-002')


def test_a_tuning_that_gives_one_method_fewer_runs_fails_the_fairness_gate(cases):
    """BM-004: the tuning grid of every method is cut to two candidates: the number of tuning runs differs from the protocol's four and the assertion fails"""
    cases.refuted('BM-004')


def test_a_resume_that_forgets_finished_groups_fails_the_resume_gate(cases):
    """BM-005: the reader of finished groups is replaced by one that finds none: every group is computed again and the assertion fails"""
    cases.refuted('BM-005')


def test_a_statistic_out_of_its_domain_fails_the_units_gate(cases):
    """BM-006: every statistic is written with a median of 1.5: the units gate reports the efficiency and the assertion fails"""
    cases.refuted('BM-006')


def test_a_pool_that_changes_the_rows_fails_the_worker_gate(cases):
    """BM-007: the rows this process computes have their efficiency median reduced by ten percent: the pool, which computes its own rows in other processes, no longer agrees and the assertion fails"""
    cases.refuted('BM-007')
