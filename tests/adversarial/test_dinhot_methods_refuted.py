"""Method requirements MD-001 to MD-022 (docs/design/features/methods/): each test replaces the method's run by a degraded one (a flat phase with zero efficiency and uniformity) and runs the acceptance test of the ladder row in a child pytest, which must fail on its own assertion. The untouched acceptance tests are the suite tests/methods/, run by the ordinary session, so no control child repeats them here (they take tens of minutes)."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'MD-001': ('tests/methods/baseline/test_m01_superposition.py::test_acceptance_10x10_matches_published_trend', [
        {"target": 'pipeline.model.holo.methods.baseline.m01_superposition:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-002': ('tests/methods/baseline/test_m02_random_superposition.py::test_acceptance_10x10_over_seeds', [
        {"target": 'pipeline.model.holo.methods.baseline.m02_random_superposition:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-003': ('tests/methods/baseline/test_m03_random_mask.py::test_acceptance_10x10_over_seeds', [
        {"target": 'pipeline.model.holo.methods.baseline.m03_random_mask:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-004': ('tests/methods/baseline/test_m04_gs.py::test_acceptance_10x10_30_iterations_flat_beam', [
        {"target": 'pipeline.model.holo.methods.baseline.m04_gs:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-005': ('tests/methods/baseline/test_m05_gaa.py::test_uniformity_above_gs_at_equal_iterations', [
        {"target": 'pipeline.model.holo.methods.baseline.m05_gaa:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-006': ('tests/methods/baseline/test_m06_gsw.py::test_acceptance_10x10_flat_beam', [
        {"target": 'pipeline.model.holo.methods.baseline.m06_gsw:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-007': ('tests/methods/baseline/test_m07_phase_fixed_wgs.py::test_acceptance_fewer_iterations_than_gsw_on_50x30', [
        {"target": 'pipeline.model.holo.methods.baseline.m07_phase_fixed_wgs:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-008': ('tests/methods/baseline/test_m08_mraf.py::test_signal_error_five_times_below_gs_at_the_cost_of_efficiency', [
        {"target": 'pipeline.model.holo.methods.baseline.m08_mraf:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-009': ('tests/methods/optim/test_m09_direct_search.py::test_acceptance_uniformity_on_the_10x10_task', [
        {"target": 'pipeline.model.holo.methods.optim.m09_direct_search:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-010': ('tests/methods/optim/test_m10_cg.py::test_acceptance_square_lattice_below_one_percent_error', [
        {"target": 'pipeline.model.holo.methods.optim.m10_cg:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-011': ('tests/methods/optim/test_m11_wirtinger_adam.py::test_acceptance_lower_trap_intensity_error_than_gs_at_equal_iterations', [
        {"target": 'pipeline.model.holo.methods.optim.m11_wirtinger_adam:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-012': ('tests/methods/control/test_m12_closed_loop.py::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations', [
        {"target": 'pipeline.model.holo.methods.control.m12_closed_loop:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-013': ('tests/methods/optim/test_m13_crosstalk_cg.py::test_acceptance_lower_error_than_m10_on_the_crosstalk_device_for_a_large_disc', [
        {"target": 'pipeline.model.holo.methods.optim.m13_crosstalk_cg:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-014': ('tests/methods/control/test_m14_zernike.py::test_modal_search_recovers_noll_4_to_11_within_5_percent', [
        {"target": 'pipeline.model.holo.methods.control.m14_zernike:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-015': ('tests/methods/control/test_m15_vortex.py::test_isolated_vortex_ring_phase_within_0_1_rad', [
        {"target": 'pipeline.model.holo.methods.control.m15_vortex:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-016': ('tests/methods/control/test_m16_rearrangement.py::test_no_crossing_moves_for_alpha_1_5_on_7x7_to_3x3', [
        {"target": 'pipeline.model.holo.methods.control.m16_rearrangement:assign', "wrap": 'lambda *a, **k: orig(*a, **k)[::-1]'},
    ]),
    'MD-017': ('tests/methods/optim/test_m18_ot_mraf.py::test_acceptance_live_size_lower_error_than_random_start', [
        {"target": 'pipeline.model.holo.methods.optim.m18_ot_mraf:run', "wrap": 'lambda *a, **k: (lambda r: dataclasses.replace(r, fields=np.zeros_like(r.fields)))(orig(*a, **k))'},
    ]),
    'MD-018': ('tests/methods/baseline/test_m19_multiplane.py::test_acceptance_three_planes_within_the_band', [
        {"target": 'pipeline.model.holo.methods.baseline.m19_multiplane:run', "wrap": 'lambda *a, **k: (lambda r: dataclasses.replace(r, fields=np.zeros_like(r.fields)))(orig(*a, **k))'},
    ]),
    'MD-019': ('tests/methods/beyond/test_b1_device_wgs.py::test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device', [
        {"target": 'pipeline.model.holo.methods.beyond.b1_device_wgs:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-020': ('tests/methods/beyond/test_b2_flicker_bounded.py::test_acceptance_transient_intensity_at_least_0_9_and_above_lpi', [
        {"target": 'pipeline.model.holo.methods.beyond.b2_flicker_bounded:run', "wrap": "lambda *a, **k: (lambda r: dataclasses.replace(r, meta=dict(r.meta, transient_ratio=r.meta['transient_ratio'] * 0.5)))(orig(*a, **k))"},
    ]),
    'MD-021': ('tests/methods/beyond/test_b4_robust.py::test_acceptance_aberration_only_p95_sigma_1_25_times_below_phase_fixed_wgs', [
        {"target": 'pipeline.model.holo.methods.beyond.b4_robust:run', "wrap": '(lambda R: lambda setup, target, *a, **k: R(phi=np.zeros((setup.n_pix, setup.n_pix)), history=[dict(iteration=i + 1, efficiency=0.0, uniformity=0.0, rel_std=100.0, time_s=0.0, error=1.0) for i in range(60)], fields=np.zeros(1), meta=dict(open_loop_rel_std=19.0, coefficients=np.zeros(21))))(__import__("pipeline.model.holo.core.types", fromlist=["Result"]).Result)'},
    ]),
    'MD-022': ('tests/methods/beyond/test_b5_pareto.py::test_acceptance_hypervolume_and_domination_on_the_10x10_task', [
        {"target": 'pipeline.model.holo.methods.beyond.b5_pareto:run', "wrap": "lambda *a, **k: (lambda r: dataclasses.replace(r, meta=dict(r.meta, front=r.meta['front'] * 0.5)))(orig(*a, **k))"},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('methods'), control=False)


def test_a_degraded_m01_fails_its_acceptance_test(cases):
    """MD-001: a degraded M01 fails its acceptance test"""
    cases.refuted('MD-001', asserted=True)


def test_a_degraded_m02_fails_its_acceptance_test(cases):
    """MD-002: a degraded M02 fails its acceptance test"""
    cases.refuted('MD-002', asserted=True)


def test_a_degraded_m03_fails_its_acceptance_test(cases):
    """MD-003: a degraded M03 fails its acceptance test"""
    cases.refuted('MD-003', asserted=True)


def test_a_degraded_m04_fails_its_acceptance_test(cases):
    """MD-004: a degraded M04 fails its acceptance test"""
    cases.refuted('MD-004', asserted=True)


def test_a_degraded_m05_fails_its_acceptance_test(cases):
    """MD-005: a degraded M05 fails its acceptance test"""
    cases.refuted('MD-005', asserted=True)


def test_a_degraded_m06_fails_its_acceptance_test(cases):
    """MD-006: a degraded M06 fails its acceptance test"""
    cases.refuted('MD-006', asserted=True)


def test_a_degraded_m07_fails_its_acceptance_test(cases):
    """MD-007: a degraded M07 fails its acceptance test"""
    cases.refuted('MD-007', asserted=True)


def test_a_degraded_m08_fails_its_acceptance_test(cases):
    """MD-008: a degraded M08 fails its acceptance test"""
    cases.refuted('MD-008', asserted=True)


def test_a_degraded_m09_fails_its_acceptance_test(cases):
    """MD-009: a degraded M09 fails its acceptance test"""
    cases.refuted('MD-009', asserted=True)


def test_a_degraded_m10_fails_its_acceptance_test(cases):
    """MD-010: a degraded M10 fails its acceptance test"""
    cases.refuted('MD-010', asserted=True)


def test_a_degraded_m11_fails_its_acceptance_test(cases):
    """MD-011: a degraded M11 fails its acceptance test"""
    cases.refuted('MD-011', asserted=True)


def test_a_degraded_m12_fails_its_acceptance_test(cases):
    """MD-012: a degraded M12 fails its acceptance test"""
    cases.refuted('MD-012', asserted=True)


def test_a_degraded_m13_fails_its_acceptance_test(cases):
    """MD-013: a degraded M13 fails its acceptance test"""
    cases.refuted('MD-013', asserted=True)


def test_a_degraded_m14_fails_its_acceptance_test(cases):
    """MD-014: a degraded M14 fails its acceptance test"""
    cases.refuted('MD-014', asserted=True)


def test_a_degraded_m15_fails_its_acceptance_test(cases):
    """MD-015: a degraded M15 fails its acceptance test"""
    cases.refuted('MD-015', asserted=True)


def test_a_degraded_m16_fails_its_acceptance_test(cases):
    """MD-016: a degraded M16 fails its acceptance test"""
    cases.refuted('MD-016', asserted=True)


def test_a_degraded_m18_fails_its_acceptance_test(cases):
    """MD-017: a degraded M18 fails its acceptance test"""
    cases.refuted('MD-017', asserted=True)


def test_a_degraded_m19_fails_its_acceptance_test(cases):
    """MD-018: a degraded M19 fails its acceptance test"""
    cases.refuted('MD-018', asserted=True)


def test_a_degraded_b1_fails_its_acceptance_test(cases):
    """MD-019: a degraded B1 fails its acceptance test"""
    cases.refuted('MD-019', asserted=True)


def test_a_degraded_b2_fails_its_acceptance_test(cases):
    """MD-020: a degraded B2 fails its acceptance test"""
    cases.refuted('MD-020', asserted=True)


def test_a_degraded_b4_fails_its_acceptance_test(cases):
    """MD-021: a degraded B4 fails its acceptance test"""
    cases.refuted('MD-021', asserted=True)


def test_a_degraded_b5_fails_its_acceptance_test(cases):
    """MD-022: a degraded B5 fails its acceptance test"""
    cases.refuted('MD-022', asserted=True)
