# BS-1: Device-aware conjugate-gradient refinement (engine id B1; named device-aware weighted GS until 0.02.003)

| Item | Value |
|---|---|
| Ladder row | BS-1, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, device-aware, baked |
| Targets, dimensions | traps, 2D (`SPEC.dims` is `(2,)`) |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b1_device_wgs.py` (`SPEC` line 45, `run` line 52) |
| Gate | `tests/methods/beyond/test_b1_device_wgs.py` |
| Live port | none (lane `baked`; `getMethod('B1')` raises `NotLive`) |
| Card | [B1](../../frameworks/B1_device-aware-wgs.md) |
| Outcome (0.02.004) | negative result against Schroff et al. 2023: through the same warm start, device model and conjugate gradient, their normalized-error loss gives 0.031 percent against 0.030 percent for the efficiency-level loss on the crosstalk device and 0.222 against 0.242 percent on the 4-bit device (five seeds, overlapping ranges), so the method's own elements add nothing measurable, and the weight update (off by default since 0.02.004) makes the spread 7 times higher; the gain belongs to the device model in the loop (a geometric-mean factor of 201.3 over M07 on the crosstalk device, 1.0 without the model); the ladder criterion against M07 is met (at least two times lower, efficiency at most 10 percent lower), in the benchmark on the C08 device at 100 iterations both thresholds hold on 4 of 6 geometries, and a hologram takes 34 s on the crosstalk task and 779 s to 1940 s on the benchmark geometries against 0.37 s to 7.4 s for M07 |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** Putting the SLM's pixel crosstalk and quantizer inside the loop of a conjugate-gradient refinement that starts from weighted GS, for trap arrays, with a few conjugate-gradient
steps on a device-aware loss, makes the traps equal on the device and not only in the ideal model: on the crosstalk device the relative standard deviation of the trap intensities is
at least two times below that of phase-fixed WGS (M07), at an efficiency at most 10 percent lower.

**The gap.** Schroff et al. 2023 (https://doi.org/10.1038/s41598-023-30296-6) put the crosstalk model into conjugate gradient on shaped potentials and a Gaussian spot array (their Fig. 5c; 10 minutes per feedback protocol, no WGS
comparison); Persson, Engstrom and Goksor 2012 (Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334) modify a hologram algorithm for crosstalk (known here through its abstract only); Kim et al. 2019 (https://doi.org/10.1364/OL.44.003178) and Ebadi et al. 2021 (https://arxiv.org/abs/2012.12281) use no device model in the solver and rely on
camera feedback (the gap study, algorithms dossier D5.1 B1). The proposal combines the device model of Schroff et al. with a weighted GS start (and, as an option, the weights of Di Leonardo et al. 2007
(https://doi.org/10.1364/OE.15.001913)), applied to trap arrays, and it is run against Schroff et al.'s own loss (`loss='normalized-error'`, the update of 2026-11-14); it is a method that answers the problem differently from M07 (solver aware of the
device) and not a validation protocol.

**What is and is not new (read in full, update of 2026-11-15).** Schroff et al. already put a pixel-crosstalk model (3 by 3 upsampling, a fitted kernel) inside a conjugate-gradient minimization of a normalized intensity error, with automatic differentiation and camera feedback, and make light potentials with it, among them a Gaussian spot array (their Fig. 5c). The idea of a crosstalk model inside a conjugate-gradient refinement of a trap array is theirs, not DinHot's. The method is a transposition of that approach to point-trap arrays, with three elements of its own (the efficiency-level loss, the weight update, the best-iterate safeguard), and the paper measures whether they add anything: they do not (the update at the end of this record).

## Problem it answers

Hologram quality on a pixelated SLM with pixel crosstalk, 4-bit-class phase and a fill factor, where the ideal-model solvers equalize the model and not the device.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`, `b1_device_wgs.py` line 56), `budget` (`iterations` is the number of outer iterations), `rng`,
  optional `init` (overrides the warm start), `device` (a `core.device.Device`; with `None` the ideal model), `steps`, `warm`, `weights` (default False), `loss` (`'efficiency-level'`, the default, or `'normalized-error'`), `steepness`. Traps must be on FFT bins with $z = 0$ and no vortex when a
  device is given (the traps are read at the nearest bin). `steps < 1` or `warm < 0` raises a `ValueError`.
