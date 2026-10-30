# M11: Wirtinger gradient descent with Adam

| Item | Value |
|---|---|
| Ladder row | M11, tier sota (SDD, Method ladder) |
| Family, lane | optimization, both (small sizes live, full size baked) |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/optim/m11_wirtinger_adam.py` (`SPEC` line 36, `PAPER_LR` line 38, `DEFAULT_LR` line 39, `run` line 42) on `data-pipeline/pipeline/model/holo/methods/optim/_common.py` (`adam_minimize` line 398) |
| Gate | `tests/methods/optim/test_m11_wirtinger_adam.py` |
| Live port | `frontend/src/engine/holo/methods/optim.ts` (`m11`, line 550; `adamMinimize`, line 432) |
| Card | [M11](../../frameworks/M11_wirtinger-adam.md) |

## Tier and role

State of the art, replicated: treat the hologram as a differentiable program, so that any linear forward model (the point-trap form, the FFT
form, a device) can be optimized with a first-order method as long as the gradient with respect to the phase is available. The solution
replicated is Chakravarthula, Peng, Kollin, Fuchs, Heide and Wetzstein, "Wirtinger Holography for Near-Eye Displays", ACM TOG 38(6), 213
(2019), https://doi.org/10.1145/3355089.3356539, Eqs. (5) to (8), with the Adam optimizer of Kingma and Ba 2015 (named in the module, not
re-read). It is the bridge between the classical iterative methods and the learned ones (M17).

## Problem it answers

A low trap-intensity error from a short first-order run on the ideal or on a device model, with a gradient pulled back through the
propagation by the chain rule instead of an ad hoc update.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` or `field`, `budget` (`iterations` Adam steps; `time_s` a deadline), `rng`, optional `init`,
  `lr`, `efficiency`, `device`. With a `device` the traps must be on FFT bins with $z = 0$ and no vortex (`TrapForward`, `_common.py` line 165).
- Output: `Result` with `phi` in $[0, 2\pi)$, `history` where `history[k]` is the state before step $k+1$ (Adam is not a descent method; the
  cost may rise), `fields`, and `meta` (`lr`, `paper_lr`, `device_aware`).

## The method

Minimize $f(|P(H(\phi))|^2, I) + \|\phi\|^2$ over the phase with a differentiable propagation $P$ and $H = c\,e^{i\phi}$. The gradient of the
real loss with respect to the complex field is the Wirtinger derivative $\partial L/\partial z^*$, pulled back through $P$ by the chain rule
(Chakravarthula et al. 2019, Eqs. (5) to (8)):

$$\frac{\partial L}{\partial\phi_j} = 2\operatorname{Re}\!\big(i\,f_j\,\overline{(P^H G)_j}\big),\qquad G = \frac{\partial L}{\partial z^*} = L'(I)\,z,$$

so any linear forward model works (`TrapForward`, the point-trap form with $z$ and vortex charge or the device FFT form; `FocalForward` for
shaped fields). The loss here is the quadratic intensity loss of the optimization module,
$C_2 = \sum(I_m - T_m)^2/\sum T_m^2$, with the design efficiency 0.9 for traps and 0.4 for fields (`m11_wirtinger_adam.py` lines 49 and 51);
the paper's $\|\phi\|^2$ term has weight zero (a phase penalty has no role for a phase-only hologram of traps). Adam (Kingma and Ba 2015):
$m \leftarrow \beta_1 m + (1-\beta_1)g$, $v \leftarrow \beta_2 v + (1-\beta_2)g^2$, $x \leftarrow x - \mathrm{lr}\,\hat m/(\sqrt{\hat v} + \epsilon)$ with
bias-corrected $\hat m$, $\hat v$ (`_common.py` lines 398 to 424). The paper uses L-BFGS for quadratic losses and Adam with learning rate 0.001 for
learned losses. The start is $n_{pix}^2$ uniform random phases from `rng`.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `lr` | `DEFAULT_LR = 1.0` | `m11_wirtinger_adam.py` line 39 | the tuning record below: the paper's 0.001 moves a pixel at most 0.03 rad in 30 iterations |
| `PAPER_LR` | 0.001 (recorded, not used) | line 38 | Chakravarthula et al. 2019, for learned losses |
| $\beta_1$, $\beta_2$, $\epsilon$ | 0.9, 0.999, $10^{-8}$ | `_common.py` line 398 | Kingma and Ba 2015 |
| `efficiency` | 0.9 traps, 0.4 fields | `m11_wirtinger_adam.py` lines 49 and 51 | design level (as M10) |

