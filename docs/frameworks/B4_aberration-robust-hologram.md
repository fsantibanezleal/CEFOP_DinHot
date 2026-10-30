# B4, Aberration-robust hologram (beyond the published state of the art)

| Item | Value |
|---|---|
| Family | beyond, robust design |
| Lane | baked |
| Targets, dimensions | traps, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/beyond/b4_robust.py`, `SPEC` line 56, `run` line 105 |
| Claim | robustness to residual aberrations; robustness to pointing errors is reported, not claimed |

## Purpose

After a correction, residual aberrations remain and they vary across the field. B4 optimises the hologram for a distribution of residual aberrations instead
of for the nominal system, so the trap spread stays low over the whole distribution.

## The gap and the narrowed claim

Aberrations vary across the field and are corrected per site (a Zernike set per trap) or with one global set (Ebadi et al. 2021, https://arxiv.org/abs/2012.12281 ;
Manetsch et al. 2025, https://arxiv.org/abs/2403.12021 ); no source read optimises the hologram for a distribution of residual aberration (https://arxiv.org/abs/2512.15967
is the nearest). The claim was narrowed on 2026-10-28 after a measurement: the original claim included robustness to pointing errors, which was not reached (see below).

## Method

Minimise the expected loss over residual Zernike coefficients $a_k\sim\mathcal{N}(0, s_a^2)$ (Noll 4 to 11, waves, piston and tilts excluded):

$$\min_\phi\ \mathbb{E}_a\,L\big(\phi + 2\pi W(a)\big), \qquad L = \frac{\sum_m(I_m - T_m)^2}{\sum_m T_m^2}, \qquad T_m = 0.9\,e_{nom}\,\frac{w_m}{\sum w}$$

with $W$ the wavefront ([P03](P03_zernike.md)) added to the SLM phase as in the total-phase sum of Nogrette et al. 2014 (https://arxiv.org/abs/1402.5329 ) and $e_{nom}$ the
efficiency of the starting hologram. Default design `"sigma"`: the expectation is replaced by a deterministic sigma-point set, $\pm s_a\sqrt{8}$ on one mode at a time (16
points, covariance exactly $s_a^2 I$), so the loss has no sampling noise and Fletcher-Reeves CG with a strong-Wolfe line search converges on it. Design `"sample"` (used
automatically when `pointing_bins > 0`): $Q$ seeded random draws resampled at every iteration, Adam, with independent trap displacements $d_m\sim\mathcal{N}(0, s_p^2)$ added to
each draw. Gradients are closed form (the aberration is a phase offset, so $dL/d\phi$ is the unperturbed formula at the shifted phase). The inner solver is phase-fixed WGS
whose hologram starts the expected-cost steps.

## Implementation

Defaults (`b4_robust.py`, lines 58 to 63): `aberration = 0.02` waves per mode (this implementation's stated choice, not sourced), `pointing_bins = 0.0`, `q = 8`, `lr = 0.02`,
`warm = 30`, `level_fraction = 0.9`. The perturbation priors are device dependent. `ensemble_stats` evaluates a held-out ensemble.

## Acceptance criterion and test

Over a 200-sample ensemble of residual aberrations, the 95th percentile of the relative standard deviation at least 1.25 times below M07, efficiency at most 10 percent
lower; pointing robustness is measured and reported, not claimed:
`tests/methods/beyond/test_b4_robust.py::test_acceptance_aberration_only_p95_sigma_1_25_times_below_phase_fixed_wgs`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | M07 (nominal) | B4 | Ratio | Conditions |
|---|---|---|---|---|
| p95 relative standard deviation (percent), aberration only | 6.192 | 3.947 | 1.57 times (median 1.435 over three seeds, re-measured 2026-10-29 after the rule corrections; 6.268, 4.045 and 1.55 before) | 200-sample ensemble, seed 999, 0.02 waves per mode (rms 0.057 waves, Strehl about 0.88), 10 by 10 task, 256 by 256, 1 seed, 40 CG iterations, level 0.9 |
| Mean efficiency | 0.7169 | 0.7031 | minus 1.9 percent | same |
| p95 with a 0.15 bin pointing error added | 8.492 | 8.152 | 1.04 times | `"sample"` design, 20 samples, re-measured 2026-10-29 (7.457, 7.309 and 1.02 before the rule corrections) |

Level sensitivity: a target level of 0.937 gives 1.28 times, 0.95 with 80 iterations gives 1.23 times, 0.9 with 80 iterations gives 1.55 times; the level trades a little efficiency for
robustness. The pointing result is a negative one: a displaced trap loses intensity in proportion to the curvature of its spot, which the spot width fixes, and halving the loss needs a
spot 1.4 times wider, about half the peak efficiency (the implementer's reasoning, not a source). The test for pointing asserts only that it runs and returns finite ratios.
Tried and not adopted: ensemble WGS with per-iteration samples (worse), Adam on random samples (1.0 to 1.1 times), CG on 16 fixed random samples (1.05 times).

## Limits

- The robustness prior is a stated parameter. A real instrument's residual distribution has to be measured.
- Pointing robustness is not obtained; the benchmark reports the negative result.

## References

- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281 ; Manetsch et al. 2025, https://arxiv.org/abs/2403.12021
- Robust holograms, https://arxiv.org/abs/2512.15967 ; Nogrette et al. 2014, https://arxiv.org/abs/1402.5329
