# M10: Conjugate-gradient minimization

| Item | Value |
|---|---|
| Ladder row | M10, tier sota (SDD, Method ladder) |
| Family, lane | optimization, both (small sizes live, full size baked) |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/optim/m10_cg.py` (`SPEC` line 38, `optimize` line 56, `run` line 93) on `data-pipeline/pipeline/model/holo/methods/optim/_common.py` (`cg_minimize` line 289, `TrapCost` line 189, `FieldCost` line 221) |
| Gate | `tests/methods/optim/test_m10_cg.py` |
| Live port | `frontend/src/engine/holo/methods/optim.ts` (`m10`, line 516; `cgMinimize`, line 390) |
| Card | [M10](../../frameworks/M10_conjugate-gradient.md) |

## Tier and role

State of the art, replicated: minimize an intensity cost over all pixel phases at once with a gradient method. The solution replicated is
Harte, Bruce, Belmonte and Arnold, Opt. Express 22, 26548 (2014), https://doi.org/10.1364/OE.22.026548 (arXiv 1408.0188), Eqs. (1) to (11),
which is the reference for smooth potentials with suppressed optical vortices and the parent of the device-aware variant M13 and of the
gradient family M11, BS-1 and BS-4. The gradient costs two Fourier transforms, so it is cheap.

## Problem it answers

A shaped potential (or a trap array) at the accuracy a first-order method can reach, without vortices in the signal region, for a cost
that is explicit and a gradient that is closed form (so the TypeScript port needs no automatic differentiation).

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` or `field`, `budget` (`iterations` is split among the stages; `time_s` a deadline), `rng`,
  optional `init`, `t` (an even integer at least 2 or a tuple of them), `efficiency` (the design efficiency of the target). `device` is
  ignored by M10 (the ideal model; `run` passes `device=None`, line 96): M13 is the device-aware variant.
- Output: `Result` with `phi` in $[0, 2\pi)$, `history` with one entry per accepted step (the cost, and `t`), `fields` (the last trap fields
  or focal field) and `meta` (`method`, `iterations`, `device_aware`).
- A field target must be on the `n_fft` by `n_fft` focal grid (`FieldCost`, `_common.py` line 235).

## The method

The SLM field is $E_{in} = A_j e^{i\phi_j}$, the focal field $E_{out}$ its zero-padded Fourier transform, and the cost over the signal
region (the noise region is free) is (Harte et al. 2014, Eqs. (1) to (11))

$$C_t = \sum_{nm}\big(T_{nm} - |\tilde\psi_{nm}|^2\big)^t,\qquad
\frac{\partial C_t}{\partial\phi_{rs}} = 2t\,\operatorname{Re}\big(i\,\psi_{rs}^*X_{rs}\big),\qquad
X_{rs} = \sum_{nm}(T_{nm} - I_{nm})^{t-1}\,\tilde\psi_{nm}^*\,e^{+2\pi i(rn+sm)/N}.$$

In the code the cost is normalized by $\sum(sT)^t$ (scale free, the same minimizers), $s = 1$, with the target intensity carrying the
requested efficiency: for traps $T_m = \eta\,w_m/\sum w$, for fields $T = \eta\,N_{pix}\,a^2/\sum_{SR}a^2$, so $\sum T$ is the requested fraction of
the total power (`TrapCost`, line 189; `FieldCost`, line 221). The gradient is $\partial L/\partial\phi_j = 2\operatorname{Re}\big(i f_j\,\overline{(Op^H G)_j}\big)$
with $G = L'(I)\,Z$ the Wirtinger gradient (module docstring of `_common.py`), where `FocalForward` and `TrapForward` implement the operator and its
adjoint (two FFTs).

$t = 2$ is the basic cost; the powered cost $t = 4$ suppresses the vortices that the basic cost leaves (Harte: 26 percent error with $t = 2$;
the sequential $t = 4$ then $t = 2$ gives 0.07 percent on a ring and power-law target after 13 000 iterations).

Optimizer: Fletcher-Reeves nonlinear conjugate gradient, $d_i = -g_i + \gamma_i d_{i-1}$ with $\gamma_i = g_i\cdot g_i/(g_{i-1}\cdot g_{i-1})$
(Harte Eqs. (3) to (5)), with a strong-Wolfe line search (cubic interpolation, Nocedal and Wright, Algorithms 3.5 and 3.6, Eq. 3.59). The source
does not state the line search; this is DinHot's choice, and $c_2 < 1/2$ keeps the Fletcher-Reeves directions descent directions. The first
trial step moves the largest pixel by 0.1 rad, later ones are $2(f_k - f_{k-1})/\phi'(0)$ (Eq. 3.60); if the direction is not a descent
direction or the search fails, the iteration restarts from steepest descent and the run stops if that fails too. The cost never increases
(`_common.py` lines 289 to 337). The start is $n_{pix}^2$ uniform random phases from `rng`.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `t` | `None`: stages $(4, 2)$ with an equal share of the iterations each for a field, $(2)$ for traps | `m10_cg.py` lines 43 to 53 | Harte et al. 2014 (sequential powers); for traps the basic cost |
| `efficiency` | 0.9 for traps, 0.4 for fields | `m10_cg.py` lines 68 and 71 | Harte reports 45 to 64 percent in the trapping region (fields); 0.9 for traps is DinHot's design level |
| `c1`, `c2` | $10^{-4}$, 0.1 | `_common.py` line 290 | Nocedal and Wright (the values for a nonlinear conjugate gradient) |
| `max_line_evals` | 25 | `_common.py` line 290 | numerical guard |
| `DEFAULT_LATTICE_ITERATIONS` | 1500 | `m10_cg.py` line 40 | DinHot's budget for the lattice acceptance test (Harte: 4000 iterations for the same figure) |

