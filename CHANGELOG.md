# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.02.004], 2026-11-20

The benchmark compares the methods at equal wall clock, the first proposed method is what its measurements support, and the
publications are revised from a new generation.

### Changed

- Method B5 is "Efficiency-uniformity continuation" (Spanish "Continuación eficiencia-uniformidad") in the engine `SPEC`, the SDD ladder row and
  views, the B5 design record, the methods and benchmark requirements, and every reader text of the app in both languages. Its paper
  (Zenodo 10.5281/zenodo.24022463) finds 4 to 7 of its 20 points dominated by weighted GS iterates, so it is not the Pareto front.
- The name "Pareto front" stays only for a non-dominated set computed from measured points (the Story page's front of the methods' medians).
  The Methodology and the Benchmark pages say that the continuation points are not a non-dominated set.
- The App's convergence sub-view `pareto` is labelled "Trade-off" (Spanish "Compromiso"): it compares every method of a benchmark cell on the
  efficiency-uniformity plane and recommends one, and it draws no Pareto front. Its B5 series and readout read "Efficiency-uniformity
  continuation". The Benchmark tab of the same name reads "Efficiency-uniformity continuation". The URL value `?tab=pareto` is unchanged.
- Unchanged identifiers: the id `B5`, the module `b5_pareto.py`, the design record file names, the `pareto` key of `benchmark-results` and
  every field name. The committed manifests under `data/derived` carry B5's old name until the 0.02.004 generation regenerates them.
- Requirement MD-026 with its gates: the engine name test, `frontend/src/content/methodology/b5-name.test.ts` (source strings and the built
  `dist` text) and an adversarial row.
- The papers, the report and the notebooks are renamed by a later unit.
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
- B1 is "Device-aware conjugate-gradient refinement" (Spanish: "Refinamiento por gradiente conjugado con modelo del dispositivo"), named
  "Device-aware weighted GS" until 0.02.003; the id B1 is unchanged. The name is changed in the engine, the case library, the app's ladder, methodology
  and case texts and the design documents of the method. The committed manifests, the bake and the papers keep the old name until the 0.02.004
  generation and the later unit that renames the papers and the notebooks.
- B1's `weights` option (the multiplicative weight update of weighted GS before every outer iteration) is False by default. The ablation of the paper
  gives a spread 7 times lower without it on the acceptance task (0.030 against 0.205 percent) and 3 times lower on the full device (0.242 against
  0.724 percent), and mixed results on the benchmark lattices. `weights=True` reproduces the 0.02.003 run exactly (a run recorded before the change is a
  test fixture, `tests/fixtures/b1_recorded_before_0_02_004.npz`); the default equals the old `weights=False` exactly.
- B1's new `loss` option: `'efficiency-level'` (default, the target of 0.02.003) or `'normalized-error'`, the normalized-error cost of Schroff et al. 2023
  (Sci. Rep. 13, 3252, eq (3), p. 3) on the trap intensities through the same device model, with the same warm start, conjugate-gradient optimizer and
  best-iterate safeguard, so a comparison isolates the loss. Its gradient is checked against finite differences. `steepness` (default: the relative
  squared error scale) is an option; Schroff et al.'s `s = 1e12` is a pixel-grid constant that only rescales the cost.
- M16's new `sequence` option: `'lpi'` (default, unchanged) or `'per-frame-gs'`, the hologram sequence of Kim, Kim, Lee and Ahn 2019 (Opt. Express 27(3),
  2184): a weighted GS per frame towards that frame's trap positions, the previous frame's phase as the initial phase ("induction", section 3.3,
  p. 2188), 5 iterations per frame (`frame_iterations`, Fig. 3 caption, p. 2190). The trajectory and the frame count are those of the linear phase
  interpolation. `budget.time_s` is a deadline for it (a cut run returns the frames it reached, `meta['truncated']`), `meta['iterations']` counts the GS
  iterations and the engine's evaluation counter counts the evaluations. `meta` of both sequences gains `sequence`, `frames_done`, `truncated` and
  `max_phase_step`.
- Requirements MD-023 to MD-025 with their gates and adversarial plants (`tests/adversarial/test_dinhot_methods_refuted.py`).
- Known limits: the rearrangement driver of a case (`stages/rearrangement.py`) already warm-starts every frame from the previous one with the case's weight
  method, so it is not M16's sequence and is unchanged; the benchmark and the bake are not run by this unit.
