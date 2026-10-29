"""Engine requirements EN-001 to EN-017 (docs/design/features/engine/): each test plants the defect the requirement forbids in the product's code and runs the requirement's own gate in a child pytest (plant_run.py), which passes untouched and must fail planted."""
from __future__ import annotations

import pytest
from plant_run import run_cases

pytest.importorskip("numpy")

TABLE = {
    'EN-001': ('tests/engine/test_forward.py::test_fft_and_point_trap_agree_on_bins', [
        {"target": 'pipeline.model.holo.core.forward:trap_fields_from_fft', "wrap": 'lambda *a, **k: orig(*a, **k) * 1.001'},
    ]),
    'EN-002': ('tests/engine/test_forward.py::test_parseval_fft', [
        {"target": 'pipeline.model.holo.core.forward:fft_focal_field', "wrap": 'lambda *a, **k: orig(*a, **k) * 1.01'},
    ]),
    'EN-003': ('tests/engine/test_forward.py::test_out_of_field_raises_everywhere', [
        {"target": 'pipeline.model.holo.core.forward:point_trap_fields', "wrap": 'lambda *a, **k: np.zeros(len(a[2]), dtype=complex)'},
    ]),
    'EN-004': ('tests/engine/test_geometry.py::test_bin_and_field', [
        {"target": 'pipeline.model.holo.core.geometry:focal_bin_m', "wrap": 'lambda *a, **k: orig(*a, **k) * 2'},
    ]),
    'EN-005': ('tests/engine/test_metrics.py::test_definitions', [
        {"target": 'pipeline.model.holo.core.metrics:uniformity', "wrap": 'lambda i, *a, **k: 1 - orig(i, *a, **k)'},
    ]),
    'EN-006': ('tests/engine/test_metrics.py::test_error_cases', [
        {"target": 'pipeline.model.holo.core.metrics:efficiency', "wrap": 'lambda i, *a, **k: float(np.sum(i))'},
    ]),
    'EN-007': ('tests/engine/test_device.py::test_quantize_error_bound', [
        {"target": 'pipeline.model.holo.core.device:quantize', "wrap": 'lambda phi, b, *a, **k: np.floor(np.mod(phi, 2 * math.pi) / (2 * math.pi / 2**b)) * (2 * math.pi / 2**b)'},
    ]),
    'EN-008': ('tests/engine/test_device.py::test_crosstalk_adjoint_inner_product_identity', [
        {"target": 'pipeline.model.holo.core.device:crosstalk_adjoint', "wrap": 'lambda *a, **k: orig(*a, **k) * 2'},
    ]),
    'EN-009': ('tests/engine/test_device.py::test_pixel_envelope_against_brute_force_dft', [
        {"target": 'pipeline.model.holo.core.device:device_focal_field', "wrap": 'lambda *a, **k: orig(*a, **k) * 1.01'},
    ]),
    'EN-010': ('tests/engine/test_rng.py::test_matches_independent_implementation', [
        {"target": 'pipeline.model.holo.core.rng:Rng.next_u32', "wrap": 'lambda self: orig(self) ^ 1'},
    ]),
    'EN-011': ('tests/engine/test_rng.py::test_bad_seed', [
        {"target": 'pipeline.model.holo.core.rng:Rng.__init__', "wrap": 'lambda self, seed=1, *a, **k: orig(self, 1)'},
    ]),
    'EN-012': ('tests/engine/test_zernike.py::test_orthonormal_over_disc', [
        {"target": 'pipeline.model.holo.core.zernike:zernike', "wrap": 'lambda *a, **k: orig(*a, **k) * 1.2'},
    ]),
    'EN-013': ('tests/engine/test_dynamics.py::test_corner_frequency_oracle', [
        {"target": 'pipeline.model.holo.core.dynamics:bead_trajectory', "wrap": 'lambda *a, **k: orig(*a, **k) * 2'},
    ]),
    'EN-014': ('tests/engine/test_trapphys.py::test_gaussian_stiffness_eq12_13', [
        {"target": 'pipeline.model.holo.core.trapphys:gaussian_stiffness_N_per_m', "wrap": 'lambda *a, **k: orig(*a, **k) * 0.5'},
    ]),
    'EN-015': ('tests/engine/test_camera.py::test_gains_are_per_trap_seeded_and_order_independent', [
        {"target": 'pipeline.model.holo.core.camera:EmulatedCamera.gain', "wrap": '(lambda calls: lambda self, i: calls.append(1) or orig(self, i) * (1 + 0.01 * len(calls)))([])'},
    ]),
    'EN-016': ('tests/engine/test_traps.py::test_out_of_field_names_trap_and_bound', [
        {"target": 'pipeline.model.holo.core.traps:check_in_field', "wrap": 'lambda *a, **k: None'},
    ]),
    'EN-017': ('tests/engine/test_types_registry.py::test_result_validation', [
        {"target": 'pipeline.model.holo.core.types:Result.__post_init__', "wrap": 'lambda self: None'},
    ]),
}


