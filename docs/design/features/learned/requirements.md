# Requirements: the two learned slots (cgh-net M17, warmstart-model B3): baselines, release rule, ONNX

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
Two model slots are catalog rows (`cgh-net` for M17 and `warmstart-model` for B3), each with a baseline behind the same contract
(M19 volumetric GS for M17, the random start of M07 for B3). A model is released only when it meets the criterion of its ladder row
on held-out data written apart before training; until then the baseline answers and says so. M17 is released; B3 was tested and
refuted, so its slot is empty and the measured negative is the record. Training and the ONNX export run locally on the GPU
(`requirements-gpu.txt`), never in CI (ADR-0074); the tests that need torch or onnx run in that venv. The release rule is also the
readiness state of the slot (feature `contracts`).

| ID | Requirement | Gate |
|---|---|---|
| LN-001 | WHILE no valid model card and graph are released for `cgh-net`, THE M17 module SHALL answer with the M19 baseline at the budget it was given and SHALL label the result `provenance` baseline. | `tests/learned/test_m17_cgh_net.py::test_the_baseline_answers_while_unreleased` |
| LN-002 | IF the setup is not the 128 x 128 SLM with padding 1, a trap is off the three planes or beyond 60 bins, or the target is a shaped field, THEN THE M17 module SHALL raise `ValueError` naming the requirement. | `tests/learned/test_m17_cgh_net.py::test_geometry_and_target_errors_name_the_requirement` |
| LN-003 | THE M17 input SHALL be three unit-energy amplitude planes rendered from the traps by the same generator that made the training data. | `tests/learned/test_m17_cgh_net.py::test_planes_from_traps_renders_three_unit_energy_planes` |
| LN-004 | WHILE no model is released for `warmstart-model`, THE B3 module SHALL answer with the random start of M07 and SHALL label the result `provenance` baseline. | `tests/learned/test_b3_warm_start.py::test_the_module_answers_with_the_random_start_while_unreleased` |
| LN-005 | THE record of the rejected `warmstart-model` SHALL state the measured ratio of the median iterations to 1 percent (random start over network start), below the 2 times the ladder row BS-3 requires, with the control that explains the gain, and no ONNX file of the slot SHALL exist while the claim is refuted. | `tests/learned/test_b3_warm_start.py::test_measured_negative_the_two_times_criterion_is_not_met` |
| LN-006 | WHERE `cgh-net` is released, THE committed model metrics SHALL show, on at least 150 held-out volumes, a median accuracy against GS above 1. | `tests/learned/test_m17_cgh_net.py::test_committed_metrics_meet_the_criterion` |
| LN-007 | THE exported graphs SHALL use only the operators the browser runtime supports, be small, and carry the input and output tensors the catalog row names. | `tests/learned/test_nets_export.py::test_graphs_are_web_safe_small_and_have_the_contract_io` |