- The Methodology page states the device-aware conjugate-gradient refinement as a negative result against Schroff et al. 2023: their crosstalk model in a conjugate-gradient refinement already makes a spot array (their Fig. 5c), and through the same warm start, device model and conjugate gradient the method's own elements (the efficiency-level loss, the weight update, the best-iterate safeguard) add nothing measurable over their normalized-error loss; the gain belongs to the device model in the loop, it is not met on the square and quasi-periodic geometries of the benchmark device, and a hologram takes seconds to minutes. English and Spanish, callout title and body.
- The flicker-bounded sequence is stated as better than linear phase interpolation and a trade against the per-frame Gerchberg-Saxton with phase induction of Kim, Kim, Lee and Ahn 2019 (phase steps about 5 times smaller, a lower per-frame spread, a lower transient minimum); the reference is added to the bibliography.
- The efficiency-uniformity continuation is stated with its small hypervolume gain, the smaller share it keeps at a stricter reference point, and the fact that its curve is not the non-dominated set of the trade-off; the Benchmark page's claims, continuation and caveat texts say the same, and the aberration-robust hologram text carries the limits of its paper.
- The framework cards and design records of the device-aware refinement, the flicker-bounded sequence and the continuation carry the 0.02.004 figures and the same readings.
- Benchmark engine: every phase of every method now stops at the deadline of a time row. The line searches of the
  conjugate-gradient minimizer (strong Wolfe and the staircase ladder; M10, M13, B1, B4, B5) check the deadline before each
  trial step and, with the deadline already past, evaluate nothing; B4's phase-fixed WGS warm start, the open-loop start and
  the inner iterations of M12, the weighted GS base and the modal sweeps of M14, and M03's loop over the traps take the
  deadline too (M03 reports the traps it served in `meta.traps_served`). With no time budget every result is bit-identical to
  before (78 method runs compared).
- Benchmark protocol: B3 (the learned warm start) is skipped on every geometry, with its reason in English and Spanish, while
  no network is released, so its rows no longer count the phase-fixed WGS fallback as a proposed method.
- A time row whose median wall clock exceeds 1.5 times its budget (or that has a time budget and no `time_s`) is over budget: shown and
  labelled ("over budget: 6.4 s for 1 s", in English and Spanish) in the Benchmark page, the trade-off view and its readout, excluded from the
  best of its kind, from every win and from the trade-off recommendation, and a cell whose rows of one kind are all over budget is a tie that
  says so (decision 10, requirement BM-017). The report's data scripts apply the same rule (`OVER_BUDGET_FACTOR`, `is_over_budget` in
  `extract_methods.py`); both sides are tested on `tests/fixtures/benchmark-over-budget.json`. On the committed 0.02.004 benchmark 16 of
  90 cells change their reading, every one of them holding an over-budget row.
