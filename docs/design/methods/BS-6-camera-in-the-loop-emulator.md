# BS-6: Open camera-in-the-loop emulator (engine: M12 on the emulated camera)

| Item | Value |
|---|---|
| Ladder row | BS-6, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, feedback emulation, live (it is M12 on `core/camera.py`; the research record calls it B6) |
| Targets, dimensions | traps on FFT bins, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m12_closed_loop.py` (`run`, line 54) on `data-pipeline/pipeline/model/holo/core/camera.py` (`EmulatedCamera`, line 34); the case driver is `data-pipeline/pipeline/stages/feedback.py` |
| Gate | `tests/methods/control/test_m12_closed_loop.py` (the same file as M12) |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m12`, line 24) and `frontend/src/engine/holo/camera.ts` |
| Card | [M12](../../frameworks/M12_closed-loop-wgs.md) and [P06](../../frameworks/P06_emulated-camera.md) |
| Outcome | hypothesis confirmed one-sidedly (the emulated loop reaches the published level or better); the classification of the row as a method beyond the state of the art is open (see Limits) |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** Feedback on the trap intensities has been published on hardware only; slmsuite needs hardware and no open emulator reproduces the published feedback curves. A simulated camera (the forward model, a
fixed per-trap gain error, additive noise, blur and the diffraction-efficiency roll-off), closed with the published update rules, reproduces the published curves in the browser: from an open-loop spread of 19
percent rms (Nogrette et al. 2014) the Nogrette update at gain 0.7 reaches the published 1.4 percent within a factor of 1.5 in 20 iterations, and from 22 percent (Kim et al. 2019) the phase-fixed square-root update
reaches the published 1.59 percent within a factor of 1.5 in three steps.

