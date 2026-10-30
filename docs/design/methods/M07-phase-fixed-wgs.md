# M07: Phase-fixed weighted GS

| Item | Value |
|---|---|
| Ladder row | M07, tier sota (SDD, Method ladder) |
| Family, lane | GS, live |
| Targets, dimensions | traps, 2D only (`SPEC.dims` is `(2,)`) |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m07_phase_fixed_wgs.py` (`SPEC` line 21, `run` line 24) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` (`rule_wgs_fixed`, line 95) |
| Gate | `tests/methods/baseline/test_m07_phase_fixed_wgs.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m07`, line 124), the WebGPU path in `frontend/src/engine/holo/gpu/` |
| Card | [M07](../../frameworks/M07_phase-fixed-wgs.md) |

## Tier and role

State of the art, replicated: the practical method for large point arrays. The solution replicated is Kim, Kim, Lee and Ahn, Opt. Lett.
44, 3178 (2019), https://doi.org/10.1364/OL.44.003178 (arXiv https://arxiv.org/abs/1903.09286): after an initial number $N$ of weighted-GS
iterations the focal-plane phase is frozen, so later iterations adjust amplitudes only and the weights stay effective; the same
procedure is used in the 1000-tweezer experiments of Ebadi et al. 2021 (https://arxiv.org/abs/2012.12281) and, through the references
of Manetsch et al. 2025 (https://arxiv.org/abs/2403.12021), at about 12 000 sites. The source reports 91.2 percent modulation efficiency
and non-uniformity below 0.5 percent on 50 by 30 foci (795 nm, focal length 250 mm, $N = 12$) and a camera correction from 22 percent to
1.59 percent in three steps (against 6.47 percent for conventional WGS).

## Problem it answers

Percent-level (here, far below one percent) trap uniformity for arrays of hundreds to thousands of traps in a few tens of iterations,
which M06 reaches much more slowly. It is also the engine of the camera correction (M12, variant `kim`).

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`), `budget`, `rng`, optional `init`,
  `n_fix` (a positive integer; a bool, a non-integer or a value below 1 raises a `ValueError`, lines 27 and 28), `form`. `device` ignored.
- Output: `Result` with `phi`, one `history` entry per iteration, `fields`, and `meta` (`method`, `form`, `iterations`, `n_fix`, `psi`: the
  frozen focal phase, or the last one if the run ended before $N$).
- The FFT form needs traps on bins with $z = 0$ and no vortex; `form='auto'` falls back to the point form otherwise, with the same hologram on
  bins (test `::test_both_forms_agree_on_2d_grid`).

## The method

At iteration $i$, with focal-plane amplitudes $B_i(\mathbf u_m) = |V_m|/a_m$ and the target amplitude $T_m = a_m = \sqrt{w_m}$ (Kim et al.
2019, the method section; equation numbers were not recorded in the research sources, not established):

$$g_i(\mathbf u_m) = \frac{\langle B_i\rangle_N}{B_i(\mathbf u_m)}\,g_{i-1}(\mathbf u_m),\quad g_0 = 1,\qquad
\mathcal F\big[A_{i+1}e^{i\phi_{i+1}}\big] = g_i\,T\,e^{i\psi_i},\qquad \psi_i = \psi_N\ \ (i \ge N)$$

so the focal phase follows the field, $\psi_i = \arg V_m$, for the first $N$ iterations and is then frozen at $\psi_N$. The weights $g$ keep
updating after the freeze and carry the memory of all earlier corrections. The reason, in the source: replacing the SLM-plane amplitude by the
laser amplitude introduces a focal phase change $\delta\psi_i$ that makes $g_i$ less effective; fixing $\psi$ removes it.

In the code (`rule_wgs_fixed`, `_gs.py` lines 95 to 107): $b = |V|/a$; `state['w'] *= mean(b)/b`; for $k < N$ the phase is `angle(v)`; at
$k = N$ the phase is stored, `state['psi'] = angle(v)`; for $k > N$ it is the stored one; the coefficient is `w * a * exp(1j * psi)`.
UNVERIFIED (docstring): the source does not define $B_i$ (taken as the field amplitude, as in M06) nor whether the $N$-th iteration already
uses the frozen phase (here it computes it; the red run of T1 shows that freezing one iteration late turns the port's parity test red).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `n_fix` $N$ | 12 | `m07_phase_fixed_wgs.py` line 24 | Kim et al. 2019: 12 WGS iterations before fixing; pinned by `::test_n_fix_default_is_kim_12` |
| `form` | `auto` | line 25 | FFT form (the paper form) on bins, else the point form (I1 report F1) |
| acceptance setting of `n_fix` | 60 | `tests/methods/baseline/test_m07_phase_fixed_wgs.py::test_acceptance_fewer_iterations_than_gsw_on_50x30` | measured on the 50 by 30 task of DinHot's grid (below) |

The ladder row of the SDD states "with the phase fixed after 60 iterations (DinHot's measured default)". In the code the default stays
Kim's 12; 60 is the value with which the acceptance criterion is run, and the default is not grid dependent (E2 report, open decision (d):
whether the default should become grid dependent is not settled). The port's default is also 12 (`baseline.ts` line 127), with the default form `fft`
(line 129) and the fallback to the point form off the bins in `frontend/src/engine/holo/engine.ts` (lines 249 to 251).

## Complexity and lane

FFT form: $O(P\log P)$ per iteration with $P = n_{fft}^2$ (about 24 ms in Node at the live grid, SDD Lanes); point form: $O(N_{pix}\,M)$.
Lane `live`. Parity worst difference of the port 5.7e-14 (T1 report D2). WebGPU: 30 iterations of M07 in 0.30 to 0.32 s against 1.5 to 1.6 s
on the CPU path in the same browser mode, with the traps on bins (T1 report D4, one Intel gen-12lp adapter; not a portable claim). Acceptance
test runtime about 44 s on the development machine (E2 report).

## Acceptance criterion and gate

Ladder row: fewer iterations than M06 to a relative standard deviation of 0.5 percent on a 50 by 30 array, with the phase fixed after 60
iterations. Gate `tests/methods/baseline/test_m07_phase_fixed_wgs.py`:

- `::test_acceptance_fewer_iterations_than_gsw_on_50x30`: 50 by 30 traps 8 bins apart (1500 traps, 44 SLM pixels per trap) on 256 by 256
  padded 2, seeds 1 and 2, budget 150, both methods in the FFT form, `n_fix=60`; M07 must reach a relative standard deviation of 0.5 percent
  (`ia` not none), M06 either never or in more iterations (`ia < ib`), and the final efficiency must exceed 0.6;
- `::test_kim_n_fix_12_saturates_on_the_crowded_grid`: with the default `n_fix=12`, seed 1, 40 iterations, the minimum relative standard
  deviation stays above 0.5 percent and the final one below 10 percent (the measured stall is pinned as a documented limit);
- `::test_phase_is_fixed_after_n_fix`, `::test_both_forms_agree_on_2d_grid`, `::test_10x10_uniform_and_deterministic`.

## Evaluation that confirms or refutes it

Confirmed if M07 reaches 0.5 percent in fewer iterations than M06 on the crowded array. Refuted by the second test for the literal
Kim setting on this grid: with $N = 12$ the spread stalls at 3.58 percent (2.9 before the 2026-10-29 rule corrections). The row is therefore confirmed only with the larger `n_fix`; the
two findings are both kept, because the replication of a published setting that does not transfer to a smaller SLM is itself a result.

## Measured result

Acceptance run of 2026-10-28 (E2 report D2 and D5), 50 by 30 array, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5
um), 2 seeds:

| Quantity | Measured | Conditions |
|---|---|---|
| Iterations to 0.5 percent, `n_fix = 60` | 64 and 64 (M06: 136 and 106), re-measured 2026-10-30 (63 and 64 against 121 and 147 before the rule corrections) | FFT form |
| Minimum spread, `n_fix = 12` | stalls at 3.58 percent over 40 iterations (2.88 before the rule corrections) | seed 1 |
| Minimum spread against `n_fix` 12 / 20 / 30 / 40 / 60 | 2.9 / 1.6 / 1.5 / 0.8 / 1e-5 percent | same grid |
| 10x10 task, flat beam, family trend (E3 in-test copy) | efficiency 0.91, uniformity 1.00 | against Di Leonardo's GSW 0.93 / 0.99 |

Mechanism (E2): on this crowded grid the phase frozen after 12 iterations belongs to an unconverged hologram and the weight update then
cannot repair it. Published (Kim): 91.2 percent efficiency and non-uniformity below 0.5 percent with $N = 12$ on a larger SLM.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; default `n_fix = 12`; each
case has its own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.788 (0.77 to 0.817) | 1 (1 to 1) | 0.00352 (0.000232 to 0.00963) |
| C02 | 30 | 0.792 (0.788 to 0.798) | 0.993 (0.984 to 1) | 0.377 (0.0139 to 0.848) |
| C03 | 30 | 0.794 (0.794 to 0.795) | 0.988 (0.983 to 0.995) | 0.419 (0.199 to 0.663) |
| C06 | 30 | 0.701 (0.696 to 0.704) | 1 (1 to 1) | 9.37e-13 (4.35e-14 to 1.61e-12) |
| C07 | 30 | 0.785 (0.778 to 0.791) | 1 (1 to 1) | 0.00397 (0.000275 to 0.00891) |
| C08 | 30 | 0.678 (0.675 to 0.681) | 0.715 (0.685 to 0.731) | 13.2 (13.1 to 13.4) |
| C09 | 30 | 0.447 (0.438 to 0.453) | 0.903 (0.889 to 0.924) | 6.16 (4.66 to 7.09) |
| C10 | 30 | 0.792 (0.79 to 0.797) | 0.999 (0.999 to 1) | 0.0222 (0.0117 to 0.0428) |
| C12 | 30 | 0.792 (0.786 to 0.797) | 0.99 (0.97 to 1) | 0.508 (0.0128 to 1.48) |
| C13 | 30 | 0.725 (0.723 to 0.727) | 0.993 (0.992 to 0.996) | 0.258 (0.179 to 0.3) |

## Limits and failure modes

- `n_fix` depends on the grid; a larger value is needed on crowded arrays. Whether the default should be grid dependent is open.
- 2D only: the freeze is defined for a plane (3D traps use M06 or M19).
- On a device with crosstalk and 4-bit phase the spread is 12 to 15 percent (C08 in the bake), which BS-1 removes.
- The WebGPU path covers only M04, M06 and M07 with traps on bins and the ideal device (T1 report D4).

## References

- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Manetsch et al. 2025, https://arxiv.org/abs/2403.12021
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913 (the weights of M06)

## Update after the corrections of 2026-10-29

From the same start, M07 now matches slmsuite 0.5.0's WGS-Kim to 1e-4 percent in the final relative standard deviation (C03, 1024 traps, 30 iterations, n_fix 12, 4 of 4 seeds: 0.1803, 0.1865, 0.3643 and 0.3256 percent). The earlier code reweighted the field of the start hologram; Kim et al. 2019 start the recursion with g_0 = 1, so the first iteration is plain GS (`tests/methods/baseline/test_m07_against_slmsuite.py`). slmsuite's default feedback exponent is 0.8; M07 and Kim use 1, and M07 also reproduces slmsuite at 0.8 once the first update is skipped.