- Device-aware paper revised for 0.02.004 (unit U5b): the method is the device-aware conjugate-gradient refinement (the weight update an option that is off, measured as an ablation row), retitled "Device-Aware Conjugate-Gradient Refinement of Holographic Optical Trap Arrays: The Device Model in the Loop, Not the Loss or the Weights, Lowers the Spread in Simulation". The flicker-bounded sections left the paper for its own manuscript.
- The normalized-error loss of Schroff et al. 2023 is run through the same warm start, device model, optimizer and safeguard as the closest published method on the lattice task, the full device and the four benchmark lattices; Proposition 2 shows that for equal traps the two losses have the same value at the target-setting phase and gradients that differ by a push along the gradient of the total light, checked on the engine's two cost classes by `figures/make_figs.py`.
- Benchmark cells are read by the win rule with their n (cells of two seeds at 100 iterations are ranges, the equal-time rows hold five seeds or more); the cost in time per hologram on the device is stated for every recommendation. The abstract is 239 printed words; `coverage.json` claims only this method; `tex/main.pdf` is no longer tracked.
- New figures `fig-schroff.pdf` and `fig-geo.pdf`, a compact benchmark table and the derived-number macros (`figures/tab_bench_read.tex`, `figures/fig_numbers.tex`) written by `figures/make_figs.py` from the data files; the flicker-bounded figures were removed.
- The flicker-bounded phase-continuous sequence has a manuscript of its own, `manuscripts/flicker-bounded-sequences/` (LaTeX in `tex/`, eight figures drawn by `figures/make_figs.py` from `data/flicker.json`, `coverage.json`, the built `main.pdf`), positioned against the per-frame Gerchberg-Saxton sequence with phase induction of Kim et al. 2019 and measured against it and against linear phase interpolation; every number is read from the macros and tables of `data/measure.py`. Its derived title is "Flicker-Bounded Phase-Continuous Hologram Sequences for Moving Optical Traps: Smaller Phase Steps than Per-Frame Gerchberg-Saxton, Higher Transient Minima than Linear Phase Interpolation, and Where the Frame-Count Bound Fails" (to be written to `product.json` and to the new concept in one change).
- The device-aware refinement paper reads the regenerated 0.02.004 benchmark: the time per hologram (99 to 399 s at 10 outer iterations, 867 to 2271 s at 100, against 0.05 to 0.99 s and 0.41 to 8.09 s for phase-fixed weighted GS), the equal-time reading on the ideal device (1 geometry better for the refinement, 2 for phase-fixed weighted GS, 3 ties; it was 1, 1 and 4) and the C08 device rows (3 better, 3 ties, unchanged) are macros of the regenerated data. A row that overran its budget is no longer described as "at most one evaluation of the device model": the median row ends 0.11 to 0.40 s after the budget, the cause is marked UNVERIFIED, and no row is over the 1.5 times budget of the over-budget rule. A new paragraph reads the same C08 rows against the best published method of each cell, as the technical report does (the refinement is better on G1 and G3, superposition of prisms and lenses on G2), and states that the comparator, not the rows, makes the difference; the abstract, the discussion and the conclusions carry it. The figure script writes the new macros (`figures/make_figs.py`, `fig_numbers.tex`); the benchmark figure and the benchmark table are redrawn. The title is unchanged.
- The efficiency-uniformity paper reads the same benchmark in two ways and says which is which. The stored-curve hypervolume cells (14 cells, one seed behind each stored curve, 1 to 9 points per curve, the published points now 2 to 4 seeds, 1,404 rows) are all ties as before; the technical report's spread cells, which score the knee hologram of the continuation at an equal wall-clock time of 1 s, give it two wins on the ideal device (G1 and G5, 11 and 12 seeds, below 0.001 percent against 0.71 and 0.12 percent), at a lower efficiency than weighted GS. A new table (`figures/tab_spread.tex`, written by `figures/make_figs.py` from the benchmark file by the report's `cell_result`) lists the seven cells, the abstract, the introduction, the results, the discussion, the limits and the conclusions say that the two readings differ in what they compare (a curve against points, one seed, per iteration count; one hologram, at equal time, at least five seeds), and the title no longer says "No Win on the Benchmark": it now ends "Two Spread Wins at Equal Time and No Hypervolume Win on the Benchmark" (the main session writes `product.json` and Zenodo). Statements that were stale are corrected: the stored curves "hold between one and seven points" (now 1 to 9) and "end at a weight of 0.05" no longer appear, and "on all six of its geometries the stored curve is not above the published union at 100 iterations" is replaced by the count of the data (3 of 7). `coverage.json` lists the new table under `title_support`.
- Papers data on the 0.02.004 engine and bake (unit U5a). Device-aware paper: `measure.py` measures the static method only, at its default (no weight update), with the weight update as an ablation row, the normalized-error loss of Schroff et al. 2023 as the closest published method (acceptance task, full device and, in `b1_weights_geo.py`, the four benchmark lattices, five seeds), n per benchmark cell, the win rule of the technical report's `cell_result` read at the equal-time row, and the per-hologram time of every method compared; the flicker-bounded measurements left this script.
- New `manuscripts/flicker-bounded-sequences/data/measure.py`: the flicker-bounded sequence against linear phase interpolation and the per-frame GS with phase induction of Kim et al. 2019 (5 and 10 iterations per frame) on the acceptance task, the 12 and 20 bin moves and the C10 sort, with the frame-count bound, phase steps, transient intensity, time, the ablation and the seven figure series and five tables of its docstring.
- Efficiency-uniformity data: the five-point union is the headline and the four-point union the secondary row, the reference-point sensitivity adds (0, 0.9) and (0, 0.95) with the share of the headline each keeps, and the stored benchmark prints n and reads a cell as a tie below five seeds. Aberration data: macros `ciClearN` and the ten-seed headline. Warm-start data rerun on the 0.02.004 engine.
- Technical report data: the device-time column, the ring cell of review B-2, the warm-start control numbers taken from the warm-start paper's own data, the companion rows quoted with the statistics the papers state, and `tests/manuscripts/test_papers_data.py`.
- The efficiency-uniformity paper reads each spread cell of the benchmark by the continuation's own row against the best published row of the cell (the win rule of the technical report's extraction, imported), on the ideal device and on the device of the benchmark at the one-second row. On the ideal device its record is 2 wins (the square lattice and the 3D lattice), 1 loss (the ring, against phase-fixed weighted GS, whose cell the report reads as a tie only because the device-aware refinement also reaches a spread below 0.001 percent) and 4 ties; on the device of the benchmark it is 0 wins, 2 losses (the square lattice, against direct search, and the ring, against the superposition of prisms and lenses) and 4 ties. The spread table prints both devices with the record, the text, abstract, discussion, limits and conclusions state it, no sentence says that the continuation ran only on the ideal device, and the title is re-derived from it ("Two Spread Wins and One Loss on the Ideal Device and Two Losses on the Benchmark's Device at Equal Time, No Hypervolume Win on the Benchmark"; the main session writes the same string in product.json and Zenodo).
- The efficiency-uniformity paper words the seed count of the published points as the fewest seeds behind a published point (direct search), and the label of its Figure 7 is no longer clipped.
- The device-aware refinement paper no longer prints a review marker for the cause of the benchmark's overrun (it says the paper does not isolate it), describes the technical report's comparator as the best published method that keeps at least half of the best published efficiency and is not over budget, reads the refinement's own row against it in its figure script, and says "at least 5 seeds on each side" in its internal validity.
- Both printed abstracts are below 250 words, counted from the built PDF with pdftotext (246 and 247); the title of the device-aware refinement paper is unchanged because nothing in the regenerated benchmark contradicts its clauses.
- The efficiency-uniformity paper no longer prints a review marker in its timing paragraph (it says the paper isolates neither the engine release nor the machine load), its abstract again gives the 95 percent intervals of the headline hypervolume difference and of the uniformity-floor difference (243 printed words), its title names the one-second row at which the record is read, and its figure script stops with an error instead of dropping a third win or loss or reading an over-budget continuation row.
- Efficiency-uniformity paper revised for 0.02.004: the method is named a weighted-cost continuation of the efficiency-uniformity trade-off throughout (the label "front" is gone except for the true Pareto-front concept), the five-point union is the headline with the four-point union as a secondary row, the reference-point table gains (0, 0.9) and (0, 0.95), related work and Table 1 position the method against invrs-gym and Maddox et al. (novelty narrowed to point-trap holograms), the benchmark is read by the win rule (every cell a tie), the abstract is within 250 words, and the title is re-derived ("... No Win on the Benchmark").
- Aberration-robust paper revised for 0.02.004: a related-work subsection on robust and tolerance-aware inverse design of photonic elements (Wang et al. 2011, BOSON-1, invrs-gym) places the sigma-point expected cost, the abstract is within 250 words and states that the level term dominates the decomposition, the ten-seed value leads, the count of seeds whose interval clears 1.25 is stated, and the sign test is called a within-hologram test.
- The README states the mixed results of two proposed methods from the 0.02.004 data: device-aware conjugate-gradient refinement (weight update off by default, hypothesis H3 refuted on two of six geometries, the normalized-error loss of Schroff et al. gives the same spread) and the efficiency-uniformity continuation (hypervolume gain of 0.0119 over the five published points, 0.0015 at the reference (0, 0.9), no win on the benchmark). It lists the flicker-bounded sequence as a paper in preparation, and `docs/frameworks.md` names B5 as the continuation.
- The notebooks `03-gerchberg-saxton/04-device-aware-refinement` and `05-optimization/05-the-efficiency-uniformity-continuation` replace the two old file names in both languages (coverage map, indexes and tests updated) and teach the methods as they are now: the weight update as a variant with its measured effect, the normalized-error loss of Schroff et al. as the closest baseline, the continuation as a curve that published iterates dominate and that is not the Pareto front. Every notebook was re-executed on the 0.02.004 bake with `scripts/run_notebooks.py`.
- The bake and the benchmark are regenerated on the 0.02.004 engine and promoted from a validated stage: 1,404 benchmark rows, the learned
  warm start out of the benchmark because its network is not released, and every worker of the bake and the benchmark opted out of the
  operating system's power throttling; with the deadline checked in every phase, 3 of the 210 rows of the 1 s budget end above 1.5 times
  it (25 before), and the over-budget rule reads them.
