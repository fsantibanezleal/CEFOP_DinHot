# BS-5: Efficiency-uniformity continuation (engine id B5)

| Item | Value |
|---|---|
| Ladder row | BS-5, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, multi-objective, baked |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b5_pareto.py` (`SPEC` line 40, `pareto_indices` line 46, `hypervolume` line 57, `_FrontCost` line 74, `run` line 94) |
| Gate | `tests/methods/beyond/test_b5_pareto.py` |
| Live port | none (lane `baked`; `getMethod('B5')` raises `NotLive`) |
| Card | [B5](../../frameworks/B5_pareto-front.md) |
| Outcome (0.02.004) | the ladder criterion is met by a small margin, and the gain is small and shrinks at a stricter reference point: over 8 seeds a hypervolume of 0.8223 against 0.8104 for the union of the five published points (a paired difference of 0.0119, 95 percent interval 0.0097 to 0.0141), and 0.0015 (12.4 percent of it) when the reference point demands a uniformity of 0.9; the curve is not the non-dominated set of the trade-off (4 to 7 of its 20 points are dominated by iterates of weighted GS); in the benchmark every cell is a tie by the win rule because the stored curves hold one seed, and the stored curve is above the union of the published points on 3 of 7 geometries at 100 iterations and on 5 of 7 at 30 |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Name.** The method is a weighted-cost continuation of the efficiency-uniformity trade-off, and its points are not the Pareto front: its own paper (Zenodo 10.5281/zenodo.24022463) finds 4 to 7 of its 20 points dominated by iterates of weighted GS run for 100 iterations. The id `B5`, this file's name and the `pareto` key of `benchmark-results` are identifiers and keep their spelling; the reader text says "continuation". "Pareto front" is kept only for the non-dominated set computed from measured points (`pareto_indices`, the Story page's front of the methods' medians).

**Hypothesis.** Every method trades efficiency against uniformity and reports single points of that trade-off. A continuation over a trade-off parameter $\lambda\in[0,1]$ of one loss, warm-started from
the neighbouring value, computes the whole curve on the same task. Its hypervolume in the (efficiency, uniformity) plane is at least that of the union of the classical single points (GS, GAA, direct search,
weighted GS), at least one continuation point dominates each of GS and GAA, and it is computed in under 60 s on the CPU for the 10x10 task.

**The gap.** Di Leonardo et al. 2007 report direct search at $f = 0.5$ and $0.25$ and GAA at 0.5 (https://doi.org/10.1364/OE.15.001913); Polin et al. 2005 use one scalar weight $f$
(https://doi.org/10.1364/OPEX.13.005831); MRAF has one mixing parameter. No source read reports a whole curve on the same task (algorithms dossier D5.1 B5). The dossier names the risk that the
weighted-GS point is already near (0.93, 0.99), so the continuation curve may be flat and its useful region is the large or device-affected cases.

## Problem it answers

Show what each extra percent of uniformity costs in light, and where the other methods sit relative to the best attainable trade-off.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`), `budget` (`iterations` is the number of CG iterations per $\lambda$), `rng`, optional `init`,
  `n_lambda` (at least 2), `warm`. The ideal device (the point-trap model; any trap $z$ and vortex charge). `device` is accepted and ignored.
- Output: `Result` with `phi` the continuation point of largest $e\cdot u$ (the knee), one `history` entry per $\lambda$ (with `lam`), `fields` the knee's trap fields, and `meta`: `lambdas`, `front` (the
  $(e, u, \sigma)$ of every $\lambda$), `pareto` (indices of the non-dominated points), `hypervolume` against the reference point $(0, 0)$, `knee`, `phis` (all holograms), `e0`.
  `hypervolume` and `pareto_indices` are public for the benchmark.

## The method

Continuation over $\lambda\in[0,1]$ of the loss

$$L_\lambda(\phi) = (1-\lambda)\,\frac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2}\;-\;\lambda\,\frac{\sum_m I_m}{e_0},\qquad T_m = e_0\,\frac{w_m}{\sum_k w_k},$$

