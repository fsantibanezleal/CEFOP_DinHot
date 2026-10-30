# M18, Optimal-transport initialized MRAF

| Item | Value |
|---|---|
| Family | optimization |
| Lane | baked |
| Targets, dimensions | shaped fields, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/optim/m18_ot_mraf.py`, `SPEC` line 51, `run` line 151 |
| Anchor | Swan et al. 2024; Torchylo et al. 2025 |

## Purpose

MRAF from a random start leaves speckle that it removes slowly. An optimal-transport (OT) map between the input beam and the target
intensity gives a smooth phase that already sends the light roughly to the right place, so MRAF starts close to its answer.

## Equations

Under the stationary-phase approximation the SLM phase satisfies the Monge-Ampere equation $G^2(\nabla\phi(x))\,\det(\nabla^2\phi(x)) = g^2(x)$ with $g^2$ the
input intensity and $G^2$ the target intensity; the quadratic-cost OT map $\gamma$ between them (Sinkhorn, $\epsilon = 0.001$) is integrated,
$\phi(x) = \int \gamma(s)\cdot ds$, and seeds GS or MRAF (Swan et al., arXiv 2408.17025, https://arxiv.org/abs/2408.17025 ). Their Table 1 (six
targets): MRAF error 1.5 to 3.9 percent with efficiency 18 to 45 percent; with OT initialization 0.17 to 0.96 percent with efficiency 53 to 85
percent. Torchylo et al. (arXiv 2512.19072, https://arxiv.org/abs/2512.19072 ): the dual form with a separable cost needs $O(N)$ memory, with the plan
$\Gamma = u\,K\,v$, $K = K_x\otimes K_y$ and the updates (the source equation is marked ESTIMATED in the research record)

$$u \leftarrow g^2 \oslash (\Lambda v \Lambda), \qquad v \leftarrow G^2 \oslash (\Lambda^T u \Lambda^T)$$

evaluated as matrix products (`Ky @ v @ Kx.T`). Here the cost is $|x-y|^2/2$ with $x$ the SLM pixel coordinate and $y$ the focal bin coordinate; the
stationary-phase relation is $k = (n_{fft}/2\pi)\,d\phi/dj$, so $\phi = (2\pi/n_{fft})\Psi$ with $\nabla\Psi = T$ the barycentric OT map. $T$ is integrated to
$\Psi$ by a least-squares Poisson solve on a mirror-extended grid (Frankot and Chellappa 1988, named in the module and not re-read). Then MRAF with
$m = 0.4$ (Pasienski and DeMarco 2008, see [M08](M08_mraf.md)); the fixed-point efficiency solves $\eta = m^2/(m^2 + (1-m)^2(1-\eta))$, which is 0.44.

## Implementation

Defaults (`m18_ot_mraf.py`, lines 53 to 55): `mix = 0.4`, `eps = 0.001`, `ot_iterations = 200`. The kernel width is
$\sigma^2 = \epsilon\,n_{fft}^2$ bins squared. The start is the OT phase; `init` replaces it (a random phase is the baseline of the acceptance
test). Grids: live size 128 by 128 (64 pixel SLM padded 2), baked 256 by 256 (128 pixel SLM padded 2). The model is the ideal device.
UNVERIFIED: the target amplitude is normalised to the total input power $n_{pix}^2$; the source does not state the normalisation (rescaling it
to the current signal-region power instead drains the signal region, efficiency 0.001).

## Acceptance criterion and test

Lower error than MRAF from a random start on the shaped targets:
`tests/methods/optim/test_m18_ot_mraf.py::test_acceptance_live_size_lower_error_than_random_start` and
`::test_acceptance_baked_size_lower_error_than_random_start`. Component tests: both Sinkhorn marginals (source marginal error below 1e-6, target
marginal below 1e-9), a pure shift is recovered to 0.6 bin, the Poisson integration recovers a known potential to 2 percent.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Grid | Target | OT-initialized error | MRAF from a random start |
|---|---|---|---|
| Live (128 by 128) | disc | 0.0204 | 0.250 and 0.273 |
| Live | ring | 0.0179 | 0.192 and 0.188 |
| Live | line | 0.0221 | 0.250 and 0.223 |
| Baked (256 by 256) | disc | 0.0259 | 0.266 |
| Baked | ring | 0.0171 | 0.228 |

Efficiency 0.445 (the closed form for $m = 0.4$ gives 0.444). About 10 times lower error than the random start. Conditions: the OT start takes no
randomness (one run per target); the two baseline values of a live target are two random starts; the benchmark repeats over 20 seeds.

## Limits

- The Sinkhorn equations of the second source are marked ESTIMATED in the research record; the implementation is checked by marginals and
  recovery tests, not against the paper's numbers.
- The barycentric map of an entropic plan has a small curl; the Poisson integration projects it to the nearest curl-free map.

## References

- Swan, Torchylo, Van de Graaff, Rudolph and Hogan 2024, https://arxiv.org/abs/2408.17025
- Torchylo, Swan, Tellez and Hogan 2025, https://arxiv.org/abs/2512.19072
- Pasienski and DeMarco 2008, https://doi.org/10.1364/OE.16.002176