- `scripts/extract_manuscripts.py` re-extracts every manuscript reader of the bake and the benchmark in dependency order (the device-aware
  and continuation papers' readings, then the report's acceptance, macros and tables), with tests; the report's ladder table has a test that
  fails when it differs from a fresh extraction from the SDD.
- The report's extraction names four methods without a benchmark row (the three that refuse every geometry by their specification and the
  learned warm start), and its protocol sentence gives each one's reason.
- The benchmark protocol text says that every phase of every method checks the deadline of a time row between units of work and that a row
  over 1.5 times its budget is labelled over budget, in English and Spanish; the shipped results keep their generated text until the next
  regeneration.
- The device-aware refinement paper lives in `manuscripts/device-aware-refinement/` (its Zenodo record key stays `device-aware-flicker-bounded`).
- Publications of this release on Zenodo: the technical report v0.02.004 (10.5281/zenodo.24382463), the device-aware refinement paper v0.05
  (10.5281/zenodo.24381813), the efficiency-uniformity paper v0.02 (10.5281/zenodo.24382032), the flicker-bounded paper v0.01 under a concept
  of its own (10.5281/zenodo.24267370, concept 10.5281/zenodo.24267369), the aberration-robust paper v0.02 (10.5281/zenodo.24267334) and the
  learned warm-start paper v0.02 (10.5281/zenodo.24267282); `product.json` declares all six with their titles.
