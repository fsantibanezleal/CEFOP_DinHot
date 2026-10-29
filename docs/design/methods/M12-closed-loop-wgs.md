# M12: Closed-loop weighted GS on an emulated camera

| Item | Value |
|---|---|
| Ladder row | M12, tier sota (SDD, Method ladder) |
| Family, lane | feedback control, live |
| Targets, dimensions | traps, 2D (FFT form: traps on bins, $z = 0$, no vortex) |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m12_closed_loop.py` (`SPEC` line 48, `run` line 54); camera in `data-pipeline/pipeline/model/holo/core/camera.py` |
| Gate | `tests/methods/control/test_m12_closed_loop.py` |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m12`, line 24) |
| Card | [M12](../../frameworks/M12_closed-loop-wgs.md); physics component [P06](../../frameworks/P06_emulated-camera.md) |

## Tier and role

State of the art, replicated on an emulation: camera-in-the-loop correction of the trap intensities. Two published procedures are replicated:
Nogrette et al., Phys. Rev. X 4, 021034 (2014), https://arxiv.org/abs/1402.5329 (19 percent rms trap-depth spread to 1.4 percent in 20
iterations at gain $G = 0.7$), and Kim, Kim, Lee and Ahn, Opt. Lett. 44, 3178 (2019), https://doi.org/10.1364/OL.44.003178 (22 percent to
1.59 percent in three phase-fixed steps against 6.47 percent for conventional WGS). The camera is an emulation (`core/camera.py`: per-trap fixed
gain error, additive noise, blur, roll-off): a result here shows that the loop works against those stated errors, not against an instrument
(the measured hardware loop is a documented frontier of the product). The case feedback curves of the section below, formerly the claim BS-6 (withdrawn as a beyond claim), are built on this module and this camera.

## Problem it answers