- Output: `Result` with `phi` in $[0, 2\pi)$, one `history` entry per outer iteration (with `loss`), `fields` the trap fields on the device, `meta` (`steps`, `warm`, `evaluations`, `weights`,
  `weight_update`, `loss`, `device_aware`).

## The method

Start from weighted GS. With the option `weights=True` keep the weights of Di Leonardo et al. 2007, Eq. (18), $w_m \leftarrow w_m\langle r\rangle/r_m$ with $r_m = |V_m|/a_m$ the trap amplitude relative to its design amplitude, measured on the
device's focal field (off by default, see the update of 2026-11-14). Replace the projection $\phi_j = \arg\sum_m c_m e^{+i\Delta_j^m}$ of the phase update by $K$ conjugate-gradient steps on the device-aware loss

$$L(\phi) = \frac{\sum_m\big(|V_m(\phi)|^2 - T_m\big)^2}{\sum_m T_m^2},\qquad T_m = \eta\,\frac{(w_m a_m)^2}{\sum_k (w_k a_k)^2},\qquad \eta = \sum_m |V_m|^2,$$

where $V = \mathrm{Op}(\phi)$ runs through the straight-through quantizer, the crosstalk operator $K * U$ (3 by 3 upsampling, circular convolution with the Schroff kernel), the FFT of the upsampled
grid and the pixel-aperture envelope. The gradient is the closed form of `FocalForward.adjoint` (the adjoint of the crosstalk operator is the convolution with the reversed kernel followed by the sum
over each 3 by 3 block): no autodiff. The target level is the current efficiency $\eta$, so the steps flatten the traps without trading efficiency away; with the weights on they supply an integral feedback
that the few steps per iteration lack, and the ablation shows that without them the spread is lower (update of 2026-11-14). Fletcher-Reeves CG with a strong-Wolfe line search restarts at every outer iteration, because the target is set again at each of them.

In the code, per outer iteration (`b1_device_wgs.py` lines 77 to 86): the trap fields on the device, the weight update, `cost.target = sum|v|^2 * (w a)^2 / sum (w a)^2`, then
`C.cg_minimize(cost.value_grad, phi, steps)`. The start is `warm` iterations of ideal-model weighted GS from the SR superposition (lines 64 to 67), or `init`.

Safeguard (added 2026-10-30). The weight update is an integrator, and three CG steps per outer iteration may not follow it on a device whose trap response is quantized and
blurred. On the benchmark's square lattice on the C08 device one seed in two ran away inside B1's own model: the loss rose from 0.044 to 0.53 between outer iterations 2 and 4, the
weights spread to a max-to-min ratio of about 1000 and the efficiency fell from 0.50 to 0.03. B1 now returns its best iterate, the warm start included: the phase of lowest relative standard
deviation on its device model among the iterates that keep at least `EFFICIENCY_FLOOR` (0.9) of the warm start's efficiency, the ten percent of the ladder criterion. The history still holds
every iterate, and `meta` names the returned one (`best_iteration`), the floor and the start's spread and efficiency. A run that converges returns its last iterate or one of its tail
(`test_a_converging_run_returns_an_iterate_of_its_tail`); a run that winds up returns an admissible iterate no worse than its start
(`test_adversarial_a_run_that_winds_up_returns_its_best_admissible_iterate`).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `weights` | False (the weight update is an option) | `b1_device_wgs.py` | the ablation of the paper, update of 2026-11-14 |
| `loss` | `'efficiency-level'` | `b1_device_wgs.py` | `'normalized-error'` is the loss of Schroff et al. 2023, eq (3) |
| `steps` | 3 CG steps per outer iteration | `b1_device_wgs.py` line 47 | DinHot's choice (a few steps; the weights give the integral feedback) |
| `warm` | 12 ideal-model GSW iterations | line 48 | Kim's $N$ = 12 (the number of WGS iterations before the phase freeze) |
| `DEFAULT_OUTER` | 4 | line 49 | the budget of the acceptance test (`Budget(B1.DEFAULT_OUTER)`); `run` itself takes the number of outer iterations from `budget.iterations` and does not read the constant |
| initial efficiency level of `TrapCost` | 0.9 | line 68 | overwritten at each iteration by the current efficiency (line 81), so it has no effect |
| `EFFICIENCY_FLOOR` | 0.9 of the warm start's efficiency | `b1_device_wgs.py` | the ladder criterion's bound (efficiency at most 10 percent lower): an iterate below it is never returned |

