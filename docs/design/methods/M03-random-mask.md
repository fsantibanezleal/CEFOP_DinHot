# M03: Random mask

| Item | Value |
|---|---|
| Ladder row | M03, tier classical (SDD, Method ladder) |
| Family, lane | analytic, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m03_random_mask.py` (`SPEC` line 26, `_owner` line 29, `run` line 40) |
| Gate | `tests/methods/baseline/test_m03_random_mask.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m03`, line 67) |
| Card | [M03](../../frameworks/M03_random-mask.md) |

## Tier and role

The established non-iterative method of the Barcelona group: split the SLM into disjoint random subdomains, one per trap, and let
each pixel show the hologram of its own trap only. It is a baseline because it is the oldest fully equal-share encoding and the
counter-example to M01: its traps are close to equal in brightness, and the price is that only about $1/M$ of the light reaches
them. Source of the assignment rule: Montes-Usategui, Pleguezuelos, Andilla and Martin-Badosa, Opt. Express 14, 2101, Eqs. (4) to
(6) (https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101); the benchmark numbers are Di Leonardo et al. 2007, Table 1
(https://doi.org/10.1364/OE.15.001913).

## Problem it answers

Equal-brightness traps from a single pass with no iteration, at a low and known efficiency; the physics bound it demonstrates is
that a random mask reaches an efficiency about the inverse of the trap count (an oracle of the SDD).

## Inputs and outputs

- Input: a `Target` of kind `traps` (a shaped target is refused naming `traps`); `setup` with `n_pix` (the partition is over the
  `n_pix` squared pixels). `device`, `init` ignored. Randomness through `rng` (`rng.uniform_array(n)`, the portable generator).
- Output: `phi` (float64, `n_pix` by `n_pix`, wrapped to $[0, 2\pi)$ by `core.geometry.wrap_phase`), `fields`, a one-entry
  `history`, and `meta['owner']`, the `n_pix` by `n_pix` integer array of the trap that owns each pixel.

## The method

The pixels are partitioned into disjoint random subdomains $I_k$ of equal share $N/M$ (a share proportional to the trap weight when
the weights differ), and each pixel shows the phase of its trap:

$$\phi_j = \Delta_j^{m(j)},\qquad I_l \cap I_m = \emptyset,\qquad \textstyle\bigcup_k I_k = \text{SLM}$$

with $\Delta_j^m$ the delay of M01 (lens, grating and vortex terms: `grating_phase`, `lens_phase`, `vortex_phase` of `core/modes.py`,
assembled at `m03_random_mask.py` lines 50 to 54). The partition `_owner` is a random permutation of the pixels (the sort order of
uniform keys, lines 30 and 31) cut at the cumulative weight edges (`np.rint(cumsum(w)/sum(w) * n)`, line 32), so the shares are
exact and not binomial. The independent per-pixel draw $\phi_j = \Delta_j^{m_j}$ of Di Leonardo et al. 2007, Table 1, is the same
method with a binomial share instead of an exact one. The source for the encoding is Montes-Usategui et al. 2006 (Eqs. (4) to (6));
the equations were taken from the research record of the gap study, not from a second reading.

## Defaults

None (`run`, line 40). The share per trap is $N/M$ for equal weights.

## Complexity and lane

Cost $O(N)$ for the permutation plus $O(N)$ per trap to build its delay on its own pixels. Lane `live` (`SPEC`, line 26); the
TypeScript port is `m03` (`frontend/src/engine/holo/methods/baseline.ts` line 67) and agrees with the Python engine under the parity
test (worst difference 1.8e-13, T1 report D2).

## Acceptance criterion and gate

Ladder row: efficiency about $1/M$; at the source's 768 squared grid, uniformity within the spread of 0.58. Gate:
`tests/methods/baseline/test_m03_random_mask.py::test_acceptance_10x10_over_seeds` (seeds 0 to 4 on the 256 by 256 padded-2 grid:
$0.5/M < e < 2/M$ and $0 < u < 0.30$) and `::test_published_grid_768_reproduces_uniformity` (two seeds on 768 by 768 padded 2:
$|u - 0.58| \le 0.10$ and $0.005 < e < 0.02$). Structural tests: the masks are disjoint and of equal share, and each pixel shows
its trap's phase.

## Evaluation that confirms or refutes it

Confirmed if the efficiency is about $1/M$ on both grids and the published uniformity of 0.58 is reproduced on the grid it was
measured on; the 768 test validates the implementation of the encoding. It would be refuted if the efficiency left the
$[0.5/M, 2/M]$ band (the partition would not be an equal share) or if the 768 uniformity missed 0.58 by more than 0.10.

## Measured result

Acceptance run of 2026-10-28 (E2 report D1 and D5), test setup (850 nm, focal length 250 mm, pitch 12.5 um, Gaussian beam of waist
fraction 1), 10x10 task 8 bins apart, $M = 100$:

| Grid | Efficiency | Uniformity | Seeds |
|---|---|---|---|
| 768 by 768 padded 2 (the published grid) | 0.008 | 0.566 [0.543, 0.590] | 2 |
| 256 by 256 padded 2 (the live grid) | 0.010 | 0.057 [0.031, 0.072] | 5 |

Published (Table 1): efficiency 0.01, uniformity 0.58, relative standard deviation 16 percent at 768 by 768. The published numbers
are reproduced on the grid they were measured on; on the live grid there are 9 times fewer pixels per trap and the uniformity
falls.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 1 | 0.0929 (0.0914 to 0.0941) | 0.928 (0.909 to 0.96) | 4.38 (3.23 to 5.72) |
| C02 | 1 | 0.00984 (0.00904 to 0.0103) | 0.064 (0.0296 to 0.118) | 53.6 (52.4 to 54.9) |
| C07 | 1 | 0.0371 (0.0363 to 0.0377) | 0.676 (0.597 to 0.745) | 15.1 (12.6 to 16.8) |
| C12 | 1 | 0.0101 (0.00994 to 0.0104) | 0.0628 (0.0497 to 0.0768) | 51 (47.5 to 54.3) |

## Limits and failure modes

Efficiency about $1/M$ whatever the geometry (in the bake C01 with 9 traps reaches 0.09, the 100-trap cases 0.01); the uniformity
depends strongly on the pixels per trap, so the method is only well-behaved on large SLMs. A trap with no pixel (a weight so small
that its share rounds to zero) is skipped (`if not sel.any(): continue`, line 48).

## References

- Montes-Usategui, Pleguezuelos, Andilla and Martin-Badosa 2006, Opt. Express 14, 2101,
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-14-6-2101
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
