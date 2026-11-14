# Changes: the benchmark at equal wall clock (unit U1 of 0.02.004)

- Every method stops at the deadline of a time row in every phase: `weighted_gs` takes a deadline, and the warm start, the outer loop and each
  line-search evaluation of the device-aware WGS (B1), the frame 0 and every frame iteration of the flicker-bounded sequence (B2) and the warm start
  and every lambda of the efficiency-uniformity front (B5) check it. A run cut by the deadline returns the iterate reached with its true counts.
- Every benchmark row records the work done: `iterations` is the inner iterations a run performed (B1 warm plus CG steps, B2 frame 0 plus frame
  iterations, B5 warm plus CG iterations) and the new `evaluations` statistic is the forward plus adjoint evaluations counted by `core/forward.py`
  (and by the crosstalk model) between the run and its scoring.
- The flicker-bounded sequence (B2) leaves the static benchmark: its frame 0 is the phase-fixed WGS it would be ranked against. Its sequence
  experiments are unchanged.
- Seeds: the time and converged rows run at least 5 seeds for every method, geometry and device; the iteration rows keep the 600 s group budget
  with at least 2.
- The large-array geometry is two geometries, `G6a` (lattice 32 x 32) and `G6b` (disordered 819); every seed runs both.
- Contract `benchmark-results` is 2.0.0 (the version gate reads the new required `evaluations` and the geometry ids as a breaking change): the
  report's extract scripts and the app refuse a 1.x document naming the version.
- A cell is read as a win only if the best published and the best proposed method both have at least 5 seeds, their interquartile ranges of the
  relative standard deviation do not overlap and their medians differ by at least 0.01 percentage points; otherwise it is a tie, and iteration rows
  never produce a win. The report's benchmark table reads the 1 s row, prints n per cell and tie; the Benchmark page prints the same reading.
- Requirements BM-008 to BM-016 with their gates; `tests/fixtures/benchmark-win-rule.json` is read by the Python and the TypeScript rule.
- The committed `data/derived` bake and readiness are of contract 1.x until the 0.02.004 generation; the tests that read the committed bake fail
  until it runs.
