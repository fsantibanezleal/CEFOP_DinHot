- Benchmark engine: every phase of every method now stops at the deadline of a time row. The line searches of the
  conjugate-gradient minimizer (strong Wolfe and the staircase ladder; M10, M13, B1, B4, B5) check the deadline before each
  trial step and, with the deadline already past, evaluate nothing; B4's phase-fixed WGS warm start, the open-loop start and
  the inner iterations of M12, the weighted GS base and the modal sweeps of M14, and M03's loop over the traps take the
  deadline too (M03 reports the traps it served in `meta.traps_served`). With no time budget every result is bit-identical to
  before (78 method runs compared).
- Benchmark protocol: B3 (the learned warm start) is skipped on every geometry, with its reason in English and Spanish, while
  no network is released, so its rows no longer count the phase-fixed WGS fallback as a proposed method.
