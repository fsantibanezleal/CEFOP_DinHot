# M09, Direct search

| Item | Value |
|---|---|
| Family | optimization |
| Lane | baked |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/optim/m09_direct_search.py`, `SPEC` line 39, `run` line 55 |
| Anchor | Polin, Hovhannisyan and Sorensen, Opt. Express 13, 5831 (2005) |

## Purpose

Visit every SLM pixel in random order, try every phase level, keep the best. It optimises an explicit cost that trades
efficiency against uniformity with one weight, and it reaches near-perfect uniformity even where GS stalls.

## Equations

With $I_m$ the trap intensities, $I^D_m = w_m/\operatorname{mean}(w)$ the design intensities and $M$ the trap count:

$$C = -\langle I\rangle + f\,\sigma, \qquad \sigma = \sqrt{\frac1M\sum_m (I_m - \gamma I^D_m)^2}, \qquad
\gamma = \frac{\sum_m I_m I^D_m}{\sum_m (I^D_m)^2}$$

(`polin_cost`, line 46). $f$ weights uniformity against efficiency. Source: Polin et al. 2005, Eqs. (11) to (13),
https://doi.org/10.1364/OPEX.13.005831 ; the benchmark numbers on the 10 by 10 task are Di Leonardo et al. 2007
(direct search from SR, $f = 0.5$: uniformity 1.00, efficiency 0.68 after 1.3 N steps), https://doi.org/10.1364/OE.15.001913 .

One sweep visits every pixel once in a seeded random order; at each pixel all $P$ trial phases $2\pi k/P$ are evaluated and the best
is kept if it lowers the cost, so the cost never increases. The trap fields are updated incrementally: a change
$dz = e^{i\phi'} - e^{i\phi}$ at pixel $j$ changes $V_m$ by $(A_j/N_{pix})\,dz\,e^{-i\Delta_j^m}$, an $O(M)$ update (point-trap form, any trap $z$
and vortex charge). Polin: convergence in about $N$ trials, worst case $NP$.

## Implementation

Defaults (`m09_direct_search.py`, lines 41 to 43): `levels = 8` (the 8 grey levels of the source row), `f = 0.5`, 2 sweeps;
`budget.iterations` is the number of sweeps and `max_trials` caps the trial phases. The start is the SR superposition rounded to the
$P$ levels (`init` overrides). The optimisation uses the ideal point-trap model: a device is not part of the model of M09.

## Acceptance criterion and test

Uniformity at least 0.98 on the 10 by 10 task; under 5 percent rms variation on a quasi-periodic 119-trap set:
`tests/methods/optim/test_m09_direct_search.py::test_acceptance_uniformity_on_the_10x10_task` and
`::test_acceptance_rms_variation_on_the_quasi_periodic_set`. The incremental update equals a full evaluation to 1e-10 and the cost
never rises.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Reference | Conditions |
|---|---|---|---|
| Uniformity, 10 by 10 task | 0.9994, 0.9992 (efficiency 0.66, 0.65) | GS 0.55 to 0.62 | 2 seeds, 256 by 256 padded 2 |
| Relative standard deviation, 119 quasi-periodic traps | 0.023 percent | paper: GS and AA above 50 percent (not run here) | 1 seed |

The quasi-periodic set is DinHot's own (a product of two Fibonacci chains); the exact geometry of Polin et al. is not published as
coordinates.

## Limits

Sequential, stuck in local minima, ghost traps absorb efficiency (Polin; Di Leonardo). The cost is baked, not live: a sweep touches
$N$ pixels.

## References

- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
