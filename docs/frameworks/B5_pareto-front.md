# B5, Efficiency-uniformity Pareto front (beyond the published state of the art)

| Item | Value |
|---|---|
| Family | beyond, multi-objective |
| Lane | baked |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/beyond/b5_pareto.py`, `SPEC` line 40, `run` line 94 |
| Gap | methods report single trade-off points, never a front on the same task |

## Purpose

Every method trades efficiency against uniformity and publishes one point of that trade-off. B5 computes the whole front by continuation, so a reader sees what each extra percent of
uniformity costs in light, and where the other methods sit relative to it.

## The gap

Di Leonardo et al. 2007 report direct search at $f = 0.5$ and $0.25$ and GAA at 0.5 (https://doi.org/10.1364/OE.15.001913 ); Polin et al. 2005 use one scalar weight $f$
(https://doi.org/10.1364/OPEX.13.005831 ); MRAF has one mixing parameter. No source read reports a whole front on the same task.

## Method

Continuation over $\lambda\in[0,1]$ of the loss

$$L_\lambda(\phi) = (1-\lambda)\,\frac{\sum_m(I_m - T_m)^2}{\sum_m T_m^2} \;-\; \lambda\,\frac{\sum_m I_m}{e_0}, \qquad T_m = e_0\,\frac{w_m}{\sum_k w_k}$$

with $I_m = |V_m|^2$ and $e_0$ the efficiency of the weighted-GS hologram at the uniform end. The research form writes $(1-\lambda)\sum(|V|^2 - w_mT_m)^2 - \lambda\sum|V|^2$; the two terms
are divided by $\sum T^2$ and $e_0$ so that both are dimensionless and of order one (UNVERIFIED reading: the scaling is not stated in the source). The start ($\lambda = 0$) is
phase-fixed WGS, refined by the same CG; each next $\lambda$ is warm-started from its neighbour and solved with `budget.iterations` Fletcher-Reeves and strong-Wolfe CG iterations. The gradient is the closed
form $G_m = [2(1-\lambda)(I_m - T_m)/\sum T^2 - \lambda/e_0]\,V_m$ pulled back by the point-trap adjoint (any trap $z$ and vortex charge; the ideal device).

## Implementation

Defaults (`b5_pareto.py`, lines 42 and 43): `n_lambda = 20`, `warm = 30`. `run` returns the point with the largest $e\cdot u$ (the knee of the front) as `phi`, and in `meta`: `lambdas`,
`front` (the $(e, u, \sigma)$ of every $\lambda$), `pareto` (indices of the non-dominated points), `hypervolume` against the reference point $(0, 0)$ and `phis` (all holograms).
`hypervolume` and `pareto_indices` are public for the benchmark.

## Acceptance criterion and test

Hypervolume at least that of the M04, M05, M09 and M06 points on the 10 by 10 task, with the front dominating M04 and M05 and computed in under 60 s:
`tests/methods/beyond/test_b5_pareto.py::test_acceptance_hypervolume_and_domination_on_the_10x10_task`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Front, uniform end to efficient end (efficiency, uniformity) | from (0.790, 1.000) to (0.8305, 0.094) | 20 values of lambda, 15 CG iterations each, 1 seed, measured before the 2026-10-29 rule corrections |
| Hypervolume | 0.8190 against 0.8018 for the union of the M04, M05, M09 and M06 points (0.8201 against 0.8033 before the corrections) | re-measured 2026-10-29 |
| Domination | 7 front points dominate M04 (0.8114, 0.5503) and 8 dominate M05 (0.8086, 0.7093) | re-measured 2026-10-29 |
| Time | 16.6 s | under contention on the development workstation, 2026-10-29; limit 60 s |

## Limits

The loss scaling is DinHot's reading (UNVERIFIED); the front is computed with the ideal device; the hypervolume depends on the reference point.

## References

- Di Leonardo, Ianni and Ruocco 2007, https://doi.org/10.1364/OE.15.001913
- Polin, Hovhannisyan and Sorensen 2005, https://doi.org/10.1364/OPEX.13.005831
- Kim et al. 2019 (the phase-fixed start), https://doi.org/10.1364/OL.44.003178
