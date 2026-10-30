# M09: Direct search

| Item | Value |
|---|---|
| Ladder row | M09, tier classical (SDD, Method ladder) |
| Family, lane | optimization, baked |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/optim/m09_direct_search.py` (`SPEC` line 39, `polin_cost` line 46, `run` line 55) |
| Gate | `tests/methods/optim/test_m09_direct_search.py` |
| Live port | none (lane `baked`; `getMethod('M09')` raises `NotLive`, `frontend/src/engine/holo/methods.parity.test.ts`) |
| Card | [M09](../../frameworks/M09_direct-search.md) |

## Tier and role

The established optimization method of holographic optical tweezers: visit every SLM pixel in random order, try every phase level
and keep the best, against an explicit cost that trades efficiency for uniformity with one weight. It is a classical baseline
because it is the reference "perfect uniformity" method of Di Leonardo, Ianni and Ruocco 2007 (uniformity 1.00 on the 10x10 task) and
because it is the explicit-cost ancestor of the gradient methods (M10, M11). Sources: Polin, Hovhannisyan and Sorensen, Opt. Express
13, 5831 (2005), https://doi.org/10.1364/OPEX.13.005831, cost Eqs. (11) to (13); the benchmark numbers are Di Leonardo et al. 2007
(https://doi.org/10.1364/OE.15.001913).

## Problem it answers

Near-perfect uniformity where Gerchberg-Saxton stalls (quasi-periodic sets, 3D sets with vortices), at a stated cost in efficiency.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`, line 59), `budget` (its
  `iterations` is the number of sweeps, its `time_s` an optional deadline), `rng` (the pixel order is a seeded Fisher-Yates through the
  portable generator, `optim/_common.py` `permutation`, line 45), optional `init` (shape `n_pix` by `n_pix`), `f`, `levels`,
  `max_trials`. `device` is ignored: the optimization uses the ideal point-trap model.
- Output: `Result` with `phi` in $[0, 2\pi)$, `history` with one entry per sweep (`cost`, `trials` extra), `fields` (trap fields) and
  `meta` (`trials`, `accepted`, `f`, `levels`, `sweeps`).

## The method

With $I_m$ the trap intensities (fractions of the input power), $I^D_m = w_m/\operatorname{mean}(w)$ the design intensities and $M$ the
trap count, the cost of Polin et al. (2005), Eqs. (11) to (13), is

$$C = -\langle I\rangle + f\,\sigma,\qquad \sigma = \sqrt{\frac1M\sum_m\big(I_m - \gamma I^D_m\big)^2},\qquad
\gamma = \frac{\sum_m I_m I^D_m}{\sum_m (I^D_m)^2}$$