The benchmark tuning grid for M10 is `t` in (1.5, 2.0, 3.0, 4.0) (`FALLBACK_TUNING`, `data-pipeline/pipeline/benchmark/protocol.py` line 56);
an odd or non-integer `t` is refused by `TrapCost` and `FieldCost` (`t < 2 or t % 2`), so only the entries 2.0 and 4.0 of that grid can run
(not established whether the benchmark skips the others: the protocol keeps a tuning grid only when `len(grid) == TUNING_CANDIDATES`).

## Complexity and lane

Per iteration: one forward and one adjoint evaluation, i.e. two FFTs, times the line-search evaluations (the cost is dominated by them). Lane
`both`: small sizes are live, full size baked. Parity of the port: 1e-8 rad (a line search and Adam pass the last-bit differences of the cost
through the iterate; observed 1e-11 rad at the live grid, T1 report D2). Test runtime about 24 s for the lattice acceptance (E3 report).

## Acceptance criterion and gate

Ladder row: the analytic gradient matches finite differences; a square lattice below 1 percent error. Gate `tests/methods/optim/test_m10_cg.py`:

- `::test_analytic_gradient_matches_finite_differences_on_a_shaped_target` and `::test_analytic_gradient_matches_finite_differences_on_traps`,
  for $t = 2$ and 4, relative error at most 1e-5 (central differences, 6 directions);
- `::test_acceptance_square_lattice_below_one_percent_error`: a 4 by 4 lattice of flat-top spots of radius 3 bins at a spacing of 16 bins on
  the 128 by 128 focal grid (64-pixel SLM padded 2), `Budget(1500)`, $t = 2$, seeds 1 and 2, signal error (the RMS fractional error with the
  intensity and the target each normalized to unit sum in the region) below 0.01;
- `::test_cost_decreases_monotonically_and_history_is_complete`, `::test_sequential_powers_run_t4_then_t2`,
  `::test_trap_target_improves_uniformity_over_a_random_start`, determinism.

## Evaluation that confirms or refutes it

Confirmed by gradient agreement to 1e-5 and a lattice error below 1 percent, within a factor close to Harte's 0.58 percent at 4000
iterations. Refuted if the gradient disagrees (the closed form would be wrong) or the cost rises (the line search would be broken, tested).

## Measured result

Acceptance run of 2026-10-28 (E3 report D1 and D5), test setup (850 nm, focal length 250 mm, pitch 12.5 um):

| Quantity | Measured | Reference | Conditions |
|---|---|---|---|
| Gradient against finite differences | largest relative error 1.76e-7 (field, $t = 2$), 8.5e-8 ($t = 4$), 4.5e-8 and 1.4e-7 through the crosstalk operator | limit 1e-5 | 4 cases, 6 directions |
| Square lattice error | 0.55 and 0.51 percent | Harte 0.58 percent at 4000 iterations | 2 seeds, 1500 iterations, $t = 2$, 64-pixel SLM padded 2 |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own
optics, listed in `data/derived/manifests/`; the C04 row is the shaped disc scored on the case's crosstalk device):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.166 (0.152 to 0.179) | 0.281 (0.175 to 0.395) | 51.7 (43.8 to 63.1) |
| C02 | 30 | 0.259 (0.254 to 0.265) | 0.0361 (0.019 to 0.0541) | 41.1 (38 to 44.4) |
| C05 | 30 | 0.21 (0.206 to 0.215) | 0.0469 (0.0243 to 0.0911) | 53 (46.8 to 61.6) |
| C06 | 30 | 0.162 (0.148 to 0.171) | 0.0621 (0.0112 to 0.145) | 45.1 (35.9 to 51) |
| C07 | 30 | 0.189 (0.185 to 0.196) | 0.0773 (0.0354 to 0.157) | 63.2 (55.6 to 70.9) |
| C08 | 30 | 0.311 (0.304 to 0.316) | 0.251 (0.0404 to 0.439) | 32.2 (29.7 to 35.5) |

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.39 (0.383 to 0.399) | 131 (105 to 170) |

The bake budget (30 iterations from a random start) is far from the 1500 of the lattice test, and the trap-array rows are far from
converged (efficiency 0.15 to 0.38 against the design level 0.9, relative standard deviation 30 to 70 percent). The method is a
first-order optimizer and the bake does not run it to convergence; these rows are not a statement about its limit.

## Limits and failure modes

- The strong-Wolfe line search is DinHot's choice; the source does not state one.
- Ideal-device model: scored on a device with crosstalk and 4-bit phase it loses accuracy (M13 is the variant that models it; C04 and C08 in the bake).
- Cost grows with the pixel count; the full-size runs are baked.
- A random start can leave vortices with $t = 2$ (the reason for the $(4, 2)$ stages for fields).

## References

- Harte, Bruce, Belmonte and Arnold 2014, Opt. Express 22, 26548, https://doi.org/10.1364/OE.22.026548
- Nocedal and Wright, Numerical Optimization, Algorithms 3.5 and 3.6 (the line search; not re-read)
