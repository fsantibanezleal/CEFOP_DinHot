# BS-4: Aberration-robust hologram (engine id B4)

| Item | Value |
|---|---|
| Ladder row | BS-4, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, robust design, baked |
| Targets, dimensions | traps, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b4_robust.py` (`SPEC` line 56, `sample_perturbation` line 66, `sigma_point_phases` line 78, `ensemble_stats` line 90, `run` line 105) |
| Gate | `tests/methods/beyond/test_b4_robust.py` |
| Live port | none (lane `baked`; `getMethod('B4')` raises `NotLive`) |
| Card | [B4](../../frameworks/B4_aberration-robust-hologram.md) |
| Outcome (0.02.004) | met for residual aberrations: a median of 1.435 times over three seeds (1.42 to 1.57, criterion 1.25) at 0.982 of the efficiency, and 1.439 times over ten seeds (1.35 to 1.57) at 0.982, every seed's point estimate above the criterion and the bootstrap interval of a single 200-sample ensemble above it on 8 of 10 seeds, so the claim rests on the median over seeds and not on every single-ensemble interval; not obtained for pointing errors (1.04 times at the acceptance budget, a reported negative; 1.48 times at 0.10 bins and 0.912 of the efficiency with a displacement prior alone and five times the budget); the first claim of 2 times for both was not reached |

## Tier and role

Beyond the state of the art: DinHot's own proposal, narrowed after a measurement.

**Hypothesis (as narrowed on 2026-10-28).** Minimizing the expected trap-intensity loss over a distribution of residual Zernike aberrations, instead of the loss at the nominal system, gives a hologram whose trap spread over
an ensemble of residual aberrations is lower than that of the nominal phase-fixed WGS: the 95th percentile of the relative standard deviation over a 200-sample ensemble at least 1.25 times below M07's, with the mean
efficiency at most 10 percent lower. Robustness to pointing errors is an option, measured and reported, not claimed.

**The original claim** (algorithms dossier D5.1 B4) was robustness to aberrations and to trap displacement together, with the 95th percentile at least 2 times lower and the mean efficiency at most 10 percent lower. With the real
implementation it failed (a strict expected-failure test in the E3 work), and the main session narrowed the claim to residual aberrations.

**The gap.** Aberrations vary across the field and are corrected per site (a Zernike set per trap) or with one global set (Ebadi et al. 2021, https://arxiv.org/abs/2012.12281; Manetsch et al. 2025,
https://arxiv.org/abs/2403.12021); no source read optimizes the hologram for a distribution of residual aberration (https://arxiv.org/abs/2512.15967 is the nearest, per the SDD).

## Problem it answers

After a correction (M14) residual aberrations remain and vary across the field; B4 keeps the trap spread low over the whole distribution instead of at the nominal point.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` (a shaped field raises a `ValueError` naming `traps`), `budget` (`iterations` expected-cost steps), `rng`, optional `init` (the start hologram), `q`, `lr`, `warm`, `aberration`,
  `pointing_bins`, `design` (`sigma` or `sample`), `level_fraction`. The `sigma` design covers aberrations only and refuses `pointing_bins > 0` (`ValueError`, lines 121 and 122); `design=None` chooses `sigma` when
  `pointing_bins == 0` and `sample` otherwise (line 118). `device` is accepted and ignored.
- Output: `Result` with `phi` in $[0, 2\pi)$, one `history` entry per step (with `loss`), `fields`, and `meta` (`design`, `q`, `lr`, `aberration`, `pointing_bins`, `start_phi`, `level`). `ensemble_stats(setup, phi, traps,
  seed=999, n=200, aberration, pointing_bins)` evaluates a hologram on a seeded ensemble and returns `efficiency_mean`, `sigma_p95`, `sigma_mean` and the sorted `sigmas`.

## The method

Minimize the expected loss over residual Zernike coefficients $a_k \sim \mathcal N(0, s_a^2)$ (Noll 4 to 11, in waves; piston and tilts excluded),

$$\min_\phi\ \mathbb E_a\, L\big(\phi + 2\pi W(a)\big),\qquad L = \frac{\sum_m (I_m - T_m)^2}{\sum_m T_m^2},\qquad T_m = \ell\,e_{nom}\,\frac{w_m}{\sum w},$$

