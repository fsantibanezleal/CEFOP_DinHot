# BS-5: Efficiency-uniformity Pareto front (engine id B5)

| Item | Value |
|---|---|
| Ladder row | BS-5, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, multi-objective, baked |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b5_pareto.py` (`SPEC` line 40, `pareto_indices` line 46, `hypervolume` line 57, `_FrontCost` line 74, `run` line 94) |
| Gate | `tests/methods/beyond/test_b5_pareto.py` |
| Live port | none (lane `baked`; `getMethod('B5')` raises `NotLive`) |
| Card | [B5](../../frameworks/B5_pareto-front.md) |
| Outcome | hypothesis confirmed on the ladder criterion (hypervolume 0.8190 against 0.8018 after the 2026-10-29 rule corrections, 0.8201 against 0.8033 before; the front dominates M04 and M05, 16.6 s); the margin is small |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** Every method trades efficiency against uniformity and reports single points of that trade-off. A continuation over a trade-off parameter $\lambda\in[0,1]$ of one loss, warm-started from
the neighbouring value, computes the whole front on the same task. Its hypervolume in the (efficiency, uniformity) plane is at least that of the union of the classical single points (GS, GAA, direct search,
weighted GS), at least one front point dominates each of GS and GAA, and it is computed in under 60 s on the CPU for the 10x10 task.

**The gap.** Di Leonardo et al. 2007 report direct search at $f = 0.5$ and $0.25$ and GAA at 0.5 (https://doi.org/10.1364/OE.15.001913); Polin et al. 2005 use one scalar weight $f$
(https://doi.org/10.1364/OPEX.13.005831); MRAF has one mixing parameter. No source read reports a whole front on the same task (algorithms dossier D5.1 B5). The dossier names the risk that the
weighted-GS point is already near (0.93, 0.99), so the front may be flat and its useful region is the large or device-affected cases.

## Problem it answers

Show what each extra percent of uniformity costs in light, and where the other methods sit relative to the best attainable trade-off.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`), `budget` (`iterations` is the number of CG iterations per $\lambda$), `rng`, optional `init`,
  `n_lambda` (at least 2), `warm`. The ideal device (the point-trap model; any trap $z$ and vortex charge). `device` is accepted and ignored.
- Output: `Result` with `phi` the front point of largest $e\cdot u$ (the knee), one `history` entry per $\lambda$ (with `lam`), `fields` the knee's trap fields, and `meta`: `lambdas`, `front` (the
  $(e, u, \sigma)$ of every $\lambda$), `pareto` (indices of the non-dominated points), `hypervolume` against the reference point $(0, 0)$, `knee`, `phis` (all holograms), `e0`.
  `hypervolume` and `pareto_indices` are public for the benchmark.

## The method

Continuation over $\lambda\in[0,1]$ of the loss

$$L_\lambda(\phi) = (1-\lambda)\,\frac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2}\;-\;\lambda\,\frac{\sum_m I_m}{e_0},\qquad T_m = e_0\,\frac{w_m}{\sum_k w_k},$$

with $I_m = |V_m|^2$ and $e_0$ the efficiency of the weighted-GS hologram at the uniform end. The research record writes $(1-\lambda)\sum(|V|^2 - w_mT_m)^2 - \lambda\sum|V|^2$; the two terms are divided by
$\sum T^2$ and $e_0$ so that both are dimensionless and of order one (UNVERIFIED reading: the scaling is not stated in the record). The start ($\lambda = 0$) is phase-fixed WGS (`warm` = 30 iterations,
`pfwgs`), refined by the same conjugate gradient; each next $\lambda$ is warm-started from its neighbour and solved with `budget.iterations` Fletcher-Reeves and strong-Wolfe CG iterations
(`_common.cg_minimize`). The gradient is the closed form $G_m = [2(1-\lambda)(I_m - T_m)/\sum T^2 - \lambda/e_0]\,V_m$ pulled back by the point-trap adjoint (`_FrontCost.value_grad`, lines 84 to 91).

Metrics of the front (`b5_pareto.py`): `pareto_indices` keeps the non-dominated rows (both columns maximized); the hypervolume is the area of the union of the rectangles $[0, p]$ over the points
$p = (e, u)$, computed by a sweep over the points sorted by efficiency (lines 57 to 71).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `n_lambda` | 20 values of $\lambda$ in $[0, 1]$ (`np.linspace`) | `b5_pareto.py` line 42 | the research record: 10 to 20 values times a warm-started run |
| `warm` | 30 phase-fixed WGS iterations | line 43 | the start of the uniform end |
| CG iterations per $\lambda$ | `budget.iterations`; 15 in the acceptance test | `run`, line 118 | the test's budget |
| reference point of the hypervolume | $(0, 0)$ | line 57 | the usual one for two maximized objectives |
| knee | the largest $e\cdot u$ | line 126 | DinHot's choice of the representative point |