Tuning record (10x10 task, 256 by 256 pixels, 30 iterations, relative standard deviation of $I_m/w_m$ in percent; E3 report D1, in the module
docstring): tuning seeds 1 to 3, lr 0.01: 90 to 108; 0.03: 68 to 75; 0.1: 10 to 15; 0.3: 3.9 to 4.8; 1.0: 2.3 to 2.5. Separate seeds 11 to 13,
median: lr 0.5: 2.92; 1.0: 2.42; 2.0: 2.40; 4.0: 14.0. The rate 2.0 ties within 1 percent and the smaller step is kept.

Finding: the benchmark tuning grid for M11 is `lr` in (3e-4, 1e-3, 3e-3, 1e-2) (`FALLBACK_TUNING`, `data-pipeline/pipeline/benchmark/protocol.py`
line 57). All four values are far below the default and, by the record above, in the range that gives 90 to 108 percent spread at 30
iterations; the `tuned` arm of the benchmark for M11 therefore cannot contain the rate that the tuning record selected. Whether this matters
for a benchmark row is not established (the rows of M11 are not yet in `data/derived/benchmark/results.json`).

## Complexity and lane

Per iteration: one forward and one adjoint evaluation, two FFTs in the FFT form. Lane `both`. Parity of the port: 1e-8 rad (Adam passes the
last-bit differences of the gradient through the iterate; observed 1.1e-12 at the method level and 1.0e-11 at the live grid, T1 report D2).

## Acceptance criterion and gate

Ladder row: lower trap-intensity error than M04 at equal iterations on the 10x10 task. Gate
`tests/methods/optim/test_m11_wirtinger_adam.py::test_acceptance_lower_trap_intensity_error_than_gs_at_equal_iterations`: seeds 1 to 3,
30 iterations each, on the 256 by 256 padded-2 grid; the relative standard deviation of $I_m/w_m$ for M11 must be below GS's per seed and in
median (the GS arm is the in-test copy of the GS rule, `_gs_family.weighted_gs` with `variant='gs'`; E3 cross-checked it against the E2 module M04
and found the same numbers to 4 digits). Companion tests: the Wirtinger gradient against finite differences on a set with $z$ offsets, a vortex and
non-uniform weights; the loss decreases and the history is recorded; a field target runs; determinism; the documented defaults.

## Evaluation that confirms or refutes it

Confirmed by a lower spread than GS in every seed; refuted if Adam with the tuned rate did not beat GS at equal iterations. The mutation run
of E3 (the paper's `lr = 0.001`) fails the acceptance test, which shows that the tuned rate is what makes the row pass.

## Measured result

Acceptance run of 2026-10-28 (E3 report D1 and D5), 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um),
30 iterations, seeds 1 to 3:

| Quantity | M11 | M04 (GS) |
|---|---|---|
| Relative standard deviation of $I_m/w_m$ (percent) | 2.54, 2.46, 2.26 | 17.79, 17.98, 18.82 |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own
optics, listed in `data/derived/manifests/`; the C04 row is the shaped disc scored on the case's crosstalk device):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.785 (0.785 to 0.786) | 0.979 (0.97 to 0.992) | 1.25 (0.494 to 1.93) |
| C02 | 30 | 0.763 (0.762 to 0.763) | 0.929 (0.921 to 0.942) | 2.5 (2.39 to 2.6) |
| C05 | 30 | 0.822 (0.814 to 0.83) | 0.957 (0.953 to 0.963) | 1.77 (1.76 to 1.79) |
| C07 | 30 | 0.766 (0.763 to 0.769) | 0.947 (0.935 to 0.958) | 2.49 (2 to 3.23) |
| C14 | 30 | 0.755 (0.754 to 0.755) | 0.956 (0.951 to 0.959) | 2.02 (1.95 to 2.05) |

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.172 (0.161 to 0.181) | 69.7 (68.5 to 72) |

## Limits and failure modes

First-order: 30 iterations stop at a few percent (2.3 to 2.5 on the 10x10 task). The tuned rate is
specific to this loss and these grids (4.0 diverges to 14 percent). Adam is not a descent method. The device-aware use requires traps on bins. On a
shaped target scored on a device (C04) the rate is the one of the trap loss, untuned for fields.

## References

- Chakravarthula, Peng, Kollin, Fuchs, Heide and Wetzstein 2019, "Wirtinger Holography for Near-Eye Displays", ACM TOG 38(6), 213,
  https://doi.org/10.1145/3355089.3356539
- Kingma and Ba 2015, Adam (named in the module; not re-read)
