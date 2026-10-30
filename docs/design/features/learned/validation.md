# Adversarial validation: the two learned slots (cgh-net M17, warmstart-model B3): baselines, release rule, ONNX

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or refuted, and the test that plants it. `scripts/check_sdd.py` fails when a requirement has no row here (or two), when a check is empty, and when a gate names a test that does not exist. A planted row runs the requirement's own gate twice in child processes (`tests/adversarial/plant_run.py`): untouched, where it passes, and with the defect wrapped around the product's code, where it must fail.

| requirement | adversarial check | gate |
|---|---|---|
| LN-001 | the answer of M17 is relabelled `real`: the provenance assertion fails | `tests/adversarial/test_dinhot_learned_refuted.py::test_a_baseline_answer_labelled_real_fails_the_provenance_gate` |
| LN-002 | M17 raises a `ValueError` that names nothing: the test that matches the requirement in the message fails | `tests/adversarial/test_dinhot_learned_refuted.py::test_an_error_that_does_not_name_the_requirement_fails_the_geometry_gate` |
| LN-003 | the rendered planes are scaled by 1.1: the unit-energy assertion fails | `tests/adversarial/test_dinhot_learned_refuted.py::test_planes_that_lose_their_unit_energy_fail_the_encoding_gate` |
| LN-004 | the answer of B3 is relabelled `real`: the provenance assertion fails | `tests/adversarial/test_dinhot_learned_refuted.py::test_a_random_start_labelled_real_fails_the_b3_provenance_gate` |
| LN-005 | the recorded iteration medians are read back with the network start twice as fast (a ratio of 2 or more): the measured-negative assertions fail | `tests/adversarial/test_dinhot_learned_refuted.py::test_a_recorded_ratio_that_reaches_two_fails_the_measured_negative_gate` |
| LN-006 | the committed metrics are read back with a median ratio of 0.9: the release assertion fails | `tests/adversarial/test_dinhot_learned_refuted.py::test_a_committed_accuracy_below_one_fails_the_release_gate` |
| LN-007 | a graph with an operator outside the list (LayerNormalization) is planted and the operator check names it (local-only: needs torch, onnx and onnxruntime of the GPU venv, which the checks job does not install) | `tests/learned/test_nets_export.py::test_adversarial_an_op_outside_the_list_is_seen` |