## Complexity and lane

Per CG step one forward and one adjoint evaluation of the upsampled model, about 3 by 3 times the pixels of the plain FFT (2.4 times cheaper with the pruned transform, M13); the source's
crosstalk model alone makes a hologram about 6 times slower. The research record asked for a time per iteration of at most three times the baseline; the ratio was not measured (not
established). Lane `baked` (`SPEC`, line 45). The acceptance test takes about 31 s on the development machine (E3 report).

## Acceptance criterion and gate

Ladder row: on the crosstalk device, relative standard deviation at least two times below M07, efficiency at most 10 percent lower. Gate
`tests/methods/beyond/test_b1_device_wgs.py::test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device`: the 10x10 task on 256 by 256 padded 2; the device
`Device(crosstalk=(1.24, 1.80), upsample=3)` (crosstalk only: no quantization, fill factor 1, no flicker); the baseline is the phase-fixed WGS of the in-test family (`n_fix = 12`) at 30 and at 100
iterations, hologram evaluated on the device, and the criterion is taken against the strongest of the two (the lowest spread and the highest efficiency); B1 with `Budget(4)` outer iterations,
seed 1; B1's spread must be at most half the baseline's and its efficiency at least 0.9 of the baseline's. Other tests: a small grid is flattened through the quantizer and the crosstalk, the ideal
model without a device, a shaped field is refused, determinism.

## Evaluation that confirms or refutes it

The hypothesis is refuted if, on the crosstalk device, B1's spread is not at least half of M07's, or if it gets there by losing more than 10 percent of the efficiency; it is also refuted in spirit
if more iterations of the plain solver close the gap (an ideal-model solver that keeps iterating would not need the device model). The test controls for the second: the baseline at 100 iterations is
no better than at 30. The research record's fuller criterion (also G6, equal or lower spread after 3 camera-feedback steps, time per iteration at most 3 times) is not part of the ladder gate and
was not measured.

## Measured result

All values are those of the 0.02.004 generation, read from the committed data files of `manuscripts/device-aware-flicker-bounded/data/` (`beyond_numbers.tex`, `tab_schroff.tex`, `tab_abl_b1_geo.tex`) and of `manuscripts/holographic-trap-studio/data/studio_numbers.tex`. The refinement runs with the weight update off (the default), 10x10 task, 256 by 256 padded 2, five seeds, simulated, against the phase-fixed WGS of the ladder (M07).

| Task | Method | Factor over M07, geometric mean (95 percent interval) | Efficiency ratio | Seconds per hologram |
|---|---|---|---|---|
| crosstalk device | device-aware refinement (default) | 201.3 (132.9 to 304.9) | 0.999 | 34 |
| crosstalk device | normalized-error loss of Schroff et al. 2023 | 159.9 (107 to 239.1) | 0.999 | 34 |
| crosstalk device | with the weight update | 24.4 (17.5 to 34.1) | 0.995 | n/a |
| crosstalk device | without the device model | 1.0 | 1.000 | n/a |
| 4-bit device | device-aware refinement (default) | 23.5 (18.6 to 29.6) | 0.997 | 59 |
| 4-bit device | normalized-error loss of Schroff et al. 2023 | 26.1 (20.2 to 33.9) | 0.997 | 58 |
| 4-bit device | with the weight update | 7.4 (5.7 to 9.8) | 0.990 | n/a |

