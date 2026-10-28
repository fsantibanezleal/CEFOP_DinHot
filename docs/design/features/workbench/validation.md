# Adversarial validation: the example workbench, end to end

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or
refuted, and the test that plants it. `scripts/check_sdd.py` fails when a requirement has no row here (or two), when a
check is empty, and when a gate names a test that does not exist. A row is evidence that the requirement can fail,
not only that it passes.

| requirement | adversarial check | gate |
|---|---|---|
| EX-001 | a result of 0.75 planted against an expected range of 0.9 to 0.95 is refused and the message names the metric; an unknown metric and a case with no range are refused too | `tests/test_expect.py::test_adversarial_a_case_without_expectations_or_with_an_unknown_metric_fails` |
| EX-002 | the same case and seed baked twice into two roots must write the same bytes and the same SHA-256 (not only the same size), and the trace must carry a peak (an empty run would also be equal); a copy of the trace with one digit changed has the same size and must differ in bytes and in hash | `tests/test_pipeline_smoke.py::test_adversarial_same_seed_bakes_identical_bytes_and_a_changed_byte_of_equal_size_is_seen` |
| EX-003 | a test that passes while writing a new file under the derived data folder makes the whole session fail and name the file | `tests/adversarial/test_requirements_refuted.py::test_a_test_that_writes_a_committed_artifact_fails_the_session` |
| EX-004 | rows with a missing, non-numeric, NaN or out-of-range value are rejected with a reason, never coerced to a default | `tests/test_contract.py::test_adversarial_bad_rows_rejected_not_coerced` |
| EX-005 | a boolean in a number slot, an extra key and a missing key in a document are each refused, with the key named | `frontend/src/lib/contract.test.ts::adversarial: fails on a drifted document: a boolean is not a number, and extra and missing keys are named` |
| EX-008 | the host's HTML fallback answered in place of a JSON artifact is refused with an error that names the file | `frontend/src/api/artifacts.test.ts::adversarial: refuses an HTML answer (the host fallback for a missing file)` |
| EX-009 | the postbuild is run with no built index, then with an index that has no pre-paint theme script: both stop; a good build writes every standard route as its own page and 404.html (local-only: needs node and `npm ci` in frontend/, which the checks job does not install, and the CI web job runs the same script in `npm run build`) | `tests/adversarial/test_requirements_refuted.py::test_a_build_without_the_routes_or_the_theme_script_fails` |
| EX-010 | the runner of the measured gate is run against a stub gate that fails: it must fail with the stub's status and hand over the product's own brand and the built site (G6 itself, the half-viewport rule, is the shell's measurement, run locally by `npm run gate`) (local-only: needs node, and the measured gate itself needs a browser, so `npm run gate` runs it where one is installed) | `tests/adversarial/test_requirements_refuted.py::test_the_gate_runner_fails_with_the_shell_gates_status_and_measures_the_products_own_name` |
| EX-011 | the same stub run: the runner must not swallow a failing gate (G9, the selection key, is the shell's measurement, run locally by `npm run gate`) (local-only: needs node, and the measured gate itself needs a browser, so `npm run gate` runs it where one is installed) | `tests/adversarial/test_requirements_refuted.py::test_the_gate_runner_fails_with_the_shell_gates_status_and_measures_the_products_own_name` |
| EX-012 | a package.json version of 9.9.9 against VERSION makes the coherence guard fail and name it | `tests/adversarial/test_requirements_refuted.py::test_a_version_stated_twice_and_disagreeing_fails_the_coherence_guard` |
