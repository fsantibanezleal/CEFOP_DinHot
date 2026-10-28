# M18: Optimal-transport initialized MRAF

| Item | Value |
|---|---|
| Ladder row | M18, tier sota (SDD, Method ladder) |
| Family, lane | optimization, baked |
| Targets, dimensions | shaped fields only, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/optim/m18_ot_mraf.py` (`SPEC` line 51, `sinkhorn_separable` line 59, `barycentric_map` line 83, `integrate_gradient` line 97, `ot_phase` line 113, `mraf` line 130, `run` line 151) |
| Gate | `tests/methods/optim/test_m18_ot_mraf.py` |
| Live port | none (lane `baked`; `getMethod('M18')` raises `NotLive`) |
| Card | [M18](../../frameworks/M18_ot-initialized-mraf.md) |

## Tier and role

State of the art, replicated: MRAF from a random start leaves speckle that it removes slowly; an optimal-transport (OT) map between the input beam and the target
intensity gives a smooth phase that already sends the light roughly to the right place, so MRAF starts close to its answer. The solutions replicated are Swan,
Torchylo, Van de Graaff, Rudolph and Hogan, arXiv 2408.17025 (https://arxiv.org/abs/2408.17025; their Table 1, six targets: MRAF error 1.5 to 3.9 percent with
efficiency 18 to 45 percent, with OT initialization 0.17 to 0.96 percent with efficiency 53 to 85 percent) and, for the memory-light dual form, Torchylo, Swan, Tellez
and Hogan, arXiv 2512.19072 (https://arxiv.org/abs/2512.19072). The MRAF stage is M08's rule (Pasienski and DeMarco 2008).

## Problem it answers

An accurate smooth potential without the slow convergence of a random start, at an efficiency in the MRAF class.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `field` on the `n_fft` by `n_fft` focal grid (a trap target or another shape raises a `ValueError`, lines 154 to 158), `budget`
  (`iterations` MRAF iterations after the seed; `time_s` a deadline), `rng`, optional `init` (replaces the OT seed), `mix` in $(0, 1)$, `eps`, `ot_iterations`. `device` is
  ignored (ideal model).
- Output: `Result` with `phi` in $[0, 2\pi)$, one `history` entry per iteration (field history: efficiency, uniformity, relative standard deviation, `error`), `fields` the focal
  field, and `meta` (`ot_init`, `mix`, `eps`, and when the seed was computed `residual`, `sigma_bins`, `ot_time_s`).
- Grids: live size 128 by 128 focal grid (64-pixel SLM padded 2), baked 256 by 256 (128-pixel SLM padded 2).

## The method

Under the stationary-phase approximation the SLM phase satisfies the Monge-Ampere equation $G^2(\nabla\phi(x))\,\det(\nabla^2\phi(x)) = g^2(x)$ with $g^2$ the input intensity and
$G^2$ the target intensity; the quadratic-cost OT map $\gamma$ between them is integrated, $\phi(x) = \int\gamma(s)\cdot ds$, and seeds GS or MRAF (Swan et al. 2024).

Entropic OT by separable Sinkhorn (dual form with a separable cost, $O(N)$ memory, Torchylo et al. 2025; the equations are marked ESTIMATED in the research record): the plan
is $\Gamma = u\,K\,v$ with $K = K_x\otimes K_y$ and the updates

$$u \leftarrow g^2 \oslash (\Lambda v \Lambda),\qquad v \leftarrow G^2 \oslash (\Lambda^T u \Lambda^T),$$

evaluated as matrix products (`Ky @ v @ Kx.T`, lines 74 to 78). The cost is $|x-y|^2/2$ with $x$ the SLM pixel coordinate (pixel units) and $y$ the focal bin coordinate; the kernel width
is $\sigma^2 = \epsilon\,n_{fft}^2$ bins squared (line 123; the research record's $\epsilon = 0.001$ is for coordinates normalized by the image size). The barycentric map
$T(x) = \sum_y\Gamma(x,y)\,y/\sum_y\Gamma(x,y)$ (identity where the plan has no mass, lines 83 to 94) is integrated to $\Psi$ with $\nabla\Psi = T$ by a least-squares Poisson solve on a
mirror-extended grid (Frankot and Chellappa 1988, named in the module, not re-read: $\hat\Psi = -i(k_x\hat T_x + k_y\hat T_y)/|k|^2$, exact for a curl-free map and the least-squares projection
otherwise; lines 97 to 110). The stationary-phase relation is $k = (n_{fft}/2\pi)\,d\phi/dj$, so $\phi = (2\pi/n_{fft})\Psi$ (line 126).

Then MRAF (Pasienski and DeMarco 2008, Eq. (1)) with the mixing $m$:
$G^{(n)} = \{m\sqrt{I_0}|_{SR} + (1-m)|E^{(n)}_{out}|\,|_{NR}\}\,e^{i\arg E^{(n)}_{out}}$, then the inverse transform, the SLM amplitude reset to the beam, the phase kept
(`mraf`, lines 130 to 148). $\sqrt{I_0}$ is the target amplitude normalized to the total input power $n_{pix}^2$ (UNVERIFIED: the research record does not state the normalization; rescaling
to the current signal-region power instead drains the signal region, efficiency 0.001, measured by E3). With $m = 0.4$ the fixed point is near the efficiency solving
$\eta = m^2/(m^2 + (1-m)^2(1-\eta))$, which is 0.44.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `mix` $m$ | 0.4 | `m18_ot_mraf.py` line 53 | Pasienski and DeMarco 2008: 0.30 to 0.40 for MRAF; 0.4 puts the fixed-point efficiency at 0.44 (M08 uses 0.3) |
| `eps` $\epsilon$ | 0.001 | line 54 | the Sinkhorn value of Swan et al. 2024 (for coordinates normalized by the image size) |
| `ot_iterations` | 200 | line 55 | DinHot's choice; the marginal test (source marginal error below 1e-6, target below 1e-9) is run on a smooth problem |
| seed | the OT phase; `init` replaces it | `run`, lines 164 to 168 | a random phase is the baseline of the acceptance test |

## Complexity and lane

The separable Sinkhorn needs $O(N)$ memory and matrix products of the 1D kernels; then $O(P\log P)$ per MRAF iteration. Lane `baked` (`SPEC`, line 51). Test runtime about 10 s per
baked shape (E3 report).

## Acceptance criterion and gate

Ladder row: lower error than MRAF from a random start on the shaped targets. Gate `tests/methods/optim/test_m18_ot_mraf.py`:

- `::test_acceptance_live_size_lower_error_than_random_start` (disc, ring and a line): the 64-pixel SLM padded 2, 100 MRAF iterations at the default mixing; the OT-initialized signal
  error must be below the minimum of two random starts (seeds 5 and 6, uniform random phase passed as `init`), and the efficiency above 0.3;
- `::test_acceptance_baked_size_lower_error_than_random_start` (disc, ring): the 128-pixel SLM padded 2, one random start (seed 5);
- component tests: both Sinkhorn marginals (`::test_sinkhorn_matches_both_marginals_on_a_smooth_problem`), the barycentric map of a pure shift is a shift, the gradient integration recovers a known
  potential, the OT seed moves the beam onto a displaced blob, and determinism.

## Evaluation that confirms or refutes it

Confirmed if the OT seed gives a lower error than the random start at the same MRAF iterations and mixing; refuted if the OT phase did not beat a random one (the mutation run of E3
replaces the OT seed by a random phase and the disc and ring acceptance tests fail). The research record's proposed target is a reduction of the error by 1.4 to 10 times.

## Measured result

Acceptance run of 2026-10-28 (E3 report D2 and D5), test setup (850 nm, focal length 250 mm, pitch 12.5 um), signal error as the test defines it (the relative RMS error with the
intensity and the target each normalized to unit sum in the region), 100 MRAF iterations:

| Grid | Target | OT-initialized error | MRAF from a random start |
|---|---|---|---|
| Live (128 by 128) | disc | 0.0204 | 0.250 and 0.273 |
| Live | ring | 0.0179 | 0.192 and 0.188 |
| Live | line | 0.0221 | 0.250 and 0.223 |
| Baked (256 by 256) | disc | 0.0259 | 0.266 |
| Baked | ring | 0.0171 | 0.228 |

Efficiency 0.445 (the closed form gives 0.444). About 10 times lower error than the random start. The OT start takes no randomness (one run per target); the two baseline values of
a live target are two random starts; the benchmark repeats over 20 seeds (its rows are not yet in `data/derived/benchmark/results.json`). Published: error 0.17 to 0.96 percent with
efficiency 53 to 85 percent (OT) against 1.5 to 3.9 percent and 18 to 45 percent (MRAF); DinHot's efficiency is in the MRAF class, not in the OT class of the paper, and its errors
are 1.7 to 2.6 percent.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C04 only, a disc scored on the case's crosstalk device, with its own
optics in `data/derived/manifests/`; M18 is deterministic, so the three seeds agree):

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.422 (0.422 to 0.422) | 26.6 (26.6 to 26.6) |

## Limits and failure modes

- The Sinkhorn equations of the second source are marked ESTIMATED in the research record; the implementation is checked by marginals and recovery tests, not against the paper's numbers.
- The efficiency (0.445) does not reach the 53 to 85 percent of the paper: the fixed point of the MRAF stage at $m = 0.4$ is 0.44.
- The barycentric map of an entropic plan has a small curl; the Poisson integration projects it to the nearest curl-free map.
- Ideal-device model: scored on the C04 crosstalk device its error is 26.6 percent, close to M13's 25.8 percent and far above the ideal-device acceptance values.

## References

- Swan, Torchylo, Van de Graaff, Rudolph and Hogan 2024, https://arxiv.org/abs/2408.17025
- Torchylo, Swan, Tellez and Hogan 2025, https://arxiv.org/abs/2512.19072
- Pasienski and DeMarco 2008, Opt. Express 16, 2176, https://doi.org/10.1364/OE.16.002176