- Technical report (`manuscripts/holographic-trap-studio/`) revised for 0.02.004. Title and abstract re-derived from the equal-wall-clock benchmark:
  "DinHot: A Holographic Optical Trap Studio That Compares Hologram Methods at Equal Wall Clock on a Device Model, Where Most Benchmark Cells Tie"
  (the same title goes into `product.json` and the Zenodo record in one change; `coverage.json` `title_support` names `tab:benchmark`,
  `tab:benchmethods`, `tab:ring` and `fig:bench`).
- Protocol and results: equal wall clock with a deadline in every phase, the work recorded (`iterations`, `evaluations`), the flicker-bounded
  sequence out of every static cell, the win rule (5 seeds per side, disjoint interquartile ranges, 0.01 percentage points, otherwise a tie),
  G6a and G6b read apart; every benchmark comparison prints n and the time per hologram; the win counts are read from `studio_numbers.tex`.
- Discussion: the ring cell on the C08 device read as a trade-off of efficiency against spread and time with its n (`table_ring.tex`); every
  recommendation states its cost in time.
- Proposed methods named as their papers name them (device-aware conjugate-gradient refinement, a negative result against the normalized-error loss of
  Schroff et al.; efficiency-uniformity continuation, not a Pareto front, with its 8-seed result and interval; the flicker-bounded sequence cited as a
  companion paper). The warm-start numbers come from the warm-start paper's own data on one set; the companion papers' numbers are read from their
  generated macro files by the preamble (`\importmacros`), never retyped.
- Contract sections: the six copies of the generic version sentence replaced by what is specific to each contract; the garbled phrases, the frame-0 cost
  of the sequence, the source of e0, the displayed single-trap inequality and the companion statistics corrected; floats placed with `[!htbp]` and the
  Figure 9 reading flushed, so that none prints more than two pages after its reading.
- Figures redrawn (`figures/make_figs.py`, `make_figs_more.py`): the continuation panels for the seven geometries, and the warm-start control panel
  read from the warm-start paper's data. `tex/main.pdf`, a tracked build output, is removed; the built PDF is `main.pdf` at the folder's root.
- The technical report states the benchmark as it now runs. The title reads "at a One-Second Deadline" in place of "at Equal Wall Clock": every phase of every method checks the
  deadline, but the check runs between units of work, so a row can end past it. The protocol, the abstract, the results and the conclusions say so and no longer say that every
  method honours the deadline. A time row whose median wall clock exceeds 1.5 times its budget is over budget and is never a best or a win. In the regenerated results file 3 of
  the 210 rows at the 1 s deadline are over budget (the Wirtinger descent on G6a and G6b and the crosstalk conjugate gradient on G6b, all on the C08 device), none is a best and
  no reading changes without the rule; 107 of the 210 rows at the 0.05 s deadline are over budget and no cell is read there. The protocol also states the opt-out of the
  operating system's power throttling next to the shared-load sentence.
- tab:benchmark is now generated by figures/make_figs_more.py from the results file with the win rule of data/extract_methods.py: it prints the time per cell, the reason of every
  tie and the rows over budget. Its macros (the over-budget counts, the shaped-field rows, the winners by name) are in figures/bench_deadline.tex. The appendix of contract fields
  is split into one file per table (figures/fields_*.tex) so that each table prints after the sentence that reads it; no float prints more than one page from its reading.
- Every win is named. On the ideal device the two wins are the efficiency-uniformity continuation's (G1 and G5, below 0.001 percent: a statement about the model); its paper's
  absence of a win concerns the hypervolume cells of its stored curve. On the C08 device the two wins are the device-aware refinement's, which is the device model with a
  weighted-GS warm start: the warm-started normalized-error loss of Schroff et al. gives the same spread, the benchmark's replication of Schroff et al. starts cold (1 iteration
  at 1 s) and the recommendation is the device model in a conjugate-gradient step with either loss.
- The learned warm start has no benchmark statement left; the leader sentence states that it is read among the methods measured on every point-trap geometry of the device. The
  aberration-robust hologram is quoted with the statistic of its own paper (median over 10 seeds, with its bootstrap interval), imported from its generated macro file; the
  continuation is quoted with its paper's statistic over 8 seeds. The optimal-transport recommendation quotes its benchmark rows on G7 against mixed-region amplitude freedom
  and the half-efficiency floor; the Zernike recommendation quotes its time. The linear-profile result of the flicker-bounded sequence is stated as a comparison added after the
  results, on the 13-frame move only, with its sort result.