An open-loop hologram leaves the traps with an unequal depth because the optics and the camera disagree with the model; measuring the trap
intensities and rescaling the target iteratively brings them to the percent level.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` on FFT bins (`_gs.check_on_bins`, `m12_closed_loop.py` line 69; otherwise a `ValueError`),
  `budget` (`iterations` counts feedback iterations; `time_s` an optional cap), `rng`, optional `init`, `variant` (`nogrette` or `kim`),
  `gain` in $(0, 1]$, `camera`, `n_inner`, `n_start`, `start` (`gsw` or `gs`). Invalid values raise a `ValueError` (lines 57 to 67).
- Output: `Result` with `phi`, one `history` entry per feedback iteration: `uniformity` and `rel_std` of the MEASURED $I_m/w_m$ (what the
  experimenter sees), `efficiency` of the true fields, `rel_std_true` of the true values, `time_s`; `fields` the true trap fields; `meta`
  (`variant`, `gain`, `open_loop_rel_std` (the measured spread of the starting hologram), `camera_seed`, `n_inner`).

## The method

One feedback iteration: measure the trap intensities $I_m$ of the current hologram with the camera, rescale the target, run `n_inner` inner
iterations from the current phase, repeat. The open-loop start is `n_start` iterations of M06 from the SR start (`start='gsw'`) or plain GS
(`start='gs'`); `init` replaces it (lines 76 to 86).

Variant `nogrette` (Nogrette et al. 2014). The inner iterations are plain GS (`rule_gs`). With $\rho_m = (I_m/w_m)/\langle I/w\rangle$ the measured
intensity relative to its target and the gain $G$, the source's rescaling $I'_m = \bar I/(1 - G(1 - I_m/\bar I))$ is read as a factor on the current
target intensity,

$$w_m^T \leftarrow w_m^T\,\frac{1}{1 - G(1-\rho_m)},$$

implemented on amplitudes as $a_m \leftarrow a_m\sqrt{1/(1 - G(1-\rho_m))}$ (line 93; $\rho$ floored at $10^{-3}$, line 91). A trap at $\rho = 1$
keeps its target; the multiplicative reading is DinHot's (it keeps the memory of earlier corrections and has the same fixed point $\rho = 1$);
UNVERIFIED against the paper's printed form.

Variant `kim` (Kim et al. 2019). The target amplitudes follow the square-root weights of the source, $T^{(j)}_m = \sqrt{\langle I\rangle/I_m}\;T^{(j-1)}_m$
(`a = a / sqrt(rho)`, line 99, full gain, `gain` unused). The first inner iteration displays $\arg\mathcal F^{-1}[T e^{i\psi}]$ with the focal phase $\psi$
frozen at that of the current hologram, with no weight correction on top (the camera factor already is the correction: a second one overshoots and
the loop diverges, 19 to 82 percent, measured); later inner iterations (`n_inner > 1`) add the weights $g$ of the phase-fixed WGS of M07, reset to 1 at
every step (lines 100 to 109).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `variant` | `nogrette` | `m12_closed_loop.py` line 54 | the first row of the ladder |
| `gain` $G$ | 0.7 | line 55 | Nogrette et al. 2014 (19 percent to 1.4 percent in 20 iterations) |
| `n_inner` | `None`: 1 for `nogrette`, 3 for `kim` (lines 64 and 65) | line 55 | measured: with more inner GS iterations the algorithm's own spread is re-introduced between measurements and the loop settles at 3 to 10 percent instead of 1 to 2 (20 iterations, $G = 0.7$); for `kim`, 3 inner iterations reach 0.5 to 0.8 percent from 22 to 24 against 3.9 to 5.6 with 1 (docstring) |
| `n_start` | 30 | line 55 | DinHot's choice: enough M06 iterations for the algorithm's own spread to be small, so that the open-loop spread is the camera's (docstring) |
| `start` | `gsw` | line 56 | the open-loop spread is then the camera's; `gs` adds the algorithm's |
| camera | `EmulatedCamera(seed=rng.next_u32(), gain_rms=0.19, rolloff=False)` | line 71 | Nogrette's 19 percent rms spread |

The port has the same defaults (`control.ts` lines 28 to 38).

## Complexity and lane

One feedback iteration: `n_inner` FFT-form GS iterations plus one camera evaluation (a focal field and a read at the trap bins). Lane `live`;
parity worst difference 6.8e-14 (T1 report D2). The case feedback driver (`data-pipeline/pipeline/stages/feedback.py`) is a separate loop that
applies the same Nogrette factor to the case's weight-aware method; it is not M12 and is the subject of the feedback curves of the section below.

## Acceptance criterion and gate

Ladder row: from a 19 percent rms open-loop spread, at most 2.1 percent in 20 iterations at gain 0.7. Gate
`tests/methods/control/test_m12_closed_loop.py`:

- `::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations`: seeds 1 and 2, a camera of gain error 0.19 with no noise, blur or roll-off,
  10x10 task, 20 feedback iterations at gain 0.7; the open-loop spread must be in 14 to 25 percent, the final measured spread at most 2.1 percent
  and below the open-loop spread over 8;
- `::test_nogrette_from_plain_gs_start_removes_algorithm_and_camera_error` (`start='gs'`, final at most 2.1 percent);
- `::test_kim_square_root_update_with_phase_fixing_three_steps`: a camera of gain error 0.22, `variant='kim'`, `Budget(3)`, final at most 1.8 percent;
- `::test_gain_one_converges_faster_than_gain_point_three`, `::test_noisy_blurred_camera_still_converges`, determinism and validation.

## Evaluation that confirms or refutes it

Confirmed if the measured spread falls from about 19 percent to at most 2.1 percent in 20 iterations (within a factor 1.5 of the published 1.4
percent) and the Kim variant reaches the published level in three steps; refuted if the loop settles above those bounds. Two findings are kept as
results, not as failures: more than one inner GS iteration degrades the Nogrette loop, and a second weight correction in the first Kim step
diverges.

## Measured result

Acceptance run of 2026-10-28 (E2 report D4 and D5), 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um):

| Variant | Open loop to closed loop (percent rms) | Published | Conditions |
|---|---|---|---|
| `nogrette`, $G = 0.7$, 20 iterations | 20.9 to 1.47 (seed 1); 20.1 to 1.08 (seed 2) | 19 to 1.4 | camera gain 0.19, no noise, no roll-off |
| `kim`, 3 steps | 24.3 to 4.54, 1.68, 0.77 (seed 1); 23.4 to 3.77, 1.06, 0.53 (seed 2) | 22 to 1.59 | camera gain 0.22 in the test |

From a plain GS start with camera noise $5\times10^{-5}$, blur and roll-off the spread falls below 4 percent, and gain 1.0 converges faster than 0.3.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own optics,
listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.812 (0.811 to 0.814) | 0.73 (0.689 to 0.752) | 18.1 (17.6 to 19.1) |
| C02 | 30 | 0.806 (0.805 to 0.806) | 0.553 (0.502 to 0.608) | 19.9 (19.2 to 20.8) |
| C03 | 30 | 0.809 (0.808 to 0.811) | 0.435 (0.362 to 0.479) | 19.8 (19.3 to 20.4) |
| C13 | 30 | 0.743 (0.743 to 0.744) | 0.452 (0.383 to 0.491) | 19.4 (18.6 to 20.2) |

These bake values are scored on the true trap fields: the relative standard deviation of 17 to 20 percent is the size of the default camera's own
gain error (0.19), which is what a loop that equalizes the camera readings leaves in the true intensities. The reduction is visible in the
measured-spread history of the run and in the case feedback curves (section below), not in this score. The M12 entry runs 30 feedback iterations in the manifests (for example C02) and `data-pipeline/pipeline/stages/infer.py` passes it no camera,
so the module default camera applies; both were read from those files, not re-run.

## Limits and failure modes

- The camera is an emulation: the loop shows the correction against stated errors, not an instrument.
- The update form of the source is read multiplicatively (UNVERIFIED).
- FFT form only: traps on bins, $z = 0$, no vortex (the cases C01, C02, C03, C12 and C13 are on bins by design, I1 report F8 and I2).
- Gain above 1 needs the floor `MIN_DENOMINATOR` of the case driver; M12 itself restricts $G$ to $(0, 1]$.

## References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913 (the open-loop start)

## The emulated camera against the published curves (formerly BS-6)

Withdrawn as a beyond-the-state-of-the-art claim on 2026-10-28: an emulator that reproduces published feedback curves is a validation tool for M12, not a method that answers the problem differently (the method-tiers rule). Its design and measurements stay here.

| Item | Value |
|---|---|
| Ladder row | none: formerly BS-6, tier beyond; withdrawn as a beyond claim, the emulator is part of this record (SDD, Beyond the state of the art) |
| Family, lane | beyond, feedback emulation, live (it is M12 on `core/camera.py`; the research record calls it B6) |
| Targets, dimensions | traps on FFT bins, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m12_closed_loop.py` (`run`, line 54) on `data-pipeline/pipeline/model/holo/core/camera.py` (`EmulatedCamera`, line 34); the case driver is `data-pipeline/pipeline/stages/feedback.py` |
| Gate | `tests/methods/control/test_m12_closed_loop.py` (the same file as M12) |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m12`, line 24) and `frontend/src/engine/holo/camera.ts` |
| Card | [M12](../../frameworks/M12_closed-loop-wgs.md) and [P06](../../frameworks/P06_emulated-camera.md) |
| Outcome | hypothesis confirmed one-sidedly (the emulated loop reaches the published level or better); the classification of the row as a method beyond the state of the art is open (see Limits) |

### Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** Feedback on the trap intensities has been published on hardware only; slmsuite needs hardware and no open emulator reproduces the published feedback curves. A simulated camera (the forward model, a
fixed per-trap gain error, additive noise, blur and the diffraction-efficiency roll-off), closed with the published update rules, reproduces the published curves in the browser: from an open-loop spread of 19
percent rms (Nogrette et al. 2014) the Nogrette update at gain 0.7 reaches the published 1.4 percent within a factor of 1.5 in 20 iterations, and from 22 percent (Kim et al. 2019) the phase-fixed square-root update
reaches the published 1.59 percent within a factor of 1.5 in three steps.

**The gap.** The feedback of Nogrette et al. (https://arxiv.org/abs/1402.5329), Kim et al. (https://doi.org/10.1364/OL.44.003178), Ebadi et al. (https://arxiv.org/abs/2012.12281) and Schroff et al.
(https://doi.org/10.1038/s41598-023-30296-6) is applied on hardware, and the open library slmsuite needs hardware (algorithms dossier D5.1 B6). No open emulator that reproduces the published curves exists.

### Problem it answers

Make the camera-in-the-loop methods testable and teachable without hardware, in the browser, with every error a stated parameter.

### Inputs and outputs

- The emulator: `EmulatedCamera(seed, gain_rms=0.05, noise_rms=0.0, blur_bins=0.0, rolloff=True, fill_factor=1.0)` (`camera.py`, class at line 34, constructor at line 37). `measure(e, setup, traps)` returns the measured trap
  intensities from the centred focal field `e` in the units of $I_m = |V_m|^2$.
- The loop: `m12_closed_loop.run` (see M12): inputs `setup`, `target` (traps on bins), `budget`, `rng`, `variant`, `gain`, `camera`, `n_inner`, `n_start`, `start`; output the `Result` with the measured-spread `history`
  and `meta['open_loop_rel_std']`.
- The case driver: `feedback.run(rec, ctx, mid, first)` returns `{"steps": [{step, rel_std_pct, efficiency}, ...]}` for the case's `feedback` block (gain, steps, camera parameters).

### The method

The camera (`camera.py` module docstring) measures, at the FFT bin nearest to each trap, the intensity map: optionally blurred by a Gaussian of `blur_bins` (normalized weighted average over $\pm\lceil 3\sigma\rceil$), multiplied by the
pixel-aperture roll-off (`rolloff`), multiplied by a fixed gain per trap id $\exp(s z - s^2/2)$ with $s$ = `gain_rms` and $z$ the first normal of a stream seeded from the seed and the trap id (log-normal with mean 1 and relative rms
about `gain_rms`, drawn once per trap id, independent of the order and the composition of the trap set), plus additive Gaussian noise of rms `noise_rms` from the camera's own stream, clipped at 0. Every error is a parameter with a
stated meaning; it is an emulation, not a model of a sensor.

The loops are the two published updates of M12 (see M12): `nogrette`,
$w_m^T \leftarrow w_m^T/(1 - G(1-\rho_m))$ with $\rho_m$ the measured intensity relative to its target (the multiplicative reading is DinHot's, UNVERIFIED against the paper's printed form), and `kim`,
$T^{(j)}_m = \sqrt{\langle I\rangle/I_m}\,T^{(j-1)}_m$ with the focal phase frozen. The case driver (`stages/feedback.py`) applies the Nogrette factor $1/(1 - G(1 - I_m/\mathrm{mean}(I)))$ to the target weights of the case's
weight-aware method and re-runs it from the previous phase for `STEP_ITERATIONS` = 10 iterations per step (line 23), reporting the measured spread (the relative standard deviation of the camera readings divided by the
target weights).

### Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| camera of `EmulatedCamera` | `gain_rms` 0.05, no noise, no blur, roll-off on | `camera.py` signature | engineering defaults |
| camera of M12 | `EmulatedCamera(seed=<first draw of rng>, gain_rms=0.19, rolloff=False)` | `m12_closed_loop.py` line 71 | Nogrette's 19 percent rms trap-depth spread |
| gain of M12 | 0.7 | `m12_closed_loop.py` line 55 | Nogrette et al. 2014 |
| case feedback blocks | C01: gain 0.7, 5 steps, camera 0.1; C02: 0.7, 20 steps, 0.19; C03: 0.9, 3 steps, 0.22; C13: 0.9, 5 steps, 0.22 | `data-pipeline/pipeline/cases/library.py` (the `feedback=` blocks, lines 172, 194, 214, 260) | C02 follows Nogrette (19 percent, gain 0.7, 20 iterations); C03 and C13 use the 22 percent of Kim et al. (the driver docstring names a Kim variant for C03) |

### Complexity and lane

One feedback iteration is `n_inner` FFT-form iterations plus one camera evaluation; the whole loop runs in the Web Worker (M12, lane `live`). The camera is a few array reads per trap.

### Acceptance criterion and gate

Ladder row: from the published open-loop spreads (19 percent rms, Nogrette 2014; 22 percent, Kim 2019), the emulated loop reaches the published curves within a factor of 1.5. Gate
`tests/methods/control/test_m12_closed_loop.py`:

- `::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations` (seeds 1 and 2): the camera gain error is 0.19, the open-loop spread in 14 to 25 percent, 20 iterations at gain 0.7; the final spread at most 2.1 percent
  (1.5 times the published 1.4) and below the open-loop spread divided by 8;
- `::test_kim_square_root_update_with_phase_fixing_three_steps` (seeds 1 and 2): the camera gain error is 0.22, `variant='kim'`, three steps; the final spread at most 1.8 percent (the upper end of the published
  1.59 plus or minus 0.18);
- `::test_nogrette_from_plain_gs_start_removes_algorithm_and_camera_error`, `::test_noisy_blurred_camera_still_converges`, `::test_default_camera_is_seeded_from_the_rng_and_deterministic`.

The camera itself is tested in `tests/engine/test_camera.py`.

### Evaluation that confirms or refutes it

Confirmed if the emulated loop ends at or below the published level from the published open-loop spread; refuted if it settles above 1.5 times the published value, or if reproducing it needs errors that no stated parameter
supplies. Both bounds of the test are one-sided (upper bounds): the emulated loop is allowed to do better than the published curve.

### Measured result

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

### Limits and failure modes

- Reproducing a published number by choosing the camera's error is a tuning of the emulator, not a validation of a real device: the real errors come from the SLM and the optics. The emulator is a teaching and test tool, and
  the result shows that the loop works against these stated errors (the research record's own risk statement).
- Classification, decided: the method tiers rule says a validation protocol, a calibration or a benchmark design is not by itself a method beyond the state of the art. The
  emulator reproduces published curves, so it is a validation tool of M12 and the claim BS-6 was withdrawn (decision of 2026-10-28, recorded in the SDD's Beyond the state of the art).
- Only the end points of the two published curves are compared; the conventional-WGS clause of the research record is not run.
- The Nogrette update is read multiplicatively (UNVERIFIED); the printed form was not confirmed.
- Noise, blur and roll-off make the result worse than the ideal camera; the published experiments' own noise floor is not modelled.
- A measured hardware loop (a real SLM and a camera) is a documented frontier of the product, not part of this build.

### References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
