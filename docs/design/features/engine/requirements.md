# Requirements: the physics engine (forward models, metrics, device, Zernike, dynamics, RNG)

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The engine is the Python reference of the hologram physics under `data-pipeline/pipeline/model/holo/core/`: the two forward models
(the FFT form and the point-trap form), the angular spectrum, the trap metrics, the spatial light modulator (SLM) device model, the
Zernike basis, the trap physics and particle dynamics, the emulated camera and the portable random generator. The live engine
(feature `live-engine`) is held to it by parity tests. Gates are the tests of `tests/engine/`.

| ID | Requirement | Gate |
|---|---|---|
| EN-001 | THE FFT form and the point-trap form SHALL give the same trap fields on FFT bins, to a relative 1e-9. | `tests/engine/test_forward.py::test_fft_and_point_trap_agree_on_bins` |
| EN-002 | THE FFT propagation SHALL conserve total power (Parseval) and be inverted by its inverse transform. | `tests/engine/test_forward.py::test_parseval_fft` |
| EN-003 | IF a trap lies at or beyond the half field of the setup, THEN every forward model SHALL raise `OutOfFieldError` naming the trap, never wrap it around. | `tests/engine/test_forward.py::test_out_of_field_raises_everywhere` |
| EN-004 | THE focal bin SHALL be lambda f / (pad N p) and the half field lambda f / (2 p), from the setup alone. | `tests/engine/test_geometry.py::test_bin_and_field` |
| EN-005 | THE trap metrics SHALL be the definitions: efficiency the power in the traps, uniformity 1 - (max - min) / (max + min), relative standard deviation 100 std / mean. | `tests/engine/test_metrics.py::test_definitions` |
| EN-006 | IF the intensities are empty, not finite or sum to zero, or the weights are zero or of another length, THEN the metric SHALL raise `ValueError`, never return a number. | `tests/engine/test_metrics.py::test_error_cases` |
| EN-007 | THE phase quantizer SHALL round to the nearest of 2^b levels, with an error of at most pi / 2^b. | `tests/engine/test_device.py::test_quantize_error_bound` |
| EN-008 | THE adjoint of the crosstalk operator SHALL satisfy the inner-product identity with the operator, so that the gradient methods are exact. | `tests/engine/test_device.py::test_crosstalk_adjoint_inner_product_identity` |
| EN-009 | THE device focal field SHALL equal the brute-force discrete Fourier transform of a hologram of finite pixels (the fill factor), so that the pixel envelope is exact. | `tests/engine/test_device.py::test_pixel_envelope_against_brute_force_dft` |
| EN-010 | THE random generator SHALL be xoshiro128** seeded by SplitMix32 and reproduce the independent implementation and the committed reference stream bit for bit, so that the TypeScript port draws the same numbers. | `tests/engine/test_rng.py::test_matches_independent_implementation` |
| EN-011 | IF a seed is negative, fractional, boolean or above 32 bits, THEN the generator SHALL raise `ValueError`. | `tests/engine/test_rng.py::test_bad_seed` |
| EN-012 | THE Zernike modes SHALL be the Noll-indexed orthonormal basis over the unit disc, with rms 1 each. | `tests/engine/test_zernike.py::test_orthonormal_over_disc` |
| EN-013 | THE simulated bead SHALL have the corner frequency kappa / (2 pi gamma) and the diffusion kT / gamma of its parameters, recovered from its power spectrum. | `tests/engine/test_dynamics.py::test_corner_frequency_oracle` |
| EN-014 | THE gradient-force stiffness of a Gaussian trap SHALL be 2 alpha I0 / (c eps0 w^2), from the equations of the source. | `tests/engine/test_trapphys.py::test_gaussian_stiffness_eq12_13` |
| EN-015 | THE emulated camera SHALL give each trap the same gain on every read for a seed, whatever the order of the reads. | `tests/engine/test_camera.py::test_gains_are_per_trap_seeded_and_order_independent` |
| EN-016 | IF a trap is outside the field, THEN THE trap check SHALL raise `OutOfFieldError` that names the trap and the bound. | `tests/engine/test_traps.py::test_out_of_field_names_trap_and_bound` |
| EN-017 | THE `Result` of a method SHALL be a finite square phase with a list of history entries that carry the required keys, else `ValueError`. | `tests/engine/test_types_registry.py::test_result_validation` |
