# M13: Device-aware conjugate gradient with pixel crosstalk

| Item | Value |
|---|---|
| Ladder row | M13, tier sota (SDD, Method ladder) |
| Family, lane | optimization, device-aware, baked |
| Targets, dimensions | traps and shaped fields, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/optim/m13_crosstalk_cg.py` (`SPEC` line 36, `SCHROFF_DEVICE` line 38, `run` line 41) on the driver `optimize` of `data-pipeline/pipeline/model/holo/methods/optim/m10_cg.py` (line 56); device model `data-pipeline/pipeline/model/holo/core/device.py` |
| Gate | `tests/methods/optim/test_m13_crosstalk_cg.py` |
| Live port | none (lane `baked`; `getMethod('M13')` raises `NotLive`) |
| Card | [M13](../../frameworks/M13_crosstalk-aware-cg.md); physics component [P02](../../frameworks/P02_device-model.md) |

## Tier and role

State of the art, replicated: optimize the hologram through the SLM's pixel crosstalk. The solution replicated is Schroff, La Rooij, Haller and
Kuhr, Sci. Rep. 13, 3252 (2023), https://doi.org/10.1038/s41598-023-30296-6 (arXiv 2212.10507): each SLM pixel is upsampled to a block of
computational pixels and the phase is convolved with a fitted kernel before the Fourier transform. A method that optimizes through that blur
reaches a lower error on the device than the same optimizer that ignores it. It is the device-aware reference that BS-1 extends from shaped
potentials to the weighted GS of trap arrays.

## Problem it answers

Lower signal error on a real pixelated SLM, where neighbouring pixels blur into each other, at a stated cost in time and efficiency.

## Inputs and outputs

- Inputs: as M10 plus the `device` (a `core.device.Device`): `setup`, a `Target` of kind `traps` or `field`, `budget`, `rng`, optional `init`, `t`,
  `efficiency`. A trap target with a vortex or an axial offset on a device raises a `ValueError` (`m13_crosstalk_cg.py` lines 44 to 46). With
  `device=None`, M13 is M10 bit for bit (test `::test_without_a_device_m13_is_m10`).
- Output: `Result` as M10, with `meta['device_aware']` true when a device was given; `fields` is the focal field (or the trap fields) of the device.

## The method

Forward model of the device (Schroff et al. 2023, Methods, "Pixel crosstalk modelling", Eq. (4)): each SLM pixel is $3\times3$ computational pixels
and the phase, kept in $[0, 2\pi)$, is convolved with a kernel,

$$\tilde\phi = K * \phi_{\uparrow 3},\qquad
K = \mathcal F^{-1}\Big\{\exp\Big[-\frac{|\kappa_x|^q + |\kappa_y|^q}{\sigma^q}\Big]\Big\},\qquad \sigma = 1.24\ \mathrm{px}^{-1},\ q = 1.80.$$

The convolution is circular (FFT based), so the phase wraps at the SLM border (`core/device.py` module docstring). The model passed is the `device`:
crosstalk, the pixel-aperture envelope and the quantizer, treated straight-through (quantized in the forward pass, identity in the backward pass);
flicker is dropped (`FocalForward` replaces `flicker_rad` by 0). The cost is Harte's $C_t$ of M10 (`FieldCost`/`TrapCost`) evaluated on the device's
focal field and minimized by the same Fletcher-Reeves conjugate gradient with a strong-Wolfe line search as M10. The paper's cost is
$C = s\sum_S(\tilde T - \tilde I)^2$ with normalized $\tilde T,\tilde I$ and Polak-Ribiere CG with the gradient by autodiff; DinHot's gradient is
the closed form: the adjoint of the crosstalk operator is the convolution with the reversed kernel followed by the sum over each $3\times3$ block
(`core.device.crosstalk_adjoint`, line 128; `FocalForward.adjoint`, `optim/_common.py` line 130), so the TypeScript port would need no autodiff.
A pruned zero-padded transform (only the $n u$ nonzero rows and the wanted frequencies) makes the forward and the adjoint 2.4 times cheaper than
the plain upsampled FFT pair (0.14 s forward and 0.13 s adjoint at 256 pixels, E3 report D1).

UNVERIFIED: the unit of $k$ in the kernel. The implementation takes $k$ in cycles per SLM pixel (so the computational grid spans $\pm u/2$); the
research record did not state the unit, and the gap study was to re-check it against the paper (`core/device.py` docstring).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| device | the one passed; `SCHROFF_DEVICE = Device(crosstalk=(1.24, 1.80), upsample=3)` is the published kernel | `m13_crosstalk_cg.py` line 38 | Schroff et al. 2023 (fitted $\sigma$, $q$) |
| `t`, `efficiency`, line search | as M10 | `m10_cg.py` lines 43 to 71 | see M10 |
| upsampling | 3 | `Device.upsample` | Schroff et al. 2023 |

## Complexity and lane

One iteration costs about the 3 by 3 upsampled FFT pair against one FFT pair (the source reports a run time about 6 times longer than without
the model). Lane `baked` (`SPEC`, line 36): the gradient run on the upsampled grid is too heavy for the live budget at full size. In the bake the
cases C04 (shaped disc) and C08 (device-limited trap array) run it.

## Acceptance criterion and gate

Ladder row: on the crosstalk device, lower error than M10 without the model on a large disc. Gate
`tests/methods/optim/test_m13_crosstalk_cg.py::test_acceptance_lower_error_than_m10_on_the_crosstalk_device_for_a_large_disc`: a disc of
radius 24 bins (guard 3) on the 128 by 128 focal grid (64-pixel SLM padded 2), `Budget(100)`, $t = 2$, seed 1; M10 on the ideal model and M13 on
`Device(crosstalk=(1.24, 1.80), upsample=3)`, both holograms scored through the device (`device_focal_field`), and the M13 signal error must be
below M10's. Companion tests: the paper device, the gradient through the crosstalk operator against finite differences ($t = 2$ and 4), a
vortex trap on a device is refused, the device cost decreases and the history is recorded, determinism.

## Evaluation that confirms or refutes it

Confirmed if the device-aware run has the lower error on the device; refuted if modelling the crosstalk did not help (the optimizer would have
no use for the model). The published figures to compare in shape are Schroff Table 1: large disc 1.9 percent error with the model against 2.7
without, efficiency 28 against 34 percent. The hypothesis the row tests is therefore that the model lowers the error at some efficiency cost.

## Measured result

Acceptance run of 2026-10-28 (E3 report D2 and D5), 64-pixel SLM padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), 1 seed,
100 iterations, large disc scored on the crosstalk device:

| Quantity | M13 | M10 (no model) |
|---|---|---|
| Signal-region error | 0.241 | 1.38 |
| Efficiency | 0.535 | 0.507 |

Both errors are far above Schroff's 1.9 and 2.7 percent: the acceptance budget is 100 iterations and a single seed; the test does not claim the
published level. The ordering is the criterion.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; cases C04 and C08 with their own
optics and device in `data/derived/manifests/`; the C04 row is the shaped disc scored on the case's crosstalk device):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C08 | 30 | 0.418 (0.252 to 0.547) | 0.371 (0.0796 to 0.685) | 25.2 (11.3 to 40.7) |

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.381 (0.38 to 0.382) | 25.8 (24.5 to 26.9) |

On C04 M13 has the lowest mean error in the bake (about 26 percent, with M18 at 27, against 45 for GS, 68 for M11, 105 to 170 for M10 and about
205 for M08). On the trap array of C08 its 30 iterations are not converged (efficiency 0.27 to 0.52, relative standard deviation 19 to 31 percent).

## Limits and failure modes

- UNVERIFIED: the unit of $k$ in the kernel (above); the claim is relative to the model of the device, not to a measured instrument.
- One seed in the acceptance test; the benchmark protocol repeats it over 20 seeds (its rows are not yet in `data/derived/benchmark/results.json`).
- Baked: too heavy for the live budget at full size.
- Traps with an axial offset or a vortex are refused on a device; the trap fields are read at the nearest FFT bin.
- First-order optimizer: the trap-array rows of the bake are far from converged at 30 iterations.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6 ; arXiv 2212.10507
- Harte, Bruce, Belmonte and Arnold 2014, Opt. Express 22, 26548, https://doi.org/10.1364/OE.22.026548 (the cost)

## Update after the corrections of 2026-10-29

On the quantizing device of C08 the cost is a staircase and the strong-Wolfe line search failed after three iterations whatever the budget; a staircase (ladder) line search (`_common.staircase_search`, used by M13 only) lets it run its budget (5 and 60 iterations run 5 and 60). The scored spread on that device does not improve systematically (three seeds: 31.1, 18.9 and 30.8 percent before; 23.7, 11.3 and 40.7 after): a measured negative, with the ranges re-measured.

From the 30-iteration weighted-GS start (notebook `06-device-and-aberrations/03-crosstalk-aware-cg-against-cg`, case C08, first seed, after the rule corrections of the same day): M13 scores 7.65 percent after 5 iterations and 7.27 percent after 60 on the full C08 device, against 13.45 for M10 on the ideal model and 13.07 for the start, at an efficiency of 0.6824 against 0.6851. M13 run for the device without the quantizer and the flicker (crosstalk and aperture only) reaches 3.55 percent on that device and 6.63 percent on the full device, lower than the 7.27 of the full-model run: on this case the straight-through quantizer in the model costs more than it gives. The start matters: from a random start the same run is far worse (the bake's rows and notebook 03-04, 57.3 percent after 12 iterations).