with $I_m = |V_m|^2$ and $e_0$ the efficiency of the weighted-GS hologram at the uniform end. The research record writes $(1-\lambda)\sum(|V|^2 - w_mT_m)^2 - \lambda\sum|V|^2$; the two terms are divided by
$\sum T^2$ and $e_0$ so that both are dimensionless and of order one (DinHot's scaling, part of the method's definition: the record states none). The start ($\lambda = 0$) is phase-fixed WGS (`warm` = 30 iterations,
`pfwgs`), refined by the same conjugate gradient; each next $\lambda$ is warm-started from its neighbour and solved with `budget.iterations` Fletcher-Reeves and strong-Wolfe CG iterations
(`_common.cg_minimize`). The gradient is the closed form $G_m = [2(1-\lambda)(I_m - T_m)/\sum T^2 - \lambda/e_0]\,V_m$ pulled back by the point-trap adjoint (`_FrontCost.value_grad`, lines 84 to 91).

Metrics of the continuation curve (`b5_pareto.py`): `pareto_indices` keeps the non-dominated rows (both columns maximized); the hypervolume is the area of the union of the rectangles $[0, p]$ over the points
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

$n_\lambda$ warm-started CG runs of `budget.iterations` iterations each, one forward and adjoint evaluation per line-search step. Lane `baked` (`SPEC`, line 40). The acceptance test takes about 40 s and the continuation curve
itself 24.9 s on the development machine under contention; the limit of the test is 60 s.

## Acceptance criterion and gate

Ladder row: hypervolume at least that of the M04, M05, M09 and M06 points on the 10x10 task. Gate `tests/methods/beyond/test_b5_pareto.py::test_acceptance_hypervolume_and_domination_on_the_10x10_task`: the 10x10 task on
256 by 256 padded 2; the baseline points are GS, GAA and weighted GS at 30 iterations (the in-test family, seed 1) and direct search with one sweep (seed 1), each evaluated by the metrics `(e, u)`; B5 with
`Budget(15)` and 20 values of $\lambda$, seed 1; the continuation curve's hypervolume at least that of the baseline points, at least one continuation point with $e \ge e_b$ and $u > u_b$ for each of M04 and M05, and under 60 s. Other tests:
hypervolume on known values, the Pareto indices, the continuation curve gradient against finite differences, the continuation curve is monotone in the trade-off on a small array, a shaped field is refused, determinism.

## Evaluation that confirms or refutes it

Confirmed if the hypervolume of the continuation curve is at least that of the classical points and the continuation points dominate GS and GAA; refuted if the continuation points are dominated by the classical points (the continuation would add nothing).
The criterion is one-sided and the margin is small: the test cannot distinguish a curve that is the same as a single good point. The hypervolume with the reference point $(0, 0)$ is dominated by the region of
high uniformity, where the weighted-GS point already sits.

## Measured result

Values of the 0.02.004 generation, from `manuscripts/efficiency-uniformity-front/data/b5_numbers.tex` (10 by 10 lattice of 100 traps, 8 seeds, 20 values of lambda, 15 CG iterations each, ideal device, simulated) and `manuscripts/holographic-trap-studio/data/studio_numbers.tex` (the benchmark):

