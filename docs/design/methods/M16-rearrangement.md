# M16: Hungarian assignment and linear phase interpolation

| Item | Value |
|---|---|
| Ladder row | M16, tier sota (SDD, Method ladder) |
| Family, lane | dynamic (rearrangement), live |
| Targets, dimensions | traps (a target set and a loaded-atom set), 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m16_rearrangement.py` (`SPEC` line 46, `hungarian` line 50, `assign` line 97, `count_crossings` line 123, `run` line 134) |
| Gate | `tests/methods/control/test_m16_rearrangement.py` |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m16`, line 380; `assign`, line 351) |
| Card | [M16](../../frameworks/M16_rearrangement.md) |

## Tier and role

State of the art, replicated: decide which loaded atom goes to which target site (assignment), then move the traps smoothly with a sequence of
holograms so that no moving trap dims enough to lose its atom. Two sources are replicated: the Hungarian assignment with the cost $d^\alpha$ of Lee,
Kim and Ahn, Phys. Rev. A 95, 053424 (2017), https://doi.org/10.1103/PhysRevA.95.053424 (arXiv https://arxiv.org/abs/1704.07074), and the linear
phase interpolation (LPI) of the sequence of arXiv 2501.01391 (https://arxiv.org/abs/2501.01391, read as HTML). The LPI paper reports that, sampled at 11 kHz,
the weighted-GS spot nearly vanished several times while the LPI spot stayed above 70 percent. BS-2 is the claim built against this module's LPI.

## Problem it answers

A loaded array of atoms has holes. Rearrangement moves loaded atoms into a defect-free target pattern: who goes where, and a hologram per
step along the way.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (the target sites), `atoms` (a `TrapSet` of loaded positions, required; fewer atoms than targets
  raises a `ValueError`, line 141), `budget` (the iterations of each endpoint hologram), `rng`, `alpha`, `max_step_bins`, `n_fix`. `device` and `init`
  are ignored.
- Output: `Result` whose `phi` is the last frame; `history` one entry per frame; `fields` the trap fields of the last frame; `meta`: `frames`
  (an $(S+1) \times n \times n$ array), `n_steps` $S$, `assignment` (the atom index of each target), `min_ratio` (per trap: the minimum over the steps of
  $I_m(s)$ divided by its mean over the steps, with $V_m(s)$ the point-trap field of that frame at that step's positions), `moved` (traps with non-zero
  displacement), `crossings`, `trap_sequence` (the `TrapSet` of each step), `alpha`, `max_step_bins`.

## The method

**Assignment.** Match each target site $t_i$ to a distinct loaded atom $a_{f(i)}$ minimizing (Lee, Kim and Ahn 2017)

$$C(f) = \sum_i d_{i,f(i)}^{\,\alpha},\qquad d_{i,j} = |t_i - a_j|,\quad \alpha > 1$$

so that paths do not cross; for a square lattice $\alpha > 1.12$ keeps the minimum inter-atomic distance of the lattice during moves.
`hungarian` is the Kuhn-Munkres algorithm with potentials in numpy, $O(n^2 m)$ for an $n \times m$ cost with $n \le m$ (the rectangular case: the
unmatched atoms are released), tested against brute force on 96 random matrices of size up to 7. `count_crossings` counts the pairs of straight
paths that intersect or overlap along a segment (`_paths_cross`, line 110).

**Hologram sequence.** The initial and final holograms are phase-fixed weighted GS (M07; `n_fix` iterations before the freeze, `form='auto'`,
`budget` iterations each, lines 159 to 162). From each, every tweezer's position, amplitude and optical phase $\psi_m = \arg V_m$ are read, and
linearly interpolated over $S$ steps,

$$x_m(s) = x_m^{i} + \tfrac sS(x_m^{f} - x_m^{i}),\quad a_m(s) = a_m^{i} + \tfrac sS(a_m^{f} - a_m^{i}),\quad
\psi_m(s) = \psi_m^{i} + \tfrac sS\operatorname{wrap}(\psi_m^{f} - \psi_m^{i}),$$

and the transform is inverted at each step: $\phi(s) = \arg\sum_m a_m(s)e^{i\psi_m(s)}e^{+i\Delta_j^m(s)}$ (the point-trap back-projection, exact at
fractional positions; lines 168 to 175). The number of steps is set by the longest path, $S = \lceil d_{max}/s_{max}\rceil$ (line 151), at least 1.
Because the amplitude is interpolated and the phase advances smoothly, no trap passes through zero intensity, unlike independent weighted-GS holograms
whose free phases jump between steps.

UNVERIFIED (docstring): the paper gives the unit of the step as $\lambda f/(mL)$ with $m \approx 0.41$ in prose; the equations above are the
extraction's rendering of the described procedure; and the wrapped phase difference (the shortest phase path) is DinHot's reading of "interpolate linearly".

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `alpha` | 1.5 | `m16_rearrangement.py` line 135 | the paper value; above the 1.12 bound for a square lattice |
| `max_step_bins` $s_{max}$ | `None`: `pad` bins (one Fourier unit $\lambda f/(n_{pix}p)$), line 143 | line 135 | DinHot's reading of the paper's step unit (UNVERIFIED, above) |
| `n_fix` | 12 | line 135 | M07's default (Kim); see M07 for the grid dependence |

The port has the same defaults (`control.ts` lines 386 and 387).

## Complexity and lane

Assignment $O(n^2 m)$; the sequence costs two M07 runs plus $S+1$ point-trap back-projections ($O(N_{pix}M)$ each). Lane `live` (`SPEC`, line 46):
parity worst difference 1.8e-14 (T1 report D2); the port receives the loaded atoms of the case's rearrangement block (`random_loading`, one RNG
uniform per site). Test runtime about 33 s for the LPI test (E2 report).

