# M03, Random mask encoding

| Item | Value |
|---|---|
| Family | analytic baseline |
| Lane | live |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m03_random_mask.py`, `SPEC` line 26, `run` line 40 |
| Anchor | Montes-Usategui et al. 2006; Di Leonardo et al. 2007, Table 1 |

## Purpose

Split the SLM into disjoint random subdomains, one per trap, and let each pixel show the hologram of its trap only. Every trap
gets an equal share of the aperture, so the traps are close to equal in brightness; the price is that only about $1/M$ of the
light goes to the traps.

## Equations

$$\phi_j = \Delta_j^{m(j)}, \qquad I_l \cap I_m = \emptyset, \quad \textstyle\bigcup_k I_k = \text{SLM}$$

The partition is a random permutation of the pixels drawn through the portable generator (uniform keys, sorted), with equal
shares of $N/M$ pixels (a share proportional to the trap weight when the weights differ). Source of the assignment rule:
Montes-Usategui, Pleguezuelos, Andilla and Martin-Badosa, Opt. Express 14, 2101, Eqs. (4) to (6),
https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101 . The per-pixel independent draw of Di Leonardo 2007, Table 1,
is the same method with a binomial instead of an exact share. Published on the 10 by 10 task at 768 by 768 pixels: efficiency
0.01 (about $1/M$), uniformity 0.58, relative standard deviation 16 percent.

## Implementation

Defaults: none. `meta["owner"]` is the `n_pix` by `n_pix` array of trap indices. The partition is built by `_owner` (line 29).

## Acceptance criterion and test

Efficiency about $1/M$; at the source's 768 by 768 grid, uniformity within the spread of 0.58:
`tests/methods/baseline/test_m03_random_mask.py::test_acceptance_10x10_over_seeds` and `::test_published_grid_768_reproduces_uniformity`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Grid | Efficiency | Uniformity | Seeds |
|---|---|---|---|
| 768 by 768 pixels (the published grid) | 0.008 | 0.566 [0.543, 0.590] | 2 |
| 256 by 256 pixels (the live grid) | 0.010 | 0.057 [0.031, 0.072] | 5 |

The published numbers (0.01 and 0.58) are reproduced on the grid they were measured on, which validates the implementation. On
the live grid there are 9 times fewer pixels per trap and the uniformity falls: the method depends on the pixel count per trap.

## Limits

Efficiency about $1/M$; the result depends strongly on the number of pixels per trap.

## References

- Montes-Usategui et al. 2006, Opt. Express 14, 2101, https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101
- Di Leonardo, Ianni and Ruocco 2007, https://doi.org/10.1364/OE.15.001913
