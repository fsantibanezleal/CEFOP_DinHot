# M06: Weighted Gerchberg-Saxton (GSW)

| Item | Value |
|---|---|
| Ladder row | M06, tier classical (SDD, Method ladder) |
| Family, lane | GS, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m06_gsw.py` (`SPEC` line 18, `run` line 21) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` (`rule_gsw`, line 88) |
| Gate | `tests/methods/baseline/test_m06_gsw.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m06`, line 118) and `frontend/src/engine/holo/methods/gs.ts` |
| Card | [M06](../../frameworks/M06_gsw.md) |

## Tier and role

The established weighted variant of Gerchberg-Saxton: integral feedback on the trap weights, so that dark traps are boosted and
bright traps damped at each iteration. It is a baseline because it is the method of Di Leonardo, Ianni and Ruocco 2007 that
reaches high efficiency and high uniformity together on the 10x10 task (the best classical row of the ladder for point arrays), and
because it is the weighted base of M07 (phase-fixed), M12, M14, M15 and the starts of several optimizers. Source: Di Leonardo et al.
2007, Eq. (18) and the iteration that follows (https://doi.org/10.1364/OE.15.001913).

## Problem it answers

Equal trap intensities (uniformity above 0.9) at an efficiency close to GS, in about 10 iterations.

## Inputs and outputs

Inputs as M04 for trap targets (`form`, `init`, `budget`, `rng`); a shaped target is refused naming `traps`. Output: `Result` with
`phi`, one `history` entry per iteration, `fields` and `meta` (`method`, `form`, `iterations`). Target weights $w_m^{target}$ are
honoured: the history's `uniformity` and `rel_std` are those of $I_m/w_m$ (`core/metrics.py`).

## The method

The maximum condition of the weighted objective is (Di Leonardo et al. 2007, Eq. (18))
$\phi_j = \arg\big[\sum_m e^{i\Delta_j^m}\,w_m V_m/|V_m|\big]$, and the iteration, started from the SR hologram with $w_m^0 = 1$, is

$$w_m^k = w_m^{k-1}\,\frac{\langle |V^{k-1}| \rangle}{|V_m^{k-1}|}, \qquad
\phi_j^k = \arg \sum_m e^{+i\Delta_j^m}\; w_m^k\,\frac{V_m^{k-1}}{|V_m^{k-1}|}.$$

With target weights: $a_m = \sqrt{w_m^{target}}$, $w_m^0 = a_m$ and $|V_m|$ is replaced by $r_m = |V_m|/a_m$ (identical for equal weights):
`rule_gsw` (`_gs.py` lines 88 to 92) updates `state['w'] = w * mean(r) / r` and returns the coefficients `w * phasor(v)`; the initial
weight is set in `run_traps` (line 121, `state['a'].copy()` for this rule). The bar over $V$ in the numerator of the source was lost in
the text extraction; the sentence of the source ("adjust the weight in such a way to reduce the deviations from the average")
defines it as the average trap amplitude.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `form` | `auto` | `m06_gsw.py` line 21 | FFT form on bins, else point form (I1 report F1); `fft` for large arrays |
| $w_m^0$ | $a_m$ (1 for equal weights) | `_gs.py` line 121 | Di Leonardo et al. 2007 |

The port's default form is `point` (`frontend/src/engine/holo/methods/baseline.ts` line 121).

## Complexity and lane

Cost $K \times M \times N$ (point form), $O(P\log P)$ per iteration (FFT form). The source reports a GPU cost of about 0.44 ms per
trap and iteration at 768 by 768 (Bianchi and Di Leonardo 2010, through the algorithms dossier); DinHot relies on its own
measurement, about 24 ms per iteration in Node at the live grid (SDD, Lanes). Lane `live`; parity worst difference 1.9e-13 (T1 report
D2).

## Acceptance criterion and gate

Ladder row: efficiency and uniformity at least 0.9 within a median of 15 iterations on the 10x10 task with a flat beam (the source
reports about 10); the 3x3x3 lattice above 0.9 and 0.98. Gate `tests/methods/baseline/test_m06_gsw.py`:

- `::test_acceptance_10x10_flat_beam`: seeds 1 to 3, a flat beam; the first iteration with $e \ge 0.9$ and $u \ge 0.9$ must be at most 15
  for every seed, and the median uniformity at iteration 10 at least 0.85;
- `::test_acceptance_10x10_gaussian_beam`: the Gaussian beam of the core default, $e \ge 0.9$ of the ceiling (0.869) and $u \ge 0.9$
  within 20 iterations;
- `::test_acceptance_3x3x3_lattice`: lateral spacing 8 bins, axial step 40 mm (above the depth of field of the 256-pixel aperture);
  the first iteration within 100 with $e > 0.9$ and $u > 0.98$ together must exist for every seed;
- `::test_target_weights_are_respected`: a 2:1 weight gives an intensity ratio of 2.0 within 0.1 and a uniformity of $I/w$ above 0.95;
  `::test_fft_form_agrees`: the forms agree to 1e-6 rad.

The test is stricter than the ladder's median (every seed within 15) and looser than the source's 10; the gap is measured below.

## Evaluation that confirms or refutes it

Confirmed if efficiency and uniformity both reach 0.9 within 15 iterations on the flat-beam task and the 3D lattice meets 0.9 and 0.98;
refuted if a seed needs more than 15 iterations (the grid would converge too slowly to call the row a baseline of the ladder) or the
weights are not honoured. The paper's 10 iterations are on 768 by 768 pixels; the live grid is 256 by 256, so the bar is set at 15.

## Measured result

Acceptance run of 2026-10-28 (E2 report D2 and D5), 10x10 task 8 bins apart, 256 by 256 padded 2, test setup (850 nm, focal length 250
mm, pitch 12.5 um), seeds 1 to 3:

| Quantity | Measured | Conditions |
|---|---|---|
| First iteration with efficiency and uniformity both at 0.9 | 10, 13, 12 (flat beam); 10, 12, 12 (Gaussian, efficiency against 0.9 of the ceiling) | seeds 1, 2, 3 |
| Uniformity at iteration 10 | 0.887 [0.861, 0.910] | same |
| 3x3x3 lattice, first iteration with $e > 0.9$ and $u > 0.98$ | 32, 16, 24 (not monotone) | 3 seeds |

Published: efficiency 0.93, uniformity 0.99 after 30 iterations, above 0.9 in 10; 3x3x3 lattice 0.91 and 0.99.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.801 (0.77 to 0.817) | 1 (1 to 1) | 0.00904 (0.00233 to 0.0192) |
| C02 | 30 | 0.803 (0.801 to 0.806) | 0.971 (0.967 to 0.977) | 1.15 (0.859 to 1.47) |
| C03 | 30 | 0.805 (0.805 to 0.806) | 0.961 (0.958 to 0.964) | 1.15 (0.989 to 1.28) |
| C05 | 30 | 0.894 (0.891 to 0.897) | 0.971 (0.942 to 0.989) | 1.16 (0.496 to 2.29) |
| C06 | 30 | 0.705 (0.7 to 0.708) | 0.998 (0.997 to 0.998) | 0.126 (0.0826 to 0.168) |
| C07 | 30 | 0.797 (0.793 to 0.802) | 0.984 (0.972 to 0.992) | 0.76 (0.387 to 1.32) |
| C08 | 30 | 0.689 (0.682 to 0.695) | 0.734 (0.725 to 0.745) | 13.6 (12.5 to 14.3) |
| C09 | 30 | 0.449 (0.441 to 0.454) | 0.905 (0.887 to 0.915) | 6.01 (4.77 to 7.31) |
| C10 | 30 | 0.803 (0.801 to 0.806) | 0.976 (0.973 to 0.978) | 0.98 (0.924 to 1.09) |
| C12 | 30 | 0.801 (0.798 to 0.805) | 0.972 (0.97 to 0.975) | 1.15 (1.02 to 1.41) |
| C13 | 30 | 0.738 (0.736 to 0.74) | 0.978 (0.974 to 0.982) | 0.661 (0.593 to 0.739) |
| C14 | 30 | 0.785 (0.785 to 0.786) | 0.988 (0.985 to 0.992) | 0.486 (0.315 to 0.589) |

## Limits and failure modes

Convergence is slightly slower on the 256 grid than in the source (10 to 13 against 10 iterations). The efficiency of a Gaussian
beam is capped by the beam ceiling (0.869 at the test setup). On a device with crosstalk and 4-bit phase the weights equalize the
ideal model, not the device (C08: relative standard deviation 13 to 15 percent in the bake), which is the gap that M13 and BS-1
address. The 3D lattice does not converge monotonically.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027