Sources per value: `ablBFullFac`, `ablBFullFacLo`, `ablBFullFacHi`, `ablBFullEff` (default, crosstalk); `schroffXFac`, `schroffXFacLo`, `schroffXFacHi`, `schroffXEffRatio` (Schroff, crosstalk); `ablBWeightsFac`, `ablBWeightsFacLo`, `ablBWeightsFacHi`, `ablBWeightsEff`; `ablBNoModelFac`; `ablBFFullFac` and its interval and `ablBFFullEff`; `schroffFFac` and its interval and `schroffFEffRatio`; `ablBFWeightsFac` and its interval and `ablBFWeightsEff`; `schroffXSeconds`, `secBFMedian`, `schroffFSeconds` (all in `beyond_numbers.tex`).

Spread, median (range) in percent: crosstalk device 0.030 (0.016 to 0.032) for the default and 0.031 (0.021 to 0.049) for the normalized-error loss; 4-bit device 0.242 (0.202 to 0.335) and 0.222 (0.172 to 0.258). The efficiency-level loss has the lower spread on 4 of 5 seeds on the crosstalk device and on 2 of 5 on the 4-bit device (`schroffXDefaultBeats`, `schroffFBeatsDefault`); the ranges overlap and the two losses are indistinguishable at these seeds. On the 4-bit device the normalized-error loss has the lower median.

Outcome: the ladder criterion (a comparison with M07) is met by a wide margin on the crosstalk device and on the 4-bit device. Against the closest published method the result is negative: Schroff et al. 2023 already put a pixel-crosstalk model inside a conjugate-gradient refinement and make a spot array with it (their Fig. 5c), and the method's own elements (the efficiency-level loss, the weight update, the best-iterate safeguard) add nothing measurable over their loss. The gain belongs to the device model in the loop.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C08 only, an 8 by 8 array on a device with 4-bit phase, crosstalk (sigma 1.24, q 1.80), fill factor 0.85 and flicker 0.05 rad, scored on the device, with its optics in `data/derived/manifests/C08_device_limited.json`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C08 | 30 | 0.655 (0.651 to 0.662) | 0.862 (0.847 to 0.887) | 6.5 (5.91 to 7.04) |

On C08 the ratio of the means of the relative standard deviation of M07 over B1 is 2.0 (per seed 1.906, 1.997 and 2.228: `bakeCeightRatioThree` and `bakeCeightSeedRatios` in `beyond_numbers.tex`, so two times or more on one of three seeds) at 0.979 of M07's efficiency (`bakeCeightEffRatio`). That device has the 4-bit quantizer and the flicker that the optimizer models only as straight-through or drops, and it is the hardest of the three.

