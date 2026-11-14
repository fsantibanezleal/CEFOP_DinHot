# Changes: B1 redefined, the Schroff loss and the per-frame sequence as baselines (unit U2 of 0.02.004)

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