## Acceptance criterion and gate

Ladder row: no crossing moves for $\alpha = 1.5$ on a 7 by 7 to 3 by 3 sort; a moving trap above 70 percent of its mean intensity. Gate
`tests/methods/control/test_m16_rearrangement.py`:

- `::test_no_crossing_moves_for_alpha_1_5_on_7x7_to_3x3`: a 7 by 7 lattice of sites 8 bins apart, 21 atoms drawn at random (60 loadings, seeds
  0 to 59), the central 3 by 3 target at 8 bins; the assignment with $\alpha = 1.5$ gives zero crossings for every loading;
- `::test_lpi_keeps_moving_traps_above_70_percent`: 5 loadings, `Budget(30)`; no crossings, at least 15 moving traps in total, and the worst
  `min_ratio` of a moving trap at least 0.70; the frames array has $S+1$ frames and the last equals `phi`;
- `::test_hungarian_matches_brute_force` (rectangular matrices up to $n, m \le 7$), `::test_crossing_counter_detects_crossings`, validation.

## Evaluation that confirms or refutes it

Confirmed by zero crossings in all loadings and a minimum transient ratio above 0.70, the level the LPI paper reports. The comparison the research
record planned against independent weighted-GS holograms per step was dropped: with 9 traps the weighted GS equalizes every step and shows no flicker
(median 0.96), unlike the 11 kHz camera observation of the paper, and it is not part of the criterion. BS-2 takes over that comparison.

## Measured result

Acceptance run of 2026-10-28 (E2 report D4 and D5), 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um):

| Quantity | Measured | Conditions |
|---|---|---|
| Crossings | 0 | 60 random loadings, 21 atoms, 7 by 7 to 3 by 3, $\alpha = 1.5$ |
| Moving-trap minimum over mean intensity | 0.870 median [0.748, 0.963]; all above 0.70 | 24 moving traps, 5 loadings, `max_step_bins = pad`, steps up to 4 for this lattice |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C10 only; the efficiency of
the method's final hologram as the bake scores it; M16 is a sorting method and is bounded on efficiency only in the case record, I1 report D3):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C10 | 10 | 0.823 (0.819 to 0.826) | not recorded | not recorded |

## Limits and failure modes

- LPI does not optimize its intermediate frames (the gap BS-2 addresses); the transient measure of the module is simplified (each frame is scored at its
  own positions, not in the blend model of BS-2).
- The step unit is a reading of the paper (UNVERIFIED); the wrapped phase difference is DinHot's reading.
- The assignment needs at least as many atoms as targets (`n <= m`); the atoms beyond the targets are released.
- The reported success rate of the source (61 percent after nine rounds on a 7 by 7 to 3 by 3 sort, through the research dossier) is a different
  quantity and is not reproduced here.

## References

- Lee, Kim and Ahn 2017, Phys. Rev. A 95, 053424, https://doi.org/10.1103/PhysRevA.95.053424 ; https://arxiv.org/abs/1704.07074
- Linear phase interpolation, https://arxiv.org/abs/2501.01391
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 (the endpoint holograms)
