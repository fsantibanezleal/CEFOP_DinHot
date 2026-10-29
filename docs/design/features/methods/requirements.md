# Requirements: the method ladder: the acceptance test of every method

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The method ladder of the SDD (`## Method ladder`) lists every method with its tier, its acceptance criterion and its gate. This feature
states each criterion as a requirement with the ladder's own test as its gate; the criteria are measured on DinHot's grids and set
against the published results named in the SDD's research basis. The learned methods M17 and B3 are in the feature `learned`.
The untouched tests are the suite
`tests/methods/`; an adversarial row replaces the method by a degraded one and the test must fail on its assertion.

| ID | Requirement | Gate |
|---|---|---|
| MD-001 | ON the 10x10 task with a flat beam, THE superposition of prisms and lenses (M01) SHALL reach an efficiency within 0.10 of 0.29 and a uniformity below 0.05. | `tests/methods/baseline/test_m01_superposition.py::test_acceptance_10x10_matches_published_trend` |
| MD-002 | ON the 10x10 task with a flat beam, THE random superposition (M02) SHALL reach an efficiency above M01 and at least 0.65, with a uniformity below 0.35. | `tests/methods/baseline/test_m02_random_superposition.py::test_acceptance_10x10_over_seeds` |
| MD-003 | THE random mask (M03) SHALL reach an efficiency of about 1/M for M traps. | `tests/methods/baseline/test_m03_random_mask.py::test_acceptance_10x10_over_seeds` |
| MD-004 | ON the 10x10 task with a flat beam, THE Gerchberg-Saxton method (M04) at 30 iterations SHALL reach an efficiency of at least 0.9 and a uniformity near 0.6. | `tests/methods/baseline/test_m04_gs.py::test_acceptance_10x10_30_iterations_flat_beam` |
| MD-005 | ON the 10x10 task, THE generalized adaptive additive method (M05) SHALL reach a uniformity above GS at equal iterations. | `tests/methods/baseline/test_m05_gaa.py::test_uniformity_above_gs_at_equal_iterations` |
| MD-006 | ON the 10x10 task with a flat beam, THE weighted GS (M06) SHALL reach an efficiency and a uniformity of at least 0.9 within 15 iterations. | `tests/methods/baseline/test_m06_gsw.py::test_acceptance_10x10_flat_beam` |
| MD-007 | ON a 50x30 array, THE phase-fixed weighted GS (M07) SHALL reach a relative standard deviation of 0.5 percent in fewer iterations than M06, with the phase fixed after 60 iterations. | `tests/methods/baseline/test_m07_phase_fixed_wgs.py::test_acceptance_fewer_iterations_than_gsw_on_50x30` |
| MD-008 | ON disc, ring and bar targets, THE mixed-region amplitude freedom method (M08) SHALL reach a signal-region error at least five times below GS, at the cost of efficiency. | `tests/methods/baseline/test_m08_mraf.py::test_signal_error_five_times_below_gs_at_the_cost_of_efficiency` |
| MD-009 | ON the 10x10 task, THE direct search (M09) SHALL reach a uniformity of at least 0.98. | `tests/methods/optim/test_m09_direct_search.py::test_acceptance_uniformity_on_the_10x10_task` |
| MD-010 | ON a square lattice, THE conjugate-gradient minimization (M10) SHALL reach an error below 1 percent. | `tests/methods/optim/test_m10_cg.py::test_acceptance_square_lattice_below_one_percent_error` |
| MD-011 | ON the 10x10 task, THE Wirtinger gradient descent with Adam (M11) SHALL reach a lower trap-intensity error than M04 at equal iterations. | `tests/methods/optim/test_m11_wirtinger_adam.py::test_acceptance_lower_trap_intensity_error_than_gs_at_equal_iterations` |
| MD-012 | FROM a 19 percent rms open-loop spread, THE closed-loop weighted GS on the emulated camera (M12) SHALL reach at most 2.1 percent in 20 iterations at gain 0.7, the emulated camera reproducing the published feedback curves. | `tests/methods/control/test_m12_closed_loop.py::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations` |
| MD-013 | ON the crosstalk device and a large disc, THE device-aware conjugate gradient (M13) SHALL reach a lower error than M10 without the model. | `tests/methods/optim/test_m13_crosstalk_cg.py::test_acceptance_lower_error_than_m10_on_the_crosstalk_device_for_a_large_disc` |
| MD-014 | THE sensorless modal search (M14) SHALL recover an injected set of Noll modes 4 to 11 within 5 percent of their amplitude. | `tests/methods/control/test_m14_zernike.py::test_modal_search_recovers_noll_4_to_11_within_5_percent` |
| MD-015 | THE Laguerre-Gaussian vortex trap (M15) SHALL wind the ring phase by 2 pi l with an error under 0.1 rad. | `tests/methods/control/test_m15_vortex.py::test_isolated_vortex_ring_phase_within_0_1_rad` |
| MD-016 | ON a 7x7 to 3x3 sort, THE Hungarian assignment with alpha 1.5 (M16) SHALL make no crossing moves. | `tests/methods/control/test_m16_rearrangement.py::test_no_crossing_moves_for_alpha_1_5_on_7x7_to_3x3` |
| MD-017 | ON the shaped targets, THE optimal-transport initialized MRAF (M18) SHALL reach a lower error than MRAF from a random start. | `tests/methods/optim/test_m18_ot_mraf.py::test_acceptance_live_size_lower_error_than_random_start` |
| MD-018 | ON a three-plane target, THE multi-plane GS (M19) SHALL bring every plane mean within 25 percent of the overall mean. | `tests/methods/baseline/test_m19_multiplane.py::test_acceptance_three_planes_within_the_band` |
| MD-019 | ON the crosstalk device, THE device-aware weighted GS (BS-1, B1) SHALL reach a relative standard deviation at least two times below M07 with an efficiency at most 10 percent lower. | `tests/methods/beyond/test_b1_device_wgs.py::test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device` |
| MD-020 | THE flicker-bounded phase-continuous sequence (BS-2, B2) SHALL keep the minimum transient intensity of a moving trap at least 0.9 of its mean, above linear phase interpolation. | `tests/methods/beyond/test_b2_flicker_bounded.py::test_acceptance_transient_intensity_at_least_0_9_and_above_lpi` |
| MD-021 | OVER a 200-sample ensemble of residual aberrations, THE aberration-robust hologram (BS-4, B4) SHALL reach a 95th-percentile relative standard deviation at least 1.25 times below M07 with an efficiency at most 10 percent lower. | `tests/methods/beyond/test_b4_robust.py::test_acceptance_aberration_only_p95_sigma_1_25_times_below_phase_fixed_wgs` |
| MD-022 | ON the 10x10 task, THE efficiency-uniformity Pareto front (BS-5, B5) SHALL reach a hypervolume at least that of the M04, M05, M09 and M06 points. | `tests/methods/beyond/test_b5_pareto.py::test_acceptance_hypervolume_and_domination_on_the_10x10_task` |