- Minor findings: the six runs per seed are stated with the group bound; the residual "front" wording of the text is "curve"; the knee comparison says lower efficiency for the
  direct search only; the refinement's spread below the resolution of the file is stated at 100 iterations; the three-seed row of the refinement on C08 is labelled as measured
  with the weight update on; the single-trap reference level is introduced as such; title_support names tab:benchmark and tab:ring.
- Technical report: the continuation's record is stated as its own paper states it (reads its own row per cell: ideal device 2 wins, 1 loss on G2, 4 ties; C08 device 0 wins, 2 losses on G1 and G2, 4 ties; the report's table reads the best row of each kind, which is why G2 on the ideal device is a tie there), all from the paper's macros.
- Technical report: the refinement's one-second ideal-device record (1 win on G1, 2 losses on G6a and G6b, 3 ties) replaces "they tie", from the device-aware paper's macros; "ties elsewhere" in the summary is scoped to the C08 device.
- Technical report: the conclusions name the methods of each benchmark win; the bibliography entry of the efficiency-uniformity paper carries its final title; Figure 6 and Table 26 print on the page after their reading; a stray comma in the protocol is removed.
- The software design document's method ladder (rows BS-1, BS-2, BS-4 and BS-5), the Benchmark page's recorded column and the design records of the four proposed methods state the 0.02.004 measurements, each value read from the committed data of its paper: the device-aware refinement as a negative result against the normalized-error loss of Schroff et al. 2023 (201.3 against 159.9 times over phase-fixed weighted GS on the crosstalk device, 23.5 against 26.1 on the 4-bit device, 4 of 6 benchmark geometries meeting both thresholds), the flicker-bounded sequence as a trade against per-frame Gerchberg-Saxton with phase induction (largest phase step 0.077 rad against 0.408 rad, a lower transient minimum), the aberration-robust hologram over three and ten seeds, and the efficiency-uniformity continuation with the five-point union as its headline, its reference-point sensitivity and the benchmark count (3 of 7 geometries at 100 iterations).
- Adopted CAOS_PRODUCT_TEMPLATE 0.15.011 and 0.15.012 through `template_adopt.py`. The manuscript content check measures the abstract
  as it prints (150 to 250 words for a paper, 200 to 300 for the technical report), so it refuses the three papers whose abstracts ran
  over at 0.02.003 until their revisions shorten them. The readiness admission tests pin the generation environment's root, and the
  template's browser checks launch without a proxy. The one conflict, the repository validation rows RP-018 and RP-026, keeps DinHot's
  rows and adds the template's new admission test to RP-018.
- Adopted CAOS_PRODUCT_TEMPLATE 0.15.013 through `template_adopt.py`: the shell is pinned at 0.26.2 (already on `develop` with
  release 0.02.003), and a version-stamped stage input is refused only inside a promoted folder (RP-030), so the engine reference
  fixtures the readiness provider reads in the stage are carried.
- The units gate bounds the relative standard deviation of a hologram by its mathematical maximum for the number of traps it was computed over, 100 times the square root of N minus 1 (all the light in one trap), instead of a fixed 1000 percent; a shaped target keeps its clipped 1000, and a benchmark row whose geometry the results document does not list is reported as a units problem. A random mask stopped at its time budget on a 119 or 819 trap array leaves traps dark and has a spread above 1000 percent, which is a measurement, not a unit error.
- Every worker process of the bake and of the benchmark, and the calling process of their sequential paths, opts out of Windows power throttling, which had run the benchmark's workers at about half a core on an idle machine and so changed how many iterations a time-budgeted row gets; the benchmark's protocol text says so in English and Spanish.

### Fixed

- The App's trade-off view draws two methods of one kind at the same point (the same median uniformity and efficiency) on one chart row,
  named together in the readout, so the keyboard reaches every point: case C03 opens on G6a, where two published methods share the
  point (uniformity 0.956, efficiency 80.2 %), and the cursor could not step past them (gate G20 at every size).

## [0.02.003], 2026-11-15

### Changed

- Adopted CAOS_PRODUCT_TEMPLATE 0.15.010 and the shared app shell 0.26.2. The shell's gate now measures DinHot's long
  documentation pages, because the walk's budget scales with the document. The story's callout cards show their state. The
  fourteen methods in the rail are one select, using the shell's variant select layout, which was added for DinHot. The site's
  further files (the benchmark, the model metrics, the released models) are served through the base's product hook. Shell 0.26.0
  carries the fixes for the defects DinHot found on 0.25.0 (known defects 63 to 66 and 68): the story's step into the method view
  runs at 59.5 to 59.9 frames per second on the fifth percentile, against 15 to 20 on 0.25.0, because the shell keeps one number
  formatter per locale instead of building one per call. DinHot drops the two workarounds it carried for them: the particle view
  no longer waits for the callout band to hold before it is drawn, and no longer pauses the bead when the reader touches its chart.
  Shell 0.26.1 and 0.26.2 fix two defects DinHot found. On 0.26.0 a chart's readout was cut with an ellipsis, so the gate counted
  the Benchmark page's two robustness charts as no chart at 390 px in Spanish, whose hint at rest is wider than the chart (known
  defect 45); the readout now wraps. On 0.26.1 a keyboard reading that grew the readout of a chart filling its card dropped the
  crosshair, so the Pareto view and the particle trajectory read the hint (known defect 70); the crosshair now stays on its point.
  The generation's staged inputs are stamped and checked before a generation (template 0.15.007 to 0.15.010).
