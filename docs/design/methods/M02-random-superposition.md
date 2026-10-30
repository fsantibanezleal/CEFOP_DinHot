# M02: Random superposition

| Item | Value |
|---|---|
| Ladder row | M02, tier classical (SDD, Method ladder) |
| Family, lane | analytic, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m02_random_superposition.py` (`SPEC` line 21, `run` line 25); start function `sr_start` in `data-pipeline/pipeline/model/holo/methods/baseline/_common.py` (line 42) |
| Gate | `tests/methods/baseline/test_m02_random_superposition.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m02`, line 34) |
| Card | [M02](../../frameworks/M02_random-superposition.md) |

## Tier and role

The established analytic method that fixes the weakness of M01: the same sum of single-trap holograms with one random phase per
trap. The random phases break the regular interference of the prisms and raise the efficiency a great deal. It is a baseline for
two reasons: it is the "SR" hologram of Di Leonardo, Ianni and Ruocco 2007 (Table 1, https://doi.org/10.1364/OE.15.001913; see
also Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027), and the same random start seeds most iterative methods of
the ladder (M04 to M07, M09, M12, M19 and the beyond methods).

## Problem it answers

A one-pass hologram with good efficiency for a set of traps, when the intensity spread of 30 to 40 percent is acceptable or when a
start for an iterative method is needed.

## Inputs and outputs

- Input `setup` and `target` as M01: a `Target` of kind `traps`; a shaped-field target is refused with a `ValueError` naming
  `traps` (`_common.require_kinds`). `device` and `init` are accepted and ignored; `budget` is not consumed.
- Randomness only through `rng` (the portable xoshiro generator, `core/rng.py`, ADR-0054), via `rng.phases(M)` (one phase per trap),
  so the result is a pure function of the seed.
- Output: a `Result` with `phi` (float64, `n_pix` by `n_pix`, radians), `fields` (the trap fields $V_m$), a one-entry `history`
  and `meta['method']`.

## The method

$$\phi_j = \arg \sum_m \sqrt{w_m}\; e^{\,i(\Delta_j^m + \theta_m)},\qquad \theta_m \sim U[0, 2\pi)$$

with $\Delta_j^m$ the single-trap delay of M01 (Di Leonardo et al. 2007, Table 1, row "SR"; the same form in Bianchi and Di Leonardo
2010). `sr_start` draws the $M$ phases and back-projects the amplitudes $\sqrt{w_m}\,e^{i\theta_m}$ with `point_trap_backproject`
(`_common.py` lines 42 to 45); `run` then evaluates the trap fields (`m02_random_superposition.py` lines 29 and 30).

## Defaults

None (`run`, line 25). The random start of every other method is this function: the default start of M04 to M07 is `start_phase`
(`_common.py` line 48), which calls `sr_start` unless `init` is given.

## Complexity and lane

Cost $N \times M$, no iteration. Lane `live` (`SPEC`, line 21). The TypeScript port reproduces the RNG bit for bit
(`tests/fixtures/rng-reference.json`, `frontend/src/engine/holo/core.parity.test.ts`) and the hologram to 1.4e-14 (T1 report D2).
On a GPU the source reports about 0.35 ms per trap at 768 by 768 pixels (Bianchi and Di Leonardo 2010, through the algorithms
dossier); DinHot does not rely on that figure.

## Acceptance criterion and gate

Ladder row: on the 10x10 task with a flat beam, efficiency above M01 and at least 0.65; uniformity below 0.35 (DinHot measured 0.25
at 256 squared against 0.01 at 768 squared in the source; the ordering, not the value, transfers). Gate:
`tests/methods/baseline/test_m02_random_superposition.py::test_acceptance_10x10_over_seeds` runs seeds 0 to 5 on the 256 by 256
padded-2 grid and asserts, per seed, $|e - 0.69| \le 0.10$ and $u < 0.35$, and over the seeds a median efficiency above 0.5 and a
median uniformity below 0.5; `::test_efficiency_beats_superposition` asserts that the efficiency exceeds M01's by more than 0.2.

A reader should note the difference between the ladder text and the test: the ladder says "at least 0.65", the test accepts the
band 0.59 to 0.79 around the published 0.69; the measured minimum (0.738) satisfies both.

## Evaluation that confirms or refutes it

The row is confirmed if the efficiency clause holds (random phases raise the efficiency well above M01) and the uniformity stays
poor; it would be refuted if a seed fell outside the efficiency band or the uniformity reached the weighted methods' level. The
published uniformity of 0.01 is not the bar: on this task the intensity spread of random superposition is intrinsic to the method.

## Measured result

Acceptance run of 2026-10-28 (E2 report D1, D5): 10x10 task, 6 seeds (0 to 5), 256 by 256 padded 2, test setup (850 nm, focal length
250 mm, pitch 12.5 um, Gaussian beam), median with the range of the seeds:

| Quantity | Measured | Published (Table 1) |
|---|---|---|
| Efficiency | 0.750 [0.738, 0.752] | 0.69 |
| Uniformity | 0.252 [0.106, 0.272] | 0.01 |

The efficiency clause holds. The published uniformity is not reproduced: the spread of random superposition is about 35 percent
whatever the pixel count (128 or 256 tried) or the beam, so the published relative standard deviation of 89 percent is not reached
on this task (E2 report, summary item 1). The acceptance bound is therefore set at the measured ordering.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 1 | 0.722 (0.709 to 0.744) | 0.545 (0.373 to 0.644) | 34.7 (25.5 to 48.1) |
| C02 | 1 | 0.735 (0.72 to 0.748) | 0.169 (0.1 to 0.222) | 39.8 (35.9 to 42.3) |
| C03 | 1 | 0.743 (0.742 to 0.744) | 0.0898 (0.059 to 0.132) | 38.6 (37.6 to 39.1) |
| C05 | 1 | 0.765 (0.735 to 0.781) | 0.242 (0.233 to 0.25) | 42.8 (41.7 to 44.2) |
| C06 | 1 | 0.693 (0.691 to 0.695) | 0.833 (0.801 to 0.854) | 9.52 (8.19 to 12.1) |
| C07 | 1 | 0.727 (0.71 to 0.751) | 0.36 (0.305 to 0.425) | 37.7 (33.5 to 42.2) |
| C12 | 1 | 0.736 (0.72 to 0.749) | 0.183 (0.148 to 0.202) | 40.7 (37.4 to 43.8) |
| C13 | 1 | 0.692 (0.689 to 0.694) | 0.59 (0.572 to 0.613) | 13.8 (13.5 to 14) |
| C14 | 30 | 0.695 (0.687 to 0.699) | 0.457 (0.407 to 0.522) | 25.7 (23.7 to 27.7) |

## Limits and failure modes

High variance across seeds; no control of the trap intensities (in the committed bake the mean uniformity runs from 0.09 in C03 to 0.83 in C06).
A baseline, not a recommended method. Its quality depends on the geometry: low-symmetry sets (C06, C13) score better than
lattices (C02, C12).

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027