**The gap.** The feedback of Nogrette et al. (https://arxiv.org/abs/1402.5329), Kim et al. (https://doi.org/10.1364/OL.44.003178), Ebadi et al. (https://arxiv.org/abs/2012.12281) and Schroff et al.
(https://doi.org/10.1038/s41598-023-30296-6) is applied on hardware, and the open library slmsuite needs hardware (algorithms dossier D5.1 B6). No open emulator that reproduces the published curves exists.

## Problem it answers

Make the camera-in-the-loop methods testable and teachable without hardware, in the browser, with every error a stated parameter.

## Inputs and outputs

- The emulator: `EmulatedCamera(seed, gain_rms=0.05, noise_rms=0.0, blur_bins=0.0, rolloff=True, fill_factor=1.0)` (`camera.py`, class at line 34, constructor at line 37). `measure(e, setup, traps)` returns the measured trap
  intensities from the centred focal field `e` in the units of $I_m = |V_m|^2$.
- The loop: `m12_closed_loop.run` (see M12): inputs `setup`, `target` (traps on bins), `budget`, `rng`, `variant`, `gain`, `camera`, `n_inner`, `n_start`, `start`; output the `Result` with the measured-spread `history`
  and `meta['open_loop_rel_std']`.
- The case driver: `feedback.run(rec, ctx, mid, first)` returns `{"steps": [{step, rel_std_pct, efficiency}, ...]}` for the case's `feedback` block (gain, steps, camera parameters).

## The method

The camera (`camera.py` module docstring) measures, at the FFT bin nearest to each trap, the intensity map: optionally blurred by a Gaussian of `blur_bins` (normalized weighted average over $\pm\lceil 3\sigma\rceil$), multiplied by the
pixel-aperture roll-off (`rolloff`), multiplied by a fixed gain per trap id $\exp(s z - s^2/2)$ with $s$ = `gain_rms` and $z$ the first normal of a stream seeded from the seed and the trap id (log-normal with mean 1 and relative rms
about `gain_rms`, drawn once per trap id, independent of the order and the composition of the trap set), plus additive Gaussian noise of rms `noise_rms` from the camera's own stream, clipped at 0. Every error is a parameter with a
stated meaning; it is an emulation, not a model of a sensor.

The loops are the two published updates of M12 (see M12): `nogrette`,
$w_m^T \leftarrow w_m^T/(1 - G(1-\rho_m))$ with $\rho_m$ the measured intensity relative to its target (the multiplicative reading is DinHot's, UNVERIFIED against the paper's printed form), and `kim`,
$T^{(j)}_m = \sqrt{\langle I\rangle/I_m}\,T^{(j-1)}_m$ with the focal phase frozen. The case driver (`stages/feedback.py`) applies the Nogrette factor $1/(1 - G(1 - I_m/\mathrm{mean}(I)))$ to the target weights of the case's
weight-aware method and re-runs it from the previous phase for `STEP_ITERATIONS` = 10 iterations per step (line 23), reporting the measured spread (the relative standard deviation of the camera readings divided by the
target weights).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| camera of `EmulatedCamera` | `gain_rms` 0.05, no noise, no blur, roll-off on | `camera.py` signature | engineering defaults |
| camera of M12 | `EmulatedCamera(seed=<first draw of rng>, gain_rms=0.19, rolloff=False)` | `m12_closed_loop.py` line 71 | Nogrette's 19 percent rms trap-depth spread |
| gain of M12 | 0.7 | `m12_closed_loop.py` line 55 | Nogrette et al. 2014 |
| case feedback blocks | C01: gain 0.7, 5 steps, camera 0.1; C02: 0.7, 20 steps, 0.19; C03: 0.9, 3 steps, 0.22; C13: 0.9, 5 steps, 0.22 | `data-pipeline/pipeline/cases/library.py` (the `feedback=` blocks, lines 172, 194, 214, 260) | C02 follows Nogrette (19 percent, gain 0.7, 20 iterations); C03 and C13 use the 22 percent of Kim et al. (the driver docstring names a Kim variant for C03) |

## Complexity and lane

One feedback iteration is `n_inner` FFT-form iterations plus one camera evaluation; the whole loop runs in the Web Worker (M12, lane `live`). The camera is a few array reads per trap.

## Acceptance criterion and gate

Ladder row: from the published open-loop spreads (19 percent rms, Nogrette 2014; 22 percent, Kim 2019), the emulated loop reaches the published curves within a factor of 1.5. Gate
`tests/methods/control/test_m12_closed_loop.py`:

- `::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations` (seeds 1 and 2): the camera gain error is 0.19, the open-loop spread in 14 to 25 percent, 20 iterations at gain 0.7; the final spread at most 2.1 percent
  (1.5 times the published 1.4) and below the open-loop spread divided by 8;
- `::test_kim_square_root_update_with_phase_fixing_three_steps` (seeds 1 and 2): the camera gain error is 0.22, `variant='kim'`, three steps; the final spread at most 1.8 percent (the upper end of the published
  1.59 plus or minus 0.18);
- `::test_nogrette_from_plain_gs_start_removes_algorithm_and_camera_error`, `::test_noisy_blurred_camera_still_converges`, `::test_default_camera_is_seeded_from_the_rng_and_deterministic`.

The camera itself is tested in `tests/engine/test_camera.py`.

## Evaluation that confirms or refutes it

Confirmed if the emulated loop ends at or below the published level from the published open-loop spread; refuted if it settles above 1.5 times the published value, or if reproducing it needs errors that no stated parameter
supplies. Both bounds of the test are one-sided (upper bounds): the emulated loop is allowed to do better than the published curve.

## Measured result

Acceptance run of 2026-10-28 (E2 report D4 and D5), 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), no noise, no blur, no roll-off:

| Loop | Open loop to closed loop (percent rms) | Published | Ratio to published |
|---|---|---|---|
| Nogrette, gain 0.7, 20 iterations, camera 0.19 | 20.9 to 1.47 (seed 1); 20.1 to 1.08 (seed 2) | 19 to 1.4 | 1.05 and 0.77 |
| Kim, three phase-fixed steps, camera 0.22 | 24.3 to 4.54, 1.68, 0.77 (seed 1); 23.4 to 3.77, 1.06, 0.53 (seed 2) | 22 to 1.59 | 0.48 and 0.33 |

The emulated loop reaches the published level for Nogrette and goes below it for Kim, because the emulated camera has no noise; with noise $5\times10^{-5}$, blur and roll-off the spread from a plain GS start falls below 4 percent.
Only the end points of the published curves are compared (the intermediate points are not). The research record also asked that conventional WGS reaches 6.47 percent in three steps within a factor of 1.5; that clause is
not in the ladder row and was not run (not established).

Committed case feedback curves (`data/derived/C02_grid_feedback/trace.json` and the measured ranges; the canonical seed 20261028, the case's reference method M07 with the Nogrette factor, `data/derived/manifests/`):

| Case | Gain, steps, camera error | Measured spread, step 0 to last (percent) |
|---|---|---|
| C02 | 0.7, 20, 0.19 | 20.31, then 6.10, 2.10, 1.00 at steps 1 to 3, to 0.213 at step 20 |
| C03 | 0.9, 3, 0.22 | 22.31 to 1.357 |
| C13 | 0.9, 5, 0.22 | 21.98 to 0.522 |
| C01 | 0.7, 5, 0.10 | 9.11 to 0.0232 |

Over the three seeds of the canonical bake the final spread is 0.095 to 0.77 percent (C02), 1.11 to 1.37 (C03) and 0.45 to 0.52 (C13), from initial spreads of 18.3 to 20.3, 22.2 to 22.4 and 22.0 to 22.5 percent (`measured_ranges.json`).
The M12 method itself, scored on the true fields in the bake, is listed in the M12 record.

## Limits and failure modes

- Reproducing a published number by choosing the camera's error is a tuning of the emulator, not a validation of a real device: the real errors come from the SLM and the optics. The emulator is a teaching and test tool, and
  the result shows that the loop works against these stated errors (the research record's own risk statement).
- Classification, left open: the method tiers rule says a validation protocol, a calibration or a benchmark design is not by itself a method beyond the state of the art. BS-6 is an open emulator that reproduces published
  curves; whether it counts as a method beyond the state of the art or as a validation tool is a decision for the main session, and this record does not settle it.
- Only the end points of the two published curves are compared; the conventional-WGS clause of the research record is not run.
- The Nogrette update is read multiplicatively (UNVERIFIED); the printed form was not confirmed.
- Noise, blur and roll-off make the result worse than the ideal camera; the published experiments' own noise floor is not modelled.
- A measured hardware loop (a real SLM and a camera) is a documented frontier of the product, not part of this build.

## References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
