# M12, Closed-loop weighted GS on an emulated camera

| Item | Value |
|---|---|
| Family | feedback control |
| Lane | live |
| Targets, dimensions | traps, 2D (FFT form: traps on bins, $z = 0$, no vortex) |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/control/m12_closed_loop.py`, `SPEC` line 48, `run` line 54 |
| Anchor | Nogrette et al., Phys. Rev. X 4, 021034 (2014); Kim et al. 2019 |

## Purpose

An open-loop hologram leaves the traps with an unequal depth because the optics and the camera disagree with the model. Measuring
the trap intensities and rescaling the target iteratively brings them to the percent level. DinHot runs the loop on an emulated
camera ([P06](P06_emulated-camera.md)), so the feedback curve is reproducible in the browser without hardware.

## Equations

One feedback iteration: measure the trap intensities $I_m$ of the current hologram, rescale the target, run `n_inner` inner iterations from
the current phase, repeat. `Budget.iterations` counts feedback iterations.

Variant `nogrette` (https://arxiv.org/abs/1402.5329 ): inner iterations are plain GS; with $\rho_m = (I_m/w_m)/\langle I/w\rangle$ the measured
intensity relative to its target and gain $G$,

$$I'_m = \frac{\bar I}{1 - G\,(1 - I_m/\bar I)} \quad\Longrightarrow\quad w^T_m \leftarrow w^T_m\,\frac{1}{1 - G(1-\rho_m)}$$

The target intensity is multiplied by the factor, so a trap at $\rho = 1$ keeps its target. The multiplicative reading is DinHot's (it keeps the
memory of earlier corrections and has the same fixed point $\rho = 1$); the printed form of the update was not confirmed (UNVERIFIED).

Variant `kim` (https://arxiv.org/abs/1903.09286 ): $T^{(j)}_m = \sqrt{\langle I\rangle/I_m}\;T^{(j-1)}_m$ (square-root weights, full gain). The first inner
iteration displays $\arg \mathcal{F}^{-1}[T e^{i\psi}]$ with the focal phase $\psi$ frozen at that of the current hologram and no weight correction on
top (the camera factor already is the correction; a second one overshoots and the loop diverges, measured); later inner iterations add the weights
of the phase-fixed WGS of [M07](M07_phase-fixed-wgs.md), reset to 1 at every step. `gain` is not used.

## Implementation

Defaults (`run`, line 54): `variant = "nogrette"`, `gain = 0.7`, `n_inner = None` (1 for `nogrette`, 3 for `kim`), `n_start = 30`, `start = "gsw"`. The
camera default is `EmulatedCamera(seed=<first draw of rng>, gain_rms=0.19, rolloff=False)`. Open-loop start: 30 iterations of M06 from the SR start
(`start = "gs"` runs plain GS instead; `init` overrides). History per feedback iteration: `uniformity` and `rel_std` of the MEASURED $I_m/w_m$ (what the
experimenter sees), `efficiency` of the true fields, `rel_std_true` of the true values; `meta["open_loop_rel_std"]` is the measured spread of
the starting hologram.

Measured design findings, stated in the module docstring: with more than one inner GS iteration for `nogrette`, the algorithm's own spread is
re-introduced between measurements and the loop settles at 3 to 10 percent instead of 1 to 2 (20 iterations, $G = 0.7$); for `kim`, 3 inner iterations
reach 0.5 to 0.8 percent from 22 to 24 against 3.9 to 5.6 with 1.

## Acceptance criterion and test

From a 19 percent rms open-loop spread, at most 2.1 percent in 20 iterations at gain 0.7:
`tests/methods/control/test_m12_closed_loop.py::test_nogrette_19_percent_to_at_most_2_1_percent_in_20_iterations`; the Kim variant in three steps:
`::test_kim_square_root_update_with_phase_fixing_three_steps`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Variant | Open loop to closed loop (percent rms) | Published | Conditions |
|---|---|---|---|
| `nogrette`, $G = 0.7$, 20 iterations | 20.9 to 1.47 (seed 1); 20.1 to 1.08 (seed 2) | 19 to 1.4 | camera gain 0.19, no noise, no roll-off, 10 by 10 task, 256 by 256 padded 2 |
| `kim`, 3 steps | 24.3 to 4.54, 1.68, 0.77; 23.4 to 3.77, 1.06, 0.53 | 22 to 1.59 | same |

From a plain GS start with camera noise 5e-5, blur and roll-off the spread falls below 4 percent, and gain 1.0 converges faster than 0.3.

## Limits

- The camera is an emulation; the result shows the loop works against stated errors, not against an instrument.
- The update form of the source is read multiplicatively (UNVERIFIED).

## References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
