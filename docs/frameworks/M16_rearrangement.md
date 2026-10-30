# M16, Hungarian assignment and linear phase interpolation (rearrangement)

| Item | Value |
|---|---|
| Family | dynamic |
| Lane | live |
| Targets, dimensions | traps (an atom set and a target set), 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/control/m16_rearrangement.py`, `SPEC` line 46, `run` line 134 |
| Anchor | Lee, Kim and Ahn, Phys. Rev. A 95, 053424 (2017); linear phase interpolation, arXiv 2501.01391 |

## Purpose

A loaded array of atoms has holes. Rearrangement moves the loaded atoms into a defect-free target pattern: decide who goes where
(assignment), then move the traps smoothly (a sequence of holograms) without ever dimming a moving trap enough to lose its atom.

## Equations

**Assignment.** Match each target site $t_i$ to a distinct loaded atom $a_{f(i)}$ minimising

$$C(f) = \sum_i d_{i,f(i)}^{\,\alpha}, \qquad d_{i,j} = |t_i - a_j|$$

with $\alpha > 1$ (default 1.5, the paper value; for a square lattice $\alpha > 1.12$ keeps the minimum inter-atomic distance of the lattice during moves) so
that paths do not cross (Lee, Kim and Ahn 2017, https://doi.org/10.1103/PhysRevA.95.053424 , https://arxiv.org/abs/1704.07074 ). `hungarian` is the
Kuhn-Munkres algorithm with potentials in numpy, $O(n^2m)$ for an $n\times m$ cost with $n\le m$ (the rectangular case: the unmatched atoms are released),
tested against brute force. `count_crossings` counts pairs of straight paths that intersect or overlap.

**Hologram sequence.** Compute the initial and final phase-fixed WGS holograms ([M07](M07_phase-fixed-wgs.md)), extract each tweezer's position, amplitude and
optical phase $\psi_m = \arg V_m$, interpolate linearly over $S$ steps

$$x_m(s) = x_m^i + \tfrac sS(x_m^f - x_m^i),\quad a_m(s) = a_m^i + \tfrac sS(a_m^f - a_m^i),\quad \psi_m(s) = \psi_m^i + \tfrac sS\operatorname{wrap}(\psi_m^f - \psi_m^i)$$

and invert at each step: $\phi(s) = \arg\sum_m a_m(s)e^{i\psi_m(s)}e^{+i\Delta_j^m(s)}$ (the point-trap back-projection, exact at fractional positions). $S = \lceil d_{max}/s_{max}\rceil$ with
`max_step_bins`. Because the amplitude is interpolated and the phase advances smoothly, no trap passes through zero intensity, unlike independent weighted
GS holograms whose free phases jump between steps. Source: arXiv 2501.01391 (read as HTML).

## Implementation

Defaults (`run`, line 134): `alpha = 1.5`, `max_step_bins = pad` (one Fourier unit $\lambda f/(n_{pix}p)$), `n_fix = 12`; `atoms` (a `TrapSet` of loaded positions) is required.
Output: `phi` is the last frame; `meta` has `frames`, `n_steps`, `assignment`, `min_ratio` (per trap: the minimum over the steps of $I_m(s)$ divided by its mean),
`moved`, `crossings` and `trap_sequence`. UNVERIFIED: the paper gives the unit as $\lambda f/(mL)$ with $m\approx0.41$ in prose; the equations above are the extraction's rendering
of the described procedure, and the wrapped phase difference (shortest phase path) is DinHot's reading of "interpolate linearly".

## Acceptance criterion and test

No crossing moves for $\alpha = 1.5$ on a 7 by 7 to 3 by 3 sort; a moving trap above 70 percent of its mean intensity:
`tests/methods/control/test_m16_rearrangement.py::test_no_crossing_moves_for_alpha_1_5_on_7x7_to_3x3` and
`::test_lpi_keeps_moving_traps_above_70_percent`; the assignment equals brute force (`::test_hungarian_matches_brute_force`).

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Crossings | 0 | 60 random loadings, 21 atoms, 7 by 7 to 3 by 3 |
| Moving-trap minimum over mean intensity | 0.870 median [0.748, 0.963]; all above 0.70 | 24 moving traps, 5 loadings, `max_step_bins = pad` |

A planned comparison against independent weighted GS per step was dropped: with 9 traps the weighted GS equalises every step and shows no flicker (median 0.96), unlike the 11 kHz camera
observation of the paper; it is not an SDD criterion. The flicker-bounded sequence [B2](B2_flicker-bounded-sequence.md) raises the same minimum above 0.9.

## Limits

LPI does not optimise its intermediate frames (the gap B2 fills); the transient model of the metric is simplified (each frame is scored at its own positions).

## References

- Lee, Kim and Ahn 2017, Phys. Rev. A 95, 053424, https://doi.org/10.1103/PhysRevA.95.053424 ; https://arxiv.org/abs/1704.07074
- Linear phase interpolation, https://arxiv.org/abs/2501.01391
