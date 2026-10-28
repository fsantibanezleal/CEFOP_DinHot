# M06, Weighted Gerchberg-Saxton (GSW)

| Item | Value |
|---|---|
| Family | GS |
| Lane | live |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m06_gsw.py`, `SPEC` line 18, `run` line 21; engine `_gs.py` |
| Anchor | Di Leonardo, Ianni and Ruocco 2007, Eq. (18) |

## Purpose

GS with integral feedback on the trap weights: each iteration the weight of a trap is multiplied by the ratio between the mean
amplitude and its own, so dark traps are boosted and bright traps are damped. It reaches high efficiency and high uniformity
together, and is the weighted base of M07, M12, M14, M15 and the starts of several optimizers.

## Equations

Started from the SR hologram with $w_m^0 = 1$:

$$w_m^k = w_m^{k-1}\,\frac{\langle |V^{k-1}| \rangle}{|V_m^{k-1}|}, \qquad
\phi_j^k = \arg \sum_m e^{+i\Delta_j^m}\; w_m^k\,\frac{V_m^{k-1}}{|V_m^{k-1}|}$$

With target weights: $a_m = \sqrt{w_m^{target}}$, $w_m^0 = a_m$ and $|V_m|$ is replaced by $|V_m|/a_m$ (identical for equal weights).
Source: Di Leonardo et al. 2007, Eq. (18) and the iteration that follows, https://doi.org/10.1364/OE.15.001913 . Published: efficiency
0.93 and uniformity 0.99 after 30 iterations, above 0.9 in about 10 iterations; 3 by 3 by 3 lattice 0.91 and 0.99.

## Implementation

Defaults (`run`, line 21): `form = "point"`. The FFT form is available for large arrays (traps on bins, $z = 0$, no vortex).

## Acceptance criterion and test

Efficiency and uniformity at least 0.9 within a median of 15 iterations on the 10 by 10 task with a flat beam (the source reports
about 10); the 3 by 3 by 3 lattice above 0.9 and 0.98:
`tests/methods/baseline/test_m06_gsw.py::test_acceptance_10x10_flat_beam`, `::test_acceptance_10x10_gaussian_beam` (against 0.9 of
the beam ceiling) and `::test_acceptance_3x3x3_lattice`. Target weights are honoured: a 2:1 weight gives an intensity ratio
of 2.0 plus or minus 0.1 and a uniformity of $I/w$ above 0.95.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| First iteration with efficiency and uniformity both at 0.9 | 10, 13, 12 (flat beam); 10, 12, 12 (Gaussian, against 0.9 of the ceiling) | seeds 1, 2, 3, 256 by 256 padded 2, 10 by 10 task |
| Uniformity at iteration 10 | 0.887 [0.861, 0.910] | same |
| 3 by 3 by 3 lattice | efficiency above 0.9 and uniformity above 0.98, first reached at iteration 32, 16, 24 (not monotonic) | 3 seeds |

The paper reaches 0.9 at iteration 10 on a 768 by 768 grid; on the 256 grid it is reached at iteration 10 to 13, so the SDD bar is
set at a median of 15.

## Limits

Convergence is slightly slower on the small grid than in the source. Efficiency is capped by the beam ceiling for a Gaussian beam.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