Benchmark (`data/derived/benchmark/results.json`, the studio's 0.02.004 run; the C08 device at 100 iterations with the default parameters, 2 seeds per cell of B1, `benchOneDevSeeds`): the factors over M07 are G1 square 10 x 10 1.90, G2 ring of 36 traps 2.04, G3 random 100 traps 4.82, G4 quasi-periodic 119 1.05, G6a 2.15 and G6b 2.08, a median of 2.06 (1.05 to 4.82) at a median efficiency ratio of 0.969 (`benchOneDevList`, `benchOneDevMed`, `benchOneDevMin`, `benchOneDevMax`, `benchOneDevEff`). Both thresholds hold on 4 of 6 geometries (G2, G3, G6a, G6b: `benchOneDevPass` of `benchOneDevN`, `benchOnePassList` in `studio_numbers.tex`), not on the square lattice or the quasi-periodic set. At an equal wall-clock time of 1 s the refinement reads as better on 3 of 6 geometries and ties on 3 (`benchOneDevTimeProposed`, `benchOneDevTimeTie`). Time per hologram at 100 iterations: 779 s (G1), 810 s (G2), 822 s (G3), 832 s (G4), 1939 s (G6a) and 1940 s (G6b) against 2.728, 0.367, 0.616, 0.724, 7.444 and 5.415 s for M07 (`benchSecGeo*`). On the ideal device the spreads of B1 and of M07 are both below the resolution of the file on most geometries, which is a tie and not a gain.

Geometry ablation of the loss (`tab_abl_b1_geo.tex`, five seeds, the weight update on against the default against the normalized-error loss, spread in percent): G1 27.14, 13.64 and 14.03; G2 8.03, 8.46 and 8.55; G3 4.43, 4.27 and 4.14; G4 86.01 for all three. The weight update helps on the ring and hurts on the square lattice, which is why it stays available as an option and is off by default.

## Limits and failure modes

- The unit of $k$ in the crosstalk kernel is DinHot's reading (the model is relative to the model of the device, not to a measured instrument; see M13 and the device model P02).
- Five seeds in the measurement of the claim and one in the acceptance test; the benchmark's B1 cells on the C08 device hold 2 seeds, within the wall-clock bound of a group.
- Baked: a step works on about nine times the pixels of the plain FFT (3 by 3 upsampling); the cost of a hologram is above the live budget.
- Traps must be on bins with $z = 0$ and no vortex on a device; a shaped target is refused.
- Flicker is random and is dropped from the optimization model; it is scored but not modelled.
- The crosstalk parameters are device specific (the source's calibration took 30 minutes plus 2 hours); the effect size on a typical 8 micrometre pitch device is unknown.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
- Persson, Engstrom and Goksor 2012, Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334
- Kim, Keesling, Omran, Levine, Bernien, Greiner, Lukin and Englund 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913

## History before 0.02.004

The measurements of 2026-10-29 and 2026-10-30 (the corrected M07 and slmsuite's WGS-Kim as references, the second re-measurement after M06 projected its start's field unweighted and the GS family of the beyond methods took the ladder methods' own rules, the benchmark on its first five geometries) were taken with the weight update on, which is not the default since 0.02.004; their figures are superseded by the measured result above and are kept in the git history of this file. What they established and still holds: the crosstalk of the device, not the first-update defect of the old M07, sets the baseline's floor near 5 percent; B1 returns its best iterate that keeps 0.9 of its warm start's efficiency (The method, Safeguard; a run on the C08 square lattice wound up on one seed in two before it), and the acceptance spreads do not change with it to four digits on the crosstalk device.

## Update of 2026-11-14 (0.02.004): weights off by default, the normalized-error loss, the name

An independent review of the device-aware paper found that its own ablation refutes the weights, and that the closest published method was not run
(`wip/dinhot/msq-papers-2026-11-10.md`, findings DA-1 and DA-3). The method is therefore redefined and renamed (the id B1 stays):

- **Name.** "Device-aware conjugate-gradient refinement" (Spanish: "Refinamiento por gradiente conjugado con modelo del dispositivo"). What distinguishes it from the ladder's weighted GS is the conjugate-gradient refinement through the device model, not the weights.
- **Weights off by default.** `weights` defaults to False. The ablation (`manuscripts/device-aware-flicker-bounded/data/tab_abl_b1.tex`, five seeds, crosstalk device, 10 x 10 task): median spread 0.030 percent without the update against 0.205 percent with it, 7 times lower, at an efficiency ratio of 0.999 against 0.995;
  on the 4-bit device (`beyond_numbers.tex`, five seeds) 0.242 against 0.729 percent, 3 times lower. On the benchmark lattices the result is mixed (the C08 device at 10 iterations, median over three seeds: square lattice 14 against 29 percent at an efficiency of 0.56 against 0.60; ring of 36: 8.9 against 7.8; the random and quasi-periodic sets unchanged), so `weights=True` stays available and reproduces the 0.02.003 run exactly.
  The measured result above is the 0.02.004 re-measurement with the new default.
- **The closest published method as a loss option.** `loss='normalized-error'` replaces the efficiency-level loss by the normalized-error cost of Schroff et al. 2023 (Sci. Rep. 13, 3252, eq (3), p. 3), $C = s\sum_{S}(\tilde T - \tilde I)^2$ with $\tilde T = T/\sum_S T$ and $\tilde I = I/\sum_S I$, on the trap intensities through the same device model;
  the warm start, the conjugate-gradient optimizer, the outer iterations and the best-iterate safeguard are B1's own, so the comparison isolates the loss. The gradient is $\partial C/\partial I_k = (2s/P)(\sum_m d_m \tilde I_m - d_k)$ with $d = \tilde T - \tilde I$ and $P = \sum_m I_m$, through the adjoint of the device model, checked against finite differences.
  The steepness $s$ is `1 / sum(T~^2)` by default (so that $C$ is the relative squared error); Schroff et al.'s constant `s = 1e12` (Methods, p. 7) is a pixel-grid scale and only rescales $C$.
- **Tests.** `test_weights_true_reproduces_the_run_recorded_before_the_default_changed`, `test_the_default_equals_the_weights_false_run_recorded_before_the_default_changed`, `test_the_weight_update_is_an_option_and_off_by_default`, `test_spec_name_is_the_device_aware_conjugate_gradient_refinement` (MD-023); `test_normalized_error_value_is_schroff_eq3_on_the_trap_intensities`, `test_normalized_error_gradient_matches_finite_differences`, `test_normalized_error_runs_the_same_warm_start_and_safeguard_and_differs_only_by_the_loss`, `test_normalized_error_honours_the_deadline_and_counts_its_work` (MD-024).

## Update of 2026-11-15 (0.02.004): reported as a negative result against Schroff et al.

Read in full, Schroff et al. 2023 already put a pixel-crosstalk model inside a conjugate-gradient refinement and make a spot array with it (their Fig. 5c). Through the same warm start, device model, conjugate-gradient optimizer and safeguard, the method's own elements add nothing measurable over their normalized-error loss. The numbers are those of `manuscripts/device-aware-flicker-bounded/data/beyond_numbers.tex`, `tab_schroff.tex` and `tab_abl_b1_geo.tex` (5 seeds each, simulated):

| Quantity | Efficiency-level loss (default) | Normalized-error loss of Schroff et al. | Conditions |
|---|---|---|---|
| Spread, median (range), crosstalk device | 0.030 (0.016 to 0.032) | 0.031 (0.021 to 0.049) | 10 by 10 task; the ranges overlap |
| Factor over M07, geometric mean (95 percent interval) | 201.3 (132.9 to 304.9) | 159.9 (107.0 to 239.1) | efficiency ratio 0.999 in both |
| Spread, median (range), 4-bit device | 0.242 (0.202 to 0.335) | 0.222 (0.172 to 0.258) | the normalized-error loss has the lower median |
| Seconds per hologram, median | 34 (crosstalk), 59 (full) | 34 and 58 | one CPU |

Reading: the efficiency-level loss adds nothing measurable; the best-iterate safeguard did not act on these seeds; the weight update raises the spread from 0.030 to 0.205 percent on the crosstalk device (7 times) and from 0.242 to 0.729 on the 4-bit device (3 times). The gain belongs to the device model in the loop (without it the spread returns to 5.153 percent against 5.21 for M07: `ablBNoModelSig`, `sigmaMsevenHundred`). On the benchmark's C08 device at 100 iterations (2 seeds per cell) the factors over M07 are G1 1.90, G2 2.04, G3 4.82, G4 1.05, G6a 2.15 and G6b 2.08: both thresholds hold on the ring, the random set and the two large sets, not on the square lattice or the quasi-periodic set; at an equal wall-clock time of 1 s the refinement reads as better on 3 of 6 geometries and ties on 3 (`benchOneDevTimeProposed`, `benchOneDevTimeTie`). Time per hologram: 779 s to 1940 s on the benchmark geometries at 100 iterations against 0.37 s to 7.4 s for M07 (779 s against 2.728 s on G1; `benchSecGeo*` in `beyond_numbers.tex`). What the work keeps as its own: the transposition to point-trap arrays, the closed-form gradient of the point-trap loss, and the measurement that isolates the loss, the weights, the safeguard and the device model.