- The App opens on the optical train, from the laser to the traps, drawn from the case's setup, and shows the SLM in section, one
  pixel row with its commanded and displayed phase; both carry anchored callouts. A trap selected on the focal plane, in the per-trap
  bars or on the optical train is selected everywhere. The method at work redraws the focal plane at the iteration the reader scrubs.
- A guided story of five steps (`/story/setup`, `/story/device`, `/story/method`, `/story/compare`, `/story/hold`) states one measured
  finding per step, computed from the release's artifacts; the comparison step is on the modelled device.
- Every method is named by its name in the app, the notebooks, the manuscripts and the README; the engine ids stay in code and data.
- The notebook runtimes live in the device's venvs root (`<venvs root>/dinhot/`), as the base requires.
- Re-baked at 0.02.003: case C01 traps a bead in water (medium index 1.33), so its stiffness and corner frequency are 1.98 pN/um and
  34.5 Hz; the other twelve cases reproduce; the benchmark was run again (its cells run the seeds a 600 s wall-clock bound admits);
  the model metrics are measured again at this version by the generation itself.
- Publications: the technical report v0.02.003 (10.5281/zenodo.24049958) and the device-aware weighted GS and flicker-bounded
  sequences paper v0.04 (10.5281/zenodo.24049969), and three new papers: the efficiency-uniformity front (10.5281/zenodo.24022463),
  the aberration-robust hologram (10.5281/zenodo.24022465) and the learned warm start (10.5281/zenodo.24022471), each generated
  from this bake and reviewed by a reader other than its writer.

### Fixed

- The review findings of the technical report, the four method papers and the notebooks of topics 01 to 08, and the citations checked
  against the full texts where they were open.
- The full gate's findings on the release build: labels that overlapped or were cut in the optical train, the SLM section, the
  phasor figure and the lanes figure; the story's callouts, which overlapped at some sizes and were missing on the phone; the
  method step, which kept changing while idle.
- The local generation starts again. Template 0.15.007's check refused every version-stamped stage input, and DinHot carries its
  engine reference fixtures (`tests/fixtures/engine/`, stamped with the engine version that wrote them) for its readiness provider
  to read in the stage, outside the promoted payload; CI failed `test_the_template_workflow_config_passes`. The template's fix
  (0.15.013: refuse a stamped input only inside a promoted folder) is taken verbatim: `scripts/local/workflow.py` and its test.
- At 390 px, dense traps at the edge of a small optical-train field no longer overlap: a site that still overlaps after its nudge
  moves to the nearest free point inside the field (case C06).
- The Pareto view reads every method at a uniformity value two of them share: one chart row per value, so the keyboard and the
  pointer read both (on 0.02.002 the cursor read only the first row at that value; case C08).
- Two readings of the views by a reviewer other than their builders:
  - **The story:** its exits open the App on the step's view and method. Its callouts sit above their subjects on every screen size.
    The hold step pins its cards to the bead and to the fitted corner frequency.
  - **The App's views:**
    - A trap selected anywhere is marked in the focal image and in the per-trap bars. The focal image has micrometre axes and three callouts.
    - The dynamics view shows the bead in its trap with its position against time and its spectrum.
    - The Pareto view tells its series apart, draws the seed ranges, and recommends a method with its reason.
  - **Text:** cases and benchmark geometries are named by their names, never their ids, and micrometres are written µm.

## [0.02.002], 2026-10-31

### Changed

- Re-baked at 0.02.002, and the technical report v0.02.002 (10.5281/zenodo.23850386) and the manuscript v0.03 (10.5281/zenodo.23850389) generated from that
  bake. The report now states that the benchmark's cell medians depend on the seeds a wall-clock bound admits, so the count of
  geometries where the stored Pareto front meets the published hypervolume at 100 iterations moves between runs (margins at most 0.007).

## [0.02.001], 2026-10-31

### Changed

- Adopted CAOS_PRODUCT_TEMPLATE 0.14.000: each method is named by its name wherever a reader sees it. The app, the notebooks, the
  README and both manuscripts present 19 published methods and 5 proposed methods; the Methodology page groups them by family, and
  the Benchmark page compares published and proposed methods, each proposed method against the strongest published method of its cell.
