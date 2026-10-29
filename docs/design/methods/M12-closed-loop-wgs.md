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
(the measured hardware loop is a documented frontier of the product). BS-6 is the claim built on this module and this camera.

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
applies the same Nogrette factor to the case's weight-aware method; it is not M12 and is the subject of BS-6.

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
measured-spread history of the run and in the case feedback curves (BS-6), not in this score. The M12 entry runs 30 feedback iterations in the manifests (for example C02) and `data-pipeline/pipeline/stages/infer.py` passes it no camera,
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
