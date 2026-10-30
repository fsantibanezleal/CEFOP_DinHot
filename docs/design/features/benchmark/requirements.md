# Requirements: the benchmark: protocol, fairness and skipped cells

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The benchmark (`data-pipeline/pipeline/benchmark/protocol.py`, document `data/derived/benchmark/results.json`) runs every method valid for a
geometry, with the same seeds, the same metrics and the same budgets, on the geometries G1 to G7: medians and inter-quartile ranges over the
seeds, one row per method, geometry, device, budget and parameter set, and the Pareto fronts. Its numbers are DinHot's own and measured, never
quoted. Budgets: the 10, 30 and 100 iteration rows are runs of exactly that length, the 50 ms and 1 s rows are time-capped runs, and one
converged run per seed serves as the 60 s row; every run is scored from its final phase through the device. Tuned rows exist only for
methods that declare a tuning grid. A cell that cannot run is listed with a bilingual reason and is absent from the rows. The release run
(20 seeds, 256 pixels) is a workstation job, never CI (ADR-0074); the tests run the same code on the reduced grid (64 pixels, 2 seeds) with
planted methods (`tests/bake/planted.py`).

| ID | Requirement | Gate |
|---|---|---|
| BM-001 | THE benchmark SHALL report, for every method, geometry, device and parameter set, each budget kind (iterations, time and converged) over every seed of the run. | `tests/bake/test_benchmark.py::test_every_budget_kind_is_reported_per_group` |
| BM-002 | IF a cell cannot run (a method not registered, a target it does not accept, a device it cannot model), THEN THE benchmark SHALL list it in `skipped` with a bilingual reason and SHALL write no row for it. | `tests/bake/test_benchmark.py::test_cells_that_cannot_run_are_listed_with_a_reason_and_absent_from_rows` |
| BM-003 | THE benchmark SHALL keep the tuned and the default rows of a method apart: a tuned row exists only for a method that declares a tuning grid, and a method's tuned parameters SHALL never appear as another's defaults. | `tests/bake/test_benchmark.py::test_adversarial_tuned_and_default_rows_never_mix_parameters` |
| BM-004 | THE tuning SHALL use the same number of runs for every method that is tuned. | `tests/bake/test_benchmark.py::test_tuning_uses_the_same_number_of_runs_for_every_method` |
| BM-005 | WHEN a run resumes, THE benchmark SHALL skip the groups already finished and keep their rows. | `tests/bake/test_benchmark.py::test_resume_skips_finished_groups` |
| BM-006 | THE results document SHALL validate against its schema and hold every statistic in the domain of its unit (an efficiency in 0 to 1, a time in seconds, a deviation in percent). | `tests/bake/test_benchmark.py::test_results_validate_and_are_in_units` |
| BM-007 | THE rows of the benchmark SHALL not depend on the number of workers. | `tests/bake/test_benchmark.py::test_pool_workers_give_the_same_rows` |
