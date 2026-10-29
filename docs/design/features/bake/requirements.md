# Requirements: the bake: contract 1, the thirteen cases, the expected ranges, the lane and units gates

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The bake (`data-pipeline/run.py`, `pipeline/pipeline.py`, `pipeline/bake.py`) turns the thirteen cases of `data/examples/cases.json` into
the committed artifacts of `data/derived/`: contract 1 validates each record, every method valid for the case runs, the expected
ranges (`core/expect.py`) fail the bake outside the band, the lane gate and the units gate judge the result and the readiness is
recomputed. The bake runs on a workstation, never in CI. The tests are `tests/test_contract.py`, `tests/test_expect.py`,
`tests/test_pipeline_smoke.py`, `tests/test_manifest.py`, `tests/bake/` and `tests/methods/integration/`, over small planted
cases (`tests/bake/bakefix.py`) and over the real registry. The cases are C01 to C10, C12 and C13, and C11, which contract 1
refuses.

| ID | Requirement | Gate |
|---|---|---|
| BK-001 | IF a value is missing, not numeric, NaN, infinite, boolean where a number is due or out of range, THEN contract 1 SHALL reject the record with the field named in its reason, never coerce it. | `tests/test_contract.py::test_adversarial_bad_values_rejected_not_coerced` |
| BK-002 | IF a record lacks a required field or carries one the schema does not declare, THEN contract 1 SHALL reject it with the field named. | `tests/test_contract.py::test_missing_field_and_extra_field_rejected` |
| BK-003 | IF a trap lies at or beyond the half field of its setup, THEN contract 1 SHALL reject the record with the bound in micrometres in its reason, so that case C11 is refused and never computed. | `tests/test_contract.py::test_out_of_field_names_the_bound` |
| BK-004 | THE case registry SHALL list thirteen cases, C13 (the disordered array of 819 traps) next to C03, and contract 1 SHALL accept C13 and the committed cases document SHALL hold it. | `tests/bake/test_c13.py::test_the_registry_lists_c13_next_to_c03` |
| BK-005 | THE target of C13 SHALL be 819 traps on integer FFT bins at least 5 bins apart, drawn from the seed `20261847`, because the coordinates of Kim et al. 2019 are not published. | `tests/bake/test_c13.py::test_c13_is_819_traps_on_bins_at_least_five_bins_apart` |
| BK-006 | IF a baked value lies outside the expected range its case declares, THEN the bake SHALL fail naming the case, the method and the metric. | `tests/test_expect.py::test_a_value_outside_its_range_is_named` |
| BK-007 | THE measured range of a metric SHALL be the wider of 10 percent around the median and the spread of the seeds. | `tests/methods/integration/test_i1_integration.py::test_range_rule_is_the_wider_of_ten_percent_and_the_seed_spread` |
| BK-008 | THE lane gate SHALL judge the reference method of a case: live when it is pure Python on the allowed wheels, runs warm in at most 1500 ms and its trace is at most 256 KiB, else precompute with the reason. | `tests/bake/test_gates.py::test_lane_gate_decisions_and_budgets` |
| BK-009 | IF a baked value is in the wrong unit or domain (a percent written as a fraction, an efficiency above 1, a position in metres, a time in the wrong scale), THEN the units gate SHALL report it and the bake SHALL fail. | `tests/bake/test_gates.py::test_adversarial_domain_and_unit_violations` |
| BK-010 | THE trace of a case SHALL fit the 256 KiB budget of the lane gate: a trace over it is squeezed in the fixed steps of `core/trace.py` and the step is recorded, and one that cannot be squeezed is refused. | `tests/bake/test_gates.py::test_a_trace_that_fits_is_not_squeezed_and_one_that_does_not_is_squeezed_or_refused` |
| BK-011 | THE bake SHALL write identical artifacts for the same case, seed and version, byte for byte. | `tests/test_manifest.py::test_adversarial_two_bakes_of_the_same_inputs_write_identical_bytes` |
| BK-012 | IF a method of a case raises, THEN the bake SHALL flag it in the manifest, omit it from the artifacts and fail; IF a method is not registered, THEN the bake SHALL fail unless run with `--allow-missing-methods`, and flag it. | `tests/test_pipeline_smoke.py::test_adversarial_a_method_that_raises_is_flagged_omitted_and_fails_the_bake` |
| BK-013 | IF contract 1 refused a case, THEN the pipeline SHALL index it with its reason and never compute it, and a case id the registry does not know SHALL raise `KeyError`. | `tests/test_pipeline_smoke.py::test_a_refused_case_is_not_computed` |
| BK-014 | THE atom driver SHALL integrate with a step small enough that omega dt is at most 0.2 and SHALL oscillate at the radial frequency predicted by the curvature of the same map, within 20 percent. | `tests/methods/integration/test_i1_integration.py::test_the_atom_stays_in_the_map_and_oscillates_at_the_predicted_frequency` |
| BK-015 | THE `auto` form of M04, M05, M06 and M07 SHALL be the FFT form when every trap is on an FFT bin with z = 0 and charge 0, and the point-trap form otherwise, and the manifest SHALL flag the form each method chose. | `tests/methods/integration/test_i1_integration.py::test_auto_form_is_fft_on_bins_and_point_off_bins` |
| BK-016 | FOR a shaped target, THE bake SHALL score the signal region (the root-mean-square error over the measure region after the scale fit) in the two required metric slots, and the manifest SHALL flag that it does. | `tests/methods/integration/test_i1_integration.py::test_signal_error_agrees_with_the_methods_own_history` |
