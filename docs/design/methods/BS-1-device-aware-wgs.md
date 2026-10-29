# BS-1: Device-aware weighted GS (engine id B1)

| Item | Value |
|---|---|
| Ladder row | BS-1, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, device-aware, baked |
| Targets, dimensions | traps, 2D (`SPEC.dims` is `(2,)`) |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b1_device_wgs.py` (`SPEC` line 45, `run` line 52) |
| Gate | `tests/methods/beyond/test_b1_device_wgs.py` |
| Live port | none (lane `baked`; `getMethod('B1')` raises `NotLive`) |
| Card | [B1](../../frameworks/B1_device-aware-wgs.md) |
| Outcome | hypothesis confirmed on the ladder criterion (spread 49 times below M07 at 0.997 of its efficiency) |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** Putting the SLM's pixel crosstalk and quantizer inside the loop of the weighted GS for trap arrays, with the phase update replaced by a few conjugate-gradient
steps on a device-aware loss, makes the traps equal on the device and not only in the ideal model: on the crosstalk device the relative standard deviation of the trap intensities is
at least two times below that of phase-fixed WGS (M07), at an efficiency at most 10 percent lower.

**The gap.** Schroff et al. 2023 (https://doi.org/10.1038/s41598-023-30296-6) put the crosstalk model into conjugate gradient on shaped potentials (10 minutes per hologram, no WGS
comparison); Persson, Engstrom and Goksor 2012 (Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334) convolve the phase inside a weighted GS but
replace amplitudes only; Kim et al. 2019 (https://doi.org/10.1364/OL.44.003178) and Ebadi et al. 2021 (https://arxiv.org/abs/2012.12281) use no device model in the solver and rely on
camera feedback (the gap study, algorithms dossier D5.1 B1). The proposal is a combination of two published pieces, the weights of Di Leonardo et al. 2007
(https://doi.org/10.1364/OE.15.001913) and the device model of Schroff et al., applied to trap arrays; it is a method that answers the problem differently from M07 (solver aware of the
device) and not a validation protocol.

## Problem it answers

Hologram quality on a pixelated SLM with pixel crosstalk, 4-bit-class phase and a fill factor, where the ideal-model solvers equalize the model and not the device.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`, `b1_device_wgs.py` line 56), `budget` (`iterations` is the number of outer iterations), `rng`,
  optional `init` (overrides the warm start), `device` (a `core.device.Device`; with `None` the ideal model), `steps`, `warm`. Traps must be on FFT bins with $z = 0$ and no vortex when a
  device is given (the traps are read at the nearest bin). `steps < 1` or `warm < 0` raises a `ValueError`.
- Output: `Result` with `phi` in $[0, 2\pi)$, one `history` entry per outer iteration (with `loss`), `fields` the trap fields on the device, `meta` (`steps`, `warm`, `evaluations`, `weights`,
  `device_aware`).

## The method

Keep the weights of Di Leonardo et al. 2007, Eq. (18), $w_m \leftarrow w_m\langle r\rangle/r_m$ with $r_m = |V_m|/a_m$ the trap amplitude relative to its design amplitude, measured on the
device's focal field. Replace the projection $\phi_j = \arg\sum_m c_m e^{+i\Delta_j^m}$ of the phase update by $K$ conjugate-gradient steps on the device-aware loss

$$L(\phi) = \frac{\sum_m\big(|V_m(\phi)|^2 - T_m\big)^2}{\sum_m T_m^2},\qquad T_m = \eta\,\frac{(w_m a_m)^2}{\sum_k (w_k a_k)^2},\qquad \eta = \sum_m |V_m|^2,$$

where $V = \mathrm{Op}(\phi)$ runs through the straight-through quantizer, the crosstalk operator $K * U$ (3 by 3 upsampling, circular convolution with the Schroff kernel), the FFT of the upsampled
grid and the pixel-aperture envelope. The gradient is the closed form of `FocalForward.adjoint` (the adjoint of the crosstalk operator is the convolution with the reversed kernel followed by the sum
over each 3 by 3 block): no autodiff. The target level is the current efficiency $\eta$, so the steps flatten the traps without trading efficiency away; the weights supply the integral feedback
that the few steps per iteration lack (a one-shot fit would need many more steps). Fletcher-Reeves CG with a strong-Wolfe line search restarts at every outer iteration, because the target changes with the weights.

In the code, per outer iteration (`b1_device_wgs.py` lines 77 to 86): the trap fields on the device, the weight update, `cost.target = sum|v|^2 * (w a)^2 / sum (w a)^2`, then
`C.cg_minimize(cost.value_grad, phi, steps)`. The start is `warm` iterations of ideal-model weighted GS from the SR superposition (lines 64 to 67), or `init`.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `steps` | 3 CG steps per outer iteration | `b1_device_wgs.py` line 47 | DinHot's choice (a few steps; the weights give the integral feedback) |
| `warm` | 12 ideal-model GSW iterations | line 48 | Kim's $N$ = 12 (the number of WGS iterations before the phase freeze) |
| `DEFAULT_OUTER` | 4 | line 49 | the budget of the acceptance test (`Budget(B1.DEFAULT_OUTER)`); `run` itself takes the number of outer iterations from `budget.iterations` and does not read the constant |
| initial efficiency level of `TrapCost` | 0.9 | line 68 | overwritten at each iteration by the current efficiency (line 81), so it has no effect |

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

Acceptance run of 2026-10-28 (E3 report D3 and D5), 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), 1 seed:

| Quantity | B1 | M07 on the ideal model, scored on the device |
|---|---|---|
| Relative standard deviation (percent) | 0.091 | 4.454 (the method module, E2) and 4.504 (the in-test copy) |
| Efficiency | 0.7423 | 0.7447 and 0.7459 |
| Ratio | 49 times lower spread, 0.997 of the efficiency | |

More iterations do not help the baseline (spread 4.504 with 30 iterations and 4.525 with 100). Outcome: confirmed, by a wide margin, on this device and this seed.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C08 only, an 8 by 8 array on a device with 4-bit phase, crosstalk
(sigma 1.24, q 1.80), fill factor 0.85 and flicker 0.05 rad, scored on the device, with its optics in `data/derived/manifests/C08_device_limited.json`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C08 | 30 | 0.65 (0.639 to 0.662) | 0.872 (0.841 to 0.904) | 6.05 (5.49 to 6.71) |

On C08 the mean relative standard deviation is 6.05 percent for B1 against 13.2 for M07 (ratio 2.2, computed from the committed file) at 0.96 of M07's efficiency (0.650 against 0.676):
the factor of two holds on the harder device, which has the 4-bit quantizer and the flicker that the optimizer models only as straight-through or drops; the factor is 2.2 there against 49 in the acceptance test.

## Limits and failure modes

- UNVERIFIED: the unit of $k$ in the crosstalk kernel (the model is relative to the model of the device, not to a measured instrument; see M13 and the device model P02).
- One seed in the acceptance test; the benchmark repeats it over 20 seeds on the C08 device (its rows are not yet in `data/derived/benchmark/results.json`).
- Baked: a step works on about nine times the pixels of the plain FFT (3 by 3 upsampling); the cost of a hologram is above the live budget.
- Traps must be on bins with $z = 0$ and no vortex on a device; a shaped target is refused.
- Flicker is random and is dropped from the optimization model; it is scored but not modelled.
- The crosstalk parameters are device specific (the source's calibration took 30 minutes plus 2 hours); the effect size on a typical 8 micrometre pitch device is unknown.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
- Persson, Engstrom and Goksor 2012, Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