(`polin_cost`, `m09_direct_search.py` line 46; $f$ weights uniformity against efficiency). One sweep visits every SLM pixel once in
seeded random order; at each pixel all $P$ trial phases $2\pi k/P$ are evaluated and the best is kept if it lowers the cost, otherwise
the current phase stays, so the cost never increases (lines 96 to 110). The trap fields are updated incrementally: a change
$\delta z = e^{i\phi'} - e^{i\phi}$ at pixel $j$ changes $V_m$ by $\frac{A_j}{N_{pix}}\,\delta z\,e^{-i\Delta_j^m}$, an $O(M)$ update that
holds for any trap $z$ and vortex charge (point-trap form, lines 98 to 103). After each sweep $V$ is recomputed in full to drop the
rounding drift of the increments (line 111). The start is the SR superposition (`_gs_family.sr_start`) rounded to the $P$ levels
(line 72); `init` overrides it. Polin et al. report convergence in about $N$ trials and a worst case $N\,P$.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `levels` $P$ | 8 | `m09_direct_search.py` line 41 | the 8 grey levels of the direct-search row of Di Leonardo et al. 2007 |
| `f` | 0.5 | line 42 | the value of Di Leonardo et al. 2007's direct-search row ($f = 0.5$: uniformity 1.00, efficiency 0.68 after $1.3\,N$ steps) |
| `DEFAULT_SWEEPS` | 2 | line 43 | DinHot's budget for the acceptance tests; the constant is declared and used by the tests as `Budget(M09.DEFAULT_SWEEPS)`, but `run` itself takes the number of sweeps from `budget.iterations` (it does not read the constant) |
| `max_trials` | `None` (no cap) | `run`, line 56 | a cap on the trial phases evaluated, for the time-boxed rows |

## Complexity and lane

One trial costs $O(M)$; a sweep evaluates $N_{pix}\,P$ trials, so $O(N_{pix}\,P\,M)$ per sweep (Di Leonardo et al. 2007 give the scaling
$K \times P \times M$). Sequential by construction. Lane `baked` (`SPEC`, line 39): the full-size run is replayed from the bake; the
bake runs it on the cases C01, C02, C05, C06, C07 (committed manifests). The test of the incremental update agrees with a full
evaluation to 1e-10 (`::test_incremental_fields_equal_a_full_evaluation_and_cost_never_rises`). Test runtimes on the development
machine: about 29 s for the 10x10 acceptance and 17 s for the quasi-periodic set (E3 report, slowest tests).

## Acceptance criterion and gate

Ladder row: uniformity at least 0.98 on the 10x10 task; under 5 percent rms variation on a quasi-periodic set. Gate:

- `::test_acceptance_uniformity_on_the_10x10_task`: seeds 1 and 2, 256 by 256 padded 2, `Budget(2)` sweeps; $u \ge 0.98$ for both and
  $e > 0.3$;
- `::test_acceptance_rms_variation_on_the_quasi_periodic_set`: 119 traps, seed 1, `Budget(2)`; the relative standard deviation below
  5 percent.

The quasi-periodic set is DinHot's own (`tests/methods/optim/e3_helpers.py`, `quasi_periodic_119`: a product of two Fibonacci
chains with gaps of 9 and 6 bins, 11 by 11 sites with two removed); the coordinates of Polin et al.'s 119 traps are not published.
Further tests: `polin_cost` against the equations, the cost never rises, the trial budget is honoured, vortex and axial traps are
supported, and determinism for a seed.

## Evaluation that confirms or refutes it

Confirmed by uniformity at least 0.98 with the efficiency above 0.3 (so the uniformity is not bought by switching the traps off) and
by the quasi-periodic set below 5 percent, where the source reports GS and the adaptive-additive method above 50 percent. Refuted if
a sweep ever raises the cost or if the incremental fields drift from the full evaluation.

## Measured result

Acceptance run of 2026-10-28 (E3 report D1 and D5), 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um, 8 bins
spacing for the 10x10 task), 2 sweeps:

| Quantity | Measured | Reference | Conditions |
|---|---|---|---|
| Uniformity, 10x10 task | 0.9994, 0.9992 (efficiency 0.66, 0.65) | GS 0.55 to 0.62; published direct search 1.00 and 0.68 | seeds 1 and 2 |
| Relative standard deviation, 119 quasi-periodic traps | 0.023 percent | published: GS and adaptive-additive above 50 percent, direct search below 5 percent (Polin 2005; not re-run here) | 1 seed |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.65 (0.632 to 0.685) | 1 (1 to 1) | 0.00074 (0.000716 to 0.000762) |
| C02 | 30 | 0.649 (0.636 to 0.658) | 1 (1 to 1) | 0.0137 (0.0132 to 0.0143) |
| C05 | 30 | 0.679 (0.66 to 0.699) | 1 (1 to 1) | 0.00637 (0.00609 to 0.00677) |
| C06 | 30 | 0.642 (0.64 to 0.644) | 1 (1 to 1) | 0.00243 (0.00231 to 0.00262) |
| C07 | 30 | 0.638 (0.63 to 0.646) | 1 (1 to 1) | 0.0029 (0.0025 to 0.00356) |

## Limits and failure modes

Sequential and slow; stuck in local minima (Polin); ghost traps absorb efficiency (Di Leonardo et al. 2007): the efficiency is 0.63 to
0.70 in the bake against 0.80 for the weighted GS. The cost model is the ideal device: scored on a device with crosstalk and 4-bit
phase the uniformity drops (the reason for M13 and BS-1). The simulated annealing variant of the source is not implemented (the
source gives no quantitative result for it).

## References

- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
