# Adversarial validation: the physics engine (forward models, metrics, device, Zernike, dynamics, RNG)

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or refuted, and the test that plants it. `scripts/check_sdd.py` fails when a requirement has no row here (or two), when a check is empty, and when a gate names a test that does not exist. A planted row runs the requirement's own gate twice in child processes (`tests/adversarial/plant_run.py`): untouched, where it passes, and with the defect wrapped around the product's code, where it must fail.

| requirement | adversarial check | gate |
|---|---|---|
| EN-001 | the FFT trap fields are scaled by 1.001: the agreement test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_fft_form_that_disagrees_with_the_point_trap_form_fails_the_agreement_gate` |
| EN-002 | the focal field is scaled by 1.01 (one percent more power): the Parseval test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_propagation_that_creates_power_fails_the_parseval_gate` |
| EN-003 | the point-trap model is replaced by one that answers zeros for any trap list: the out-of-field test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_forward_model_that_accepts_a_trap_outside_the_field_fails_the_field_gate` |
| EN-004 | the focal bin is doubled: the geometry test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_focal_bin_of_the_wrong_size_fails_the_geometry_gate` |
| EN-005 | the uniformity is replaced by its complement: the definitions test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_uniformity_that_is_not_the_definition_fails_the_metric_gate` |
| EN-006 | the efficiency answers the plain sum for any input: the empty and NaN inputs no longer raise and the error test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_metric_that_accepts_an_empty_or_nan_input_fails_the_error_gate` |
| EN-007 | the quantizer is replaced by one that floors to the level below (an error up to twice the bound): the error-bound test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_quantizer_that_floors_fails_the_error_bound_gate` |
| EN-008 | the adjoint is doubled: the inner-product identity fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_an_adjoint_that_is_not_the_adjoint_fails_the_inner_product_gate` |
| EN-009 | the device focal field is scaled by 1.01: the brute-force comparison fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_device_field_that_is_not_the_dft_of_the_pixels_fails_the_envelope_gate` |
| EN-010 | the 32-bit output is XORed with 1: the independent-implementation test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_generator_that_leaves_the_published_stream_fails_the_rng_gate` |
| EN-011 | the constructor replaces every seed by 1 and accepts it: the bad-seed test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_generator_that_accepts_any_seed_fails_the_seed_gate` |
| EN-012 | every mode is scaled by 1.2: the Gram matrix is no longer the identity and the orthonormality test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_zernike_mode_of_the_wrong_norm_fails_the_orthonormality_gate` |
| EN-013 | the trajectory is doubled (a fourfold diffusion at the same corner frequency): the oracle test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_bead_with_the_wrong_diffusion_fails_the_corner_frequency_oracle` |
| EN-014 | the stiffness is halved: the equation test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_trap_stiffness_off_by_a_half_fails_the_trap_physics_gate` |
| EN-015 | the gain is scaled by a counter that grows with each call: the seeded-gain test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_camera_whose_gain_drifts_between_reads_fails_the_seeded_gain_gate` |
| EN-016 | the field check is replaced by one that accepts every trap: the out-of-field naming test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_trap_set_that_does_not_name_the_bound_fails_the_field_check_gate` |
| EN-017 | the validation of `Result` is removed: the bad results are accepted and the validation test fails | `tests/adversarial/test_dinhot_engine_refuted.py::test_a_result_that_skips_its_validation_fails_the_result_gate` |