## Complexity and lane

$n_\lambda$ warm-started CG runs of `budget.iterations` iterations each, one forward and adjoint evaluation per line-search step. Lane `baked` (`SPEC`, line 40). The acceptance test takes about 40 s and the front
itself 24.9 s on the development machine under contention; the limit of the test is 60 s.

## Acceptance criterion and gate

Ladder row: hypervolume at least that of the M04, M05, M09 and M06 points on the 10x10 task. Gate `tests/methods/beyond/test_b5_pareto.py::test_acceptance_hypervolume_and_domination_on_the_10x10_task`: the 10x10 task on
256 by 256 padded 2; the baseline points are GS, GAA and weighted GS at 30 iterations (the in-test family, seed 1) and direct search with one sweep (seed 1), each evaluated by the metrics `(e, u)`; B5 with
`Budget(15)` and 20 values of $\lambda$, seed 1; the front's hypervolume at least that of the baseline points, at least one front point with $e \ge e_b$ and $u > u_b$ for each of M04 and M05, and under 60 s. Other tests:
hypervolume on known values, the Pareto indices, the front gradient against finite differences, the front is monotone in the trade-off on a small array, a shaped field is refused, determinism.

## Evaluation that confirms or refutes it

Confirmed if the hypervolume of the front is at least that of the classical points and the front dominates GS and GAA; refuted if the front is dominated by the classical points (the continuation would add nothing).
The criterion is one-sided and the margin is small: the test cannot distinguish a front that is the same as a single good point. The hypervolume with the reference point $(0, 0)$ is dominated by the region of
high uniformity, where the weighted-GS point already sits.

## Measured result

Acceptance run of 2026-10-28 (E3 report D4 and D5), 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), 1 seed, 20 values of $\lambda$, 15 CG iterations each:

| Quantity | Measured |
|---|---|
| Front, from the uniform end to the efficient end (efficiency, uniformity) | from (0.790, 1.000) to (0.8305, 0.094) |
| Hypervolume | 0.8201 against 0.8033 for the union of the baseline points (a margin of 2.1 percent, computed) |
| Domination | one front point dominates M04 (0.8114, 0.5503) and M05 (0.8086, 0.7093) |
| Time | 24.9 s (limit 60 s), under contention on the development machine |

Outcome: confirmed under the ladder criterion. The efficiency changes by only 0.04 across the whole front while the uniformity falls from 1 to 0.09: on this task the trade-off is steep and the useful part of the front
is the high-uniformity end, which is the risk the dossier named (a flat front).

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own optics, listed in `data/derived/manifests/`; the `Iterations` column is the number of
values of $\lambda$ (20), the bake returns the knee):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 20 | 0.801 (0.77 to 0.817) | 0.999 (0.998 to 1) | 0.0318 (4.95e-11 to 0.0955) |
| C02 | 20 | 0.8 (0.796 to 0.805) | 0.995 (0.985 to 1) | 0.224 (8.62e-09 to 0.671) |
| C05 | 20 | 0.898 (0.893 to 0.904) | 0.984 (0.976 to 0.991) | 0.712 (0.482 to 0.983) |
| C07 | 20 | 0.795 (0.787 to 0.799) | 0.997 (0.995 to 1) | 0.172 (2.5e-12 to 0.278) |

On C02 the knee has a relative standard deviation of 0.67 percent or below against 0.6 to 1.3 percent for M06, at the same efficiency (0.80); on C05 (3D) its efficiency is 0.90 against 0.89.

## Limits and failure modes

- The loss scaling is DinHot's reading (UNVERIFIED); the front is computed with the ideal device, so it does not apply to a device-limited case.
- The hypervolume depends on the reference point and is dominated by the high-uniformity region.
- One seed in the acceptance test; the benchmark protocol repeats it over 20 seeds (its rows are not yet in `data/derived/benchmark/results.json`).
- The front is computed for one task and one setup; a different geometry gives a different front.
- Time depends on the machine (24.9 s under contention).

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 (the phase-fixed start)

## Update after the corrections of 2026-10-29

Re-measured after M06 and M07 were made to project the start's field unweighted and the GS family of the beyond methods was made the ladder methods' own rules: on the acceptance task the front's hypervolume is 0.8190 against 0.8018 for the M04, M05, M06 and M09 points, and 7 and 8 front points dominate M04 (0.8114, 0.5503) and M05 (0.8086, 0.7093); 16.6 s on the CPU. The criterion holds. In notebook 05-05 the front starts from M07's own hologram, so its uniform end is M07 refined and M07 is not dominated (0.7931 against 0.7930 at equal uniformity); the other five single points are.
