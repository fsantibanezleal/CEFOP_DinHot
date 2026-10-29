# Adversarial validation: the benchmark: protocol, fairness and skipped cells

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or refuted, and the test that plants it. `scripts/check_sdd.py` fails when a requirement has no row here (or two), when a check is empty, and when a gate names a test that does not exist. A planted row runs the requirement's own gate twice in child processes (`tests/adversarial/plant_run.py`): untouched, where it passes, and with the defect wrapped around the product's code, where it must fail.

| requirement | adversarial check | gate |
|---|---|---|
| BM-001 | each row is written with one seed fewer than the run's: the seed-count assertion fails | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_benchmark_that_drops_a_seed_fails_the_budget_gate` |
| BM-002 | the device skip rule is replaced by one that skips nothing: the multi-plane device cell is no longer listed and the assertions fail | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_protocol_that_skips_nothing_fails_the_skipped_cells_gate` |
| BM-003 | a planted method with a tuning grid is run next to methods without one: only it has tuned rows, and its tuned row beats its default row | `tests/bake/test_benchmark.py::test_adversarial_tuned_and_default_rows_never_mix_parameters` |
| BM-004 | the tuning grid of every method is cut to two candidates: the number of tuning runs differs from the protocol's four and the assertion fails | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_tuning_that_gives_one_method_fewer_runs_fails_the_fairness_gate` |
| BM-005 | the reader of finished groups is replaced by one that finds none: every group is computed again and the assertion fails | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_resume_that_forgets_finished_groups_fails_the_resume_gate` |
| BM-006 | every statistic is written with a median of 1.5: the units gate reports the efficiency and the assertion fails | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_statistic_out_of_its_domain_fails_the_units_gate` |
| BM-007 | the rows this process computes have their efficiency median reduced by ten percent: the pool, which computes its own rows in other processes, no longer agrees and the assertion fails | `tests/adversarial/test_dinhot_benchmark_refuted.py::test_a_pool_that_changes_the_rows_fails_the_worker_gate` |
