# M08, Mixed-region amplitude freedom (MRAF)

| Item | Value |
|---|---|
| Family | full-field GS |
| Lane | live |
| Targets, dimensions | shaped fields, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m08_mraf.py`, `SPEC` line 28, `run` line 32; engine `_gs.py` |
| Anchor | Pasienski and DeMarco, Opt. Express 16, 2176 (2008) |

## Purpose

For smooth potentials (a disc, a ring, a bar) GS leaves speckle in the signal region. MRAF leaves the amplitude free outside the
signal region, so the power that the shape does not need drains into a noise region and the shape comes out accurate. The price
is efficiency: much of the light is deliberately thrown away.

## Equations

With signal region SR, noise region NR and mixing parameter $m$:

$$G^{(n)} = \Big\{ m\,T\big|_{SR} + (1-m)\,\big|E^{(n)}_{out}\big|\,\Big|_{NR} \Big\}\;e^{\,i\arg E^{(n)}_{out}}, \qquad
\phi^{(n+1)} = \arg \mathcal{F}^{-1} G^{(n)}$$

and the SLM amplitude is reset to the beam. The signal amplitude $T$ (`Target.amplitude` inside `Target.mask`) is rescaled to the
input power. In the signal region the amplitude is forced to $mT$; in the noise region it is kept (scaled by $1-m$). $m = 1$ is
plain GS. Source: Pasienski and DeMarco 2008, Eq. (1), https://doi.org/10.1364/OE.16.002176 , https://arxiv.org/abs/0712.0794 (the
same in Holland et al. with a parameter $p$). Published (768 by 768): error 0.015 to 0.039 against 0.21 to 0.36 for GS, efficiency
0.18 to 0.45 against 0.96 to 0.99.

## Implementation

Defaults (`run`, line 32): `mixing = 0.3` (the paper reports 0.30 to 0.40; on DinHot's grid 0.3 gives error 0.03 and efficiency
0.18 for a disc of 60 bins radius, 0.4 gives 0.10 and 0.41), `start_waves = 20`.

Design decisions, stated in the module docstring and not in the source:

- The measure region is the shape eroded by one resolution cell (`pad` bins): pixels closer to the edge cannot reach their target.
  Without it the error floor is 0.10 to 0.13 and the ratio to GS is 1.4 to 3.8.
- The default start is a Fresnel-lens phase of 20 waves at the aperture edge, because a random start leaves speckle that MRAF
  removes slowly (error 0.3 after 100 iterations). The source states no start (UNVERIFIED). `start_waves = None` draws a random
  phase through `rng`; `init` overrides both.
- History: `efficiency` is the power fraction in the signal region; `error` is the paper's RMS fractional error $\eta$ (Eq. (2),
  intensity rescaled to the target) over the measure region.
- Offset-MRAF variants (Gaunt, Bruce, van Bijnen) are not implemented: their primary papers were not opened.

## Acceptance criterion and test

On disc, ring and bar targets, signal-region error at least five times below GS at the cost of efficiency:
`tests/methods/baseline/test_m08_mraf.py::test_signal_error_five_times_below_gs_at_the_cost_of_efficiency`; the thin-line limit is
pinned by `::test_thin_line_is_resolution_limited`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Target | Error GS | Error MRAF | Ratio [min, max] |
|---|---|---|---|
| Disc, radius 60 bins | 0.390 | 0.027 | 14.5 [12.4, 16.6] |
| Ring, 45 to 75 bins | 0.285 | 0.036 | 7.9 [7.8, 8.0] |
| Bar, 240 by 40 bins | 0.484 | 0.040 | 12.1 [10.4, 13.9] |
| Line, 16 bins wide | not reported | not reported | 3.2 (resolution limited, below the 5 times bar) |

Conditions: two starts of 16 and 24 waves, 45 iterations, 256 by 256 padded 2. Efficiency: GS 0.97 to 0.99, MRAF 0.18. The error
floor on a thin line is the shape edge, not the method; a shape thinner than the erosion raises `ValueError`.

## Limits

Efficiency 0.18 at the default mixing; thin features are resolution limited; the start is a DinHot choice.

## References

- Pasienski and DeMarco 2008, Opt. Express 16, 2176, https://doi.org/10.1364/OE.16.002176 ; https://arxiv.org/abs/0712.0794
