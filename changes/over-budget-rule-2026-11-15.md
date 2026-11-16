- A time row whose median wall clock exceeds 1.5 times its budget (or that has a time budget and no `time_s`) is over budget: shown and
  labelled ("over budget: 6.4 s for 1 s", in English and Spanish) in the Benchmark page, the trade-off view and its readout, excluded from the
  best of its kind, from every win and from the trade-off recommendation, and a cell whose rows of one kind are all over budget is a tie that
  says so (decision 10, requirement BM-017). The report's data scripts apply the same rule (`OVER_BUDGET_FACTOR`, `is_over_budget` in
  `extract_methods.py`); both sides are tested on `tests/fixtures/benchmark-over-budget.json`. On the committed 0.02.004 benchmark 16 of
  90 cells change their reading, every one of them holding an over-budget row.