@pytest.fixture(scope="module")
def cases(tmp_path_factory):
    return run_cases(TABLE, tmp_path_factory.mktemp('engine'))


def test_a_fft_form_that_disagrees_with_the_point_trap_form_fails_the_agreement_gate(cases):
    """EN-001: the FFT trap fields are scaled by 1.001: the agreement test fails"""
    cases.refuted('EN-001')


def test_a_propagation_that_creates_power_fails_the_parseval_gate(cases):
    """EN-002: the focal field is scaled by 1.01 (one percent more power): the Parseval test fails"""
    cases.refuted('EN-002')


def test_a_forward_model_that_accepts_a_trap_outside_the_field_fails_the_field_gate(cases):
    """EN-003: the point-trap model is replaced by one that answers zeros for any trap list: the out-of-field test fails"""
    cases.refuted('EN-003')


def test_a_focal_bin_of_the_wrong_size_fails_the_geometry_gate(cases):
    """EN-004: the focal bin is doubled: the geometry test fails"""
    cases.refuted('EN-004')


def test_a_uniformity_that_is_not_the_definition_fails_the_metric_gate(cases):
    """EN-005: the uniformity is replaced by its complement: the definitions test fails"""
    cases.refuted('EN-005')


def test_a_metric_that_accepts_an_empty_or_nan_input_fails_the_error_gate(cases):
    """EN-006: the efficiency answers the plain sum for any input: the empty and NaN inputs no longer raise and the error test fails"""
    cases.refuted('EN-006')


def test_a_quantizer_that_floors_fails_the_error_bound_gate(cases):
    """EN-007: the quantizer is replaced by one that floors to the level below (an error up to twice the bound): the error-bound test fails"""
    cases.refuted('EN-007')


def test_an_adjoint_that_is_not_the_adjoint_fails_the_inner_product_gate(cases):
    """EN-008: the adjoint is doubled: the inner-product identity fails"""
    cases.refuted('EN-008')


def test_a_device_field_that_is_not_the_dft_of_the_pixels_fails_the_envelope_gate(cases):
    """EN-009: the device focal field is scaled by 1.01: the brute-force comparison fails"""
    cases.refuted('EN-009')


def test_a_generator_that_leaves_the_published_stream_fails_the_rng_gate(cases):
    """EN-010: the 32-bit output is XORed with 1: the independent-implementation test fails"""
    cases.refuted('EN-010')


def test_a_generator_that_accepts_any_seed_fails_the_seed_gate(cases):
    """EN-011: the constructor replaces every seed by 1 and accepts it: the bad-seed test fails"""
    cases.refuted('EN-011')


def test_a_zernike_mode_of_the_wrong_norm_fails_the_orthonormality_gate(cases):
    """EN-012: every mode is scaled by 1.2: the Gram matrix is no longer the identity and the orthonormality test fails"""
    cases.refuted('EN-012')


def test_a_bead_with_the_wrong_diffusion_fails_the_corner_frequency_oracle(cases):
    """EN-013: the trajectory is doubled (a fourfold diffusion at the same corner frequency): the oracle test fails"""
    cases.refuted('EN-013')


def test_a_trap_stiffness_off_by_a_half_fails_the_trap_physics_gate(cases):
    """EN-014: the stiffness is halved: the equation test fails"""
    cases.refuted('EN-014')


def test_a_camera_whose_gain_drifts_between_reads_fails_the_seeded_gain_gate(cases):
    """EN-015: the gain is scaled by a counter that grows with each call: the seeded-gain test fails"""
    cases.refuted('EN-015')


def test_a_trap_set_that_does_not_name_the_bound_fails_the_field_check_gate(cases):
    """EN-016: the field check is replaced by one that accepts every trap: the out-of-field naming test fails"""
    cases.refuted('EN-016')


def test_a_result_that_skips_its_validation_fails_the_result_gate(cases):
    """EN-017: the validation of `Result` is removed: the bad results are accepted and the validation test fails"""
    cases.refuted('EN-017')