- The level 3 and 4 notebooks use the sections Comparison and Evidence.
- The technical report v0.02.001 (10.5281/zenodo.23837873) is organized by method family, and the manuscript on device-aware weighted
  GS and flicker-bounded sequences is at v0.02 (10.5281/zenodo.23837877), both on the numbers of 0.02.000.
- Re-baked at 0.02.001: the cases reproduce; the benchmark's cells run more seeds within the same wall-clock bound, so its medians move.

## [0.02.000], 2026-10-30

### Changed

- Re-instantiated from CAOS_PRODUCT_TEMPLATE 0.12.000 (now 0.13.001) into this repository, history kept: the pipeline, the two
  contracts, the lanes, the workbench on the shared shell, the six routes, the guards and the measured gate. The
  FastAPI and WebSocket application, its vanilla JavaScript frontend and the legacy DinHotSys C++ sources and
  binaries leave the tree; they stay in the git history (tag v0.01.000).

### Added

- The App: the workbench of DinHot (five groups and the Context write-up, a trap editor, the live and replay lanes with their labels, Focus mode,
  the two learned model slots in the browser with their baselines) and the removal of the template's example engine.
- The live engine: a TypeScript port of the forward models, the device model and fifteen methods in a Web Worker, held to the Python engine by
  parity tests, with an optional WebGPU backend that falls back to the CPU path and records why.
- Case C13, the disordered array of 819 traps, and case C14, a three-plane volume at the geometry of the released cgh-net, so the bake holds
  fourteen cases (thirteen baked, C11 refused by contract 1); the cases bake in parallel; the expected ranges are measured on three seeds and
  each case card states them, written by `scripts/write_case_ranges.py`.
- The learned slots: `cgh-net` (M17) released with its ONNX graph and card, `warmstart-model` (B3) tested and refuted, each with its baseline.
- The specification of eleven features with a gate per requirement and an adversarial check per requirement (`docs/design/features/`), and the
  planted-defect tests that run each gate with its defect (`tests/adversarial/plant_run.py`); the measured resources
  (`docs/design/measured-resources.md`).
- The three method tiers: classical, state of the art and five proposals beyond it (BS-1 to BS-5; BS-3 refuted, BS-4 negative on pointing).
- Sixty didactic notebooks, thirty per language, by topic from simple to complex, reviewed against the notebook bar and re-executed.
- The Benchmark page: the protocol, one tab per geometry with its device, parameter set and budget, the three-tier comparison, the Pareto
  fronts, the five beyond claims with their verdicts, the learned models, the device and budget curves and an in-browser timing, read from
  the committed results at run time.
- The technical report and the manuscript of BS-1 and BS-2 are generated from the committed artifacts and from scripts that measure what a
  table states: the acceptance table by `manuscripts/holographic-trap-studio/data/acceptance.py`, BS-1, BS-2 and BS-2's scope on long moves
  and on C10 by `manuscripts/device-aware-flicker-bounded/data/measure.py`.

### Fixed

- M06 and M07 project the start hologram's field with the initial weights (g0 = 1): from the same start they now equal slmsuite 0.5.0's
  WGS-Leonardo and WGS-Kim at feedback exponent 1 to four digits (`tests/methods/baseline/test_m06_against_slmsuite.py`,
  `test_m07_against_slmsuite.py`), in Python, TypeScript and WGSL; the beyond methods' GS family runs those rules instead of a copy, and the
  claims that rest on them were re-measured (BS-1, BS-2 over 8 and 6 seeds, BS-4, BS-5).
- The benchmark lists a cell whose method refuses the geometry as skipped with the method's reason, instead of stopping the run, and
  stores B5's Pareto front from the indices of its non-dominated points (the release run stopped on it).
- BS-4's robustness to pointing errors re-measured on the corrected engine: 1.04 times (1.02 before), still a reported negative.
- B1 (BS-1) returns its best iterate that keeps 0.9 of its warm start's efficiency: its weight update could wind up on a device
  it cannot follow (the benchmark's square lattice on the C08 device, where one seed fell to 0.03 efficiency); its acceptance
  figures are unchanged, C08 and the benchmark's B1 cells were re-measured.
- A released model without onnxruntime refuses to run instead of answering with its baseline under the learned method's id.
- The cgh-net, warmstart-model and model-metrics contracts (1.0.1) state the released slot: three focal planes in, the volumetric GS (M19)
  as its baseline.

## [0.01.000], 2026-07-03

### Added
- Adopt the `X.XX.XXX` versioning scheme: a `VERSION` file as the single source of truth, this `CHANGELOG`, and the first git tag. Baseline documenting the current shipped state; later changes are versioned by nature (major/minor/patch).