| Quantity | Measured (macros) |
|---|---|
| Hypervolume of the curve and of the union of the five published points (GS, GAA, weighted GS, phase-fixed WGS, direct search), reference (0, 0) | 0.8223 against 0.8104; paired difference 0.0119 (0.0097 to 0.0141), positive in 8 of 8 seeds, 1.47 percent of the union (`hvFront`, `hvFivePub`, `hvFiveDiff`, `hvFiveLo`, `hvFiveHi`, `hvFiveGe`, `hvFiveRatioPct`) |
| Against the four-point union of the acceptance criterion (M04, M05, M09 and M06, without phase-fixed WGS) | 0.8223 against 0.8071; difference 0.0152 (0.0125 to 0.0179), positive in 8 of 8 seeds (`hvFourPub`, `hvFourDiff`, `hvFourLo`, `hvFourHi`, `hvFourGe`) |
| Difference at the reference points (0.5, 0), (0.7, 0), (0, 0.9) and (0, 0.95), five-point union | 0.0117, 0.0113, 0.0015 (0.0008 to 0.0022) and 0.0011 (0.0005 to 0.0018): 97.9, 95.2, 12.4 and 9.6 percent of the headline difference; against the four points the shares at the two uniformity floors are 31.3 and 29.1 percent (`hvRefFive*Diff`, `hvRefFive*Share`, `hvRefFour*Share`) |
| Efficiency along the curve | rises from 0.793 to 0.8356, at most 5.4 percent over the start, while the uniformity falls from 1.000 to 0.015 (`eStart`, `eMaxFront`, `eMaxRatioPct`, `uMinFront`) |
| Domination | the curve dominates the weighted GS point in 2 of 8 seeds and the phase-fixed point in 3 of 8; 4 to 7 of its 20 points (a mean of 5.1) are dominated by iterates of weighted GS (`domGSWSeeds`, `domPFSeeds`, `frontDomMin`, `frontDomMax`, `frontDomMean`) |
| Benchmark (1404 rows, 20 seeds) | 14 cells (7 geometries at 30 and at 100 iterations), all ties by the win rule (one seed behind each stored curve); at 100 iterations the stored curve reaches the hypervolume of the published points on 3 of 7 geometries and loses on G1 (0.837 against 0.839), G4 (0.771 against 0.772), G6a (0.791 against 0.812) and G6b (0.725 against 0.748), by at most 0.023; at 30 iterations it reaches it on 5 of 7 (`benchFivePass`, `benchFiveN`, `benchFivePassThirty`, `benchFiveLost`, `benchFiveMargin`) |

Outcome: the ladder criterion is met by a small margin (a hypervolume gain of 1.47 percent against the five-point union), and the gain is small and shrinks at a stricter reference point: the area that the curve adds lies where the uniformity falls far below one, so a reader who requires a uniformity of 0.9 or more sees a gain that is a small share of the headline. On this task the trade-off is steep (the efficiency changes by 0.043 across the whole curve while the uniformity falls from 1 to 0.015) and the useful part of the curve is the high-uniformity end, which is the flat-curve risk the dossier named.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own optics, listed in `data/derived/manifests/`; the `Iterations` column is the number of
values of $\lambda$ (20), the bake returns the knee):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 20 | 0.801 (0.77 to 0.817) | 1 (0.999 to 1) | 0.031 (1.45e-11 to 0.0929) |
| C02 | 20 | 0.803 (0.798 to 0.811) | 0.989 (0.976 to 1) | 0.528 (4.39e-08 to 1.13) |
| C05 | 20 | 0.895 (0.889 to 0.901) | 0.985 (0.981 to 0.989) | 0.659 (0.507 to 0.82) |
| C07 | 20 | 0.799 (0.795 to 0.803) | 0.99 (0.982 to 0.995) | 0.545 (0.246 to 0.993) |

On C02 the knee has a relative standard deviation of 0.67 percent or below against 0.6 to 1.3 percent for M06, at the same efficiency (0.80); on C05 (3D) its efficiency is 0.90 against 0.89.

## Limits and failure modes

- The loss scaling is DinHot's, part of the method's definition; the continuation curve is computed with the ideal device, so it does not apply to a device-limited case.
- The hypervolume depends on the reference point and is dominated by the high-uniformity region.
- One seed in the acceptance test; the benchmark protocol repeats it over 20 seeds (its rows are not yet in `data/derived/benchmark/results.json`).
- The continuation curve is computed for one task and one setup; a different geometry gives a different curve.
- Time depends on the machine (24.9 s under contention).

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Polin, Ladavac, Lee, Roichman and Grier 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
- Kim, Keesling, Omran, Levine, Bernien, Greiner, Lukin and Englund 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 (the phase-fixed start)

## History and reading (0.02.004)

The acceptance runs of 2026-10-28 and 2026-10-29 (one seed of the gate test, before and after M06 and M07 projected the start's field unweighted and the GS family of the beyond methods took the ladder methods' own rules) are superseded by the measured result above and are kept in the git history of this file; the gate test (`tests/methods/beyond/test_b5_pareto.py`) still asserts the criterion on its own seed, and its single-seed figures are not re-recorded here because no committed data file holds them.

Reading: the curve is a weighted-cost continuation of the trade-off, not its non-dominated set, and it is computed for the ideal device, not for the device that displays the hologram.