with $W$ the wavefront (`core.zernike.phase_from_coeffs`) added to the SLM phase as in the total-phase sum of Nogrette et al. 2014 (https://arxiv.org/abs/1402.5329), $e_{nom}$ the efficiency of the starting hologram and
$\ell$ the target level fraction (0.9). Gradients are the closed form of `TrapCost` (the aberration is a phase offset, so $dL/d\phi$ is the unperturbed formula at the shifted phase).

Default design `sigma`: the expectation is replaced by a deterministic sigma-point set, $\pm s_a\sqrt{8}$ on one mode at a time (16 points, mean zero, covariance exactly $s_a^2 I$ over the 8 modes;
`sigma_point_phases`, line 78), so the loss has no sampling noise and Fletcher-Reeves CG with a strong-Wolfe line search (`_common.cg_minimize`) converges on it. Design `sample` (automatic when
`pointing_bins > 0`): $Q$ seeded random draws resampled at every iteration and Adam, with independent trap displacements $d_m \sim \mathcal N(0, s_p^2)$ in $x$ and $y$ added to each draw
(`sample_perturbation`, line 66). The inner solver is phase-fixed WGS (`warm` iterations, `pfwgs` with `n_fix` 12), whose hologram starts the expected-cost steps and sets $e_{nom}$.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `aberration` $s_a$ | 0.02 waves per mode | `b4_robust.py` line 58 | this implementation's stated choice, not sourced (the module docstring says so); the perturbation priors are device dependent |
| `pointing_bins` | 0.0 | line 59 | pointing is optional and not claimed |
| `q` | 8 | line 60 | the research record: 8 to 32 samples per iteration |
| `lr` | 0.02 | line 61 | Adam rate of the `sample` design |
| `warm` | 30 | line 62 | iterations of the phase-fixed WGS start |
| `level_fraction` $\ell$ | 0.9 | line 63 | measured trade-off (0.02.004, paper's ablation, `ablLevel*` and `ablDefault*` in `robust_numbers.tex`): the median factor and the efficiency ratio are 0.71 and 0.849 at 0.80, 1.25 and 0.929 at 0.85, 1.43 and 0.982 at 0.90, 1.27 and 1.006 at 0.937, 1.19 and 1.009 at 0.95, 1.06 and 1.014 at 1.00 (the level trades efficiency for robustness) |
| acceptance budget | 40 CG iterations | `tests/methods/beyond/test_b4_robust.py` (`ensemble_pair`) | the test's budget |

## Complexity and lane

Each step costs $Q$ (or 16, for the sigma points) times the cost of one forward and adjoint evaluation of the point-trap model, i.e. $Q$ times one WGS iteration; the ensemble evaluation is 200 forward evaluations.
Lane `baked` (`SPEC`, line 56). The acceptance ensemble test takes about 54 s on the development machine (E3 report).

## Acceptance criterion and gate

Ladder row: over a 200-sample ensemble of residual aberrations, the 95th percentile of the relative standard deviation at least 1.25 times below M07, efficiency at most 10 percent lower; robustness to pointing errors
is measured and reported, not claimed. Gate `tests/methods/beyond/test_b4_robust.py::test_acceptance_aberration_only_p95_sigma_1_25_times_below_phase_fixed_wgs`: the 10x10 task on 256 by 256 padded 2; the nominal
hologram is the in-test phase-fixed WGS (30 iterations, seed 1; E3 cross-checked it against the module M07 and found the same hologram statistics); B4 with `Budget(40)`, seed 1; both evaluated by
`ensemble_stats` on 200 samples of seed 999 with 0.02 waves per mode; B4's `sigma_p95` at most the nominal's divided by 1.25, and its mean efficiency at least 0.9 of the nominal's.
`::test_pointing_ensemble_runs_and_returns_finite_ratios_without_a_claim` asserts only that the pointing case runs and returns finite ratios. Other tests: the perturbation is seeded and has the stated scale, the gradient at a perturbed sample matches finite
differences, the sigma points have the prior covariance and the pointing case needs the `sample` design, a shaped field is refused.

## Evaluation that confirms or refutes it

The aberration claim is refuted if B4's p95 spread is not at least 1.25 times below the nominal's or it loses more than 10 percent of the efficiency. The pointing claim of the original proposal is refuted by the measurement
below. The ensemble is drawn from the same prior as the design (Gaussian, 0.02 waves per mode, Noll 4 to 11), with a different seed and different realizations (random draws against sigma points); robustness to a
different distribution (other amplitudes, other modes, a measured instrument) is not tested and is not established.

## Measured result

Values of the 0.02.004 generation, from `manuscripts/aberration-robust-hologram/data/robust_numbers.tex` (the paper's measurement of the acceptance task): 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), a 200-sample ensemble (seed 999) of 0.02 waves per mode (rms 0.057 waves, Strehl about 0.88), 40 conjugate-gradient iterations, level 0.9. Seed 1 of the acceptance test (`sigmaNomOne`, `sigmaBfourOne`, `ratioOne`, `ratioOneLo`, `ratioOneHi`):

| Quantity | Nominal (M07-equivalent) | B4 | Ratio |
|---|---|---|---|
| p95 relative standard deviation (percent), aberration only, seed 1 | 6.192 | 3.947 | 1.57 times (bootstrap interval of this one ensemble 1.34 to 1.73; criterion 1.25) |
| p95 relative standard deviation with a 0.15 bin pointing error added (`sample` design, 20 samples, B4 at 3 iterations and q = 2; `ptAccNomOne`, `ptAccBfourOne`, `ptAccOne`) | 8.492 | 8.152 | 1.04 times |

Over seeds: three seeds of the acceptance test give a median of 1.435 times (1.42 to 1.57) at 0.982 of M07's efficiency (0.981 to 0.983) (`ratioHeadThree`, `ratioMin`, `ratioMax`, `effRatioMed`, `effRatioMin`, `effRatioMax`); the paper's ten seeds give a median of 1.439 times (1.35 to 1.57) at 0.982 (0.981 to 0.983) (`ratioHeadAll`, `ratioAllMin`, `ratioAllMax`, `effAllMed`, `effAllMin`, `effAllMax`), with all 10 point estimates above 1.25 (`seedsPassing`) and the bootstrap interval of a single seed above 1.25 on 8 of 10 (`ciClearN`, `nSeedsAll`; the interval of a single 200-draw ensemble measures that finite ensemble and is wide, from about 1.34 to 1.73 for seed 1). The ratios of three and of ten seeds differ because the seeds differ; each is written with its seeds.

Variants tried and not adopted, level sensitivity and the budget are in the paper's ablation (`robust_numbers.tex`, `abl*` macros); at the chosen level the design reaches a median of 1.43 times (1.42 to 1.57) at 0.982 (`ablDefaultMed`, `ablDefaultMin`, `ablDefaultMax`, `ablDefaultEff`).

The pointing result depends on the budget (`robust_numbers.tex`): the acceptance configuration (3 steps of 2 draws, 0.15 bin) gives 1.04 times (0.85 to 1.05 over three seeds: `ptAccMed`, `ptAccMin`, `ptAccMax`), and 20 steps with a displacement prior added at most 1.12 times (`ptASampleMax`); with a displacement prior alone and 100 steps of Adam the ratio is 1.11 at 0.05 bins (`poALong`), 1.48 at 0.10 bins (1.44 to 1.50, `poBLong`, `poBLongMin`, `poBLongMax`, at 0.912 of the efficiency, `poBLongEff`) and 1.37 at 0.15 bins (`poCLong`), at 0.90 to 0.92 of the efficiency. The spread under displacement is dominated by a first-order slope term, which the design lowers (fivefold at 0.10 bins), over a second-order curvature floor that the spot width fixes; the earlier reading that the curvature alone bounds pointing robustness is incomplete. Outcome: the aberration claim is met (1.435 times over three seeds, 1.439 over ten); pointing robustness stays an option, not claimed, measured negative at the acceptance budget and positive at five times that budget with a displacement prior alone; the original 2 times is not reached.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its own optics, listed in `data/derived/manifests/`; the bake gives B4 no aberration
estimate, I1 report F5):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.777 (0.758 to 0.805) | 0.991 (0.989 to 0.994) | 0.586 (0.422 to 0.765) |
| C02 | 30 | 0.778 (0.774 to 0.783) | 0.978 (0.976 to 0.981) | 0.852 (0.835 to 0.867) |
| C07 | 30 | 0.766 (0.758 to 0.773) | 0.981 (0.979 to 0.983) | 0.983 (0.941 to 1.02) |
| C08 | 30 | 0.67 (0.666 to 0.672) | 0.717 (0.706 to 0.73) | 12.9 (12.5 to 13.6) |
| C09 | 30 | 0.443 (0.434 to 0.448) | 0.914 (0.909 to 0.925) | 5.31 (4.59 to 5.83) |

In the aberrated case C09 the mean relative standard deviation is 5.31 percent for B4 against 6.16 for M07 (1.16 times, computed from the committed file; one realization per seed, not the p95 of an ensemble) at 0.99 of its
efficiency. On ideal cases (C01, C02, C07) B4's spread is 0.4 to 1.0 percent while M07's is below 0.01 percent in 6 of the 9 seeds (the largest is 0.85): the price of robustness is a small nominal spread.

## Limits and failure modes

- The robustness prior is a stated parameter ($s_a$ = 0.02 waves), not sourced; a real instrument's residual distribution has to be measured.
- Pointing robustness is not obtained: the spot width bounds it.
- The benefit depends on the target level (efficiency traded for robustness) and on the budget; one seed of holograms in the acceptance test.
- Single device-free model: aberrations and nothing else; the traps are on the ideal point-trap model.
- The framework card [B4](../../frameworks/B4_aberration-robust-hologram.md) shows the same numbers; the E3 narrowing is recorded in `docs/design/SDD.md`.

## References

- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Manetsch et al. 2025, https://arxiv.org/abs/2403.12021
- Robust holograms, https://arxiv.org/abs/2512.15967
- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim, Keesling, Omran, Levine, Bernien, Greiner, Lukin and Englund 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 (the nominal M07)

## History before 0.02.004

The measurements of 2026-10-28 to 2026-10-29 (the acceptance run before the rule corrections, the re-measurement against the corrected M07, and the second one after B4's warm start became M07 itself, `optim/_gs_family.py`) are superseded by the measured result above and are kept in the git history of this file. The aberration claim held on every seed in each of them, and the pointing negative stood.
