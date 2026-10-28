# M08: Mixed-region amplitude freedom (MRAF)

| Item | Value |
|---|---|
| Ladder row | M08, tier sota (SDD, Method ladder) |
| Family, lane | full-field GS, live |
| Targets, dimensions | shaped fields only, 2D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m08_mraf.py` (`SPEC` line 28, `run` line 32) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` (`run_field` line 169, `measure_region` line 137, `field_error` line 155) |
| Gate | `tests/methods/baseline/test_m08_mraf.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m08`, line 136) and `frontend/src/engine/holo/methods/gs.ts` (`runField`, line 211) |
| Card | [M08](../../frameworks/M08_mraf.md) |

## Tier and role

State of the art, replicated: the method for smooth potentials (a disc, a ring, a bar) in which GS leaves speckle. The solution replicated
is Pasienski and DeMarco, Opt. Express 16, 2176 (2008), https://doi.org/10.1364/OE.16.002176 (arXiv https://arxiv.org/abs/0712.0794),
Eq. (1); the same rule appears in Holland et al. with a parameter $p$. MRAF leaves the amplitude free outside the signal region, so the
power that the shape does not need drains into a noise region and the shape comes out accurate. It is the base of M18 (optimal-transport
initialization) and the accuracy-for-efficiency reference of the shaped-target group of the ladder.

## Problem it answers

An accurate smooth potential (error of a few percent against 20 to 40 percent for GS) for atoms or particles, at the deliberate cost of
efficiency.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `field`: `amplitude` (non-negative, finite) and `mask` (the boolean signal region) on the
  `n_fft` by `n_fft` focal grid, with the shape being `mask & (amplitude > 0)`; a trap target raises a `ValueError` naming `field`.
  `budget`, `rng`, optional `init`, `mixing` in $(0, 1]$, `start_waves`. A shaped target must be `n_fft` by `n_fft` and have power
  (`_gs.py` lines 177 to 184). `device` ignored.
- Output: `Result` with `phi`, one `history` entry per iteration: `efficiency` (the power fraction in the signal region),
  `uniformity` and `rel_std` of the ratio $I/T^2$ over the measure region, `error` (the RMS fractional error $\eta$), `time_s`;
  `fields` is the focal field; `meta` has `method`, `mixing`, `iterations`.

## The method

With signal region SR, noise region NR and mixing parameter $m$ (Pasienski and DeMarco 2008, Eq. (1)):

$$G^{(n)} = \Big\{ m\,T\big|_{SR} + (1-m)\,\big|E^{(n)}_{\rm out}\big|\,\Big|_{NR} \Big\}\,e^{\,i\arg E^{(n)}_{\rm out}},\qquad
\phi^{(n+1)} = \arg \mathcal F^{-1} G^{(n)}$$

and the SLM amplitude is reset to the beam. In the signal region the amplitude is forced to $mT$; in the noise region it is kept, scaled
by $1-m$. $m = 1$ is plain GS (zero noise region; `::test_mixing_one_is_gs`). The signal amplitude $T$ (`Target.amplitude` inside
`Target.mask`) is rescaled to the input power, $\sum T^2 = N_{pix}$ (`_gs.py` line 185). The code step is lines 196 and 197.

The error of the history is the paper's RMS fractional error (Eq. (2), the intensity rescaled to the target),

$$\eta = \sqrt{\Big\langle\Big(\frac{s\,I - T^2}{T^2}\Big)^2\Big\rangle},\qquad s = \frac{\sum T^2}{\sum I}$$

over the measure region (`field_error`, line 155).

Design decisions of DinHot, none of them in the source (module docstring and E2 report D3):

- The measure region is the shape eroded by one resolution cell (`pad` bins, `measure_region`, line 137): a pixel closer to the shape edge than
  the cell cannot reach its target for any hologram. Without it the error floor is 0.10 to 0.13 and the ratio to GS 1.4 to 3.8. A shape thinner
  than the erosion raises a `ValueError`.
- The default start is a Fresnel-lens phase of `start_waves` waves at the aperture edge (`start_phase_field`, line 213), because a random
  start leaves speckle that MRAF removes slowly (error 0.3 after 100 iterations). The source states no start (UNVERIFIED).
  `start_waves=None` draws a uniform random phase through `rng`; `init` overrides both.
- Offset-MRAF variants (Gaunt, Bruce, van Bijnen) are not implemented; their primary papers were not opened.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `mixing` $m$ | 0.3 | `m08_mraf.py` line 32 | the paper reports 0.30 to 0.40 for MRAF; on DinHot's grid 0.3 gives error 0.03 and efficiency 0.18 for a disc of 60 bins radius, 0.4 gives 0.10 and 0.41 |
| `start_waves` | 20.0 (`_gs.START_WAVES`, line 166) | `m08_mraf.py` line 33 | DinHot's choice (above); the starts 16 and 24 are used in the acceptance test |

The benchmark tuning grid for M08 is `mixing` in (0.3, 0.4, 0.55, 0.7) (`FALLBACK_TUNING`, `data-pipeline/pipeline/benchmark/protocol.py`
line 55). The port's default is the same (`baseline.ts` line 139).

## Complexity and lane

$O(P\log P)$ per iteration, two FFTs ($P = n_{fft}^2$); Pasienski and DeMarco: MRAF converges in under 100 iterations. Lane `live`;
parity worst difference 7.2e-14 (T1 report D2). Acceptance runtime about 22 s per shape on the development machine (E2 report).

## Acceptance criterion and gate

Ladder row: on disc, ring and bar targets, signal-region error at least five times below GS at the cost of efficiency. Gate
`tests/methods/baseline/test_m08_mraf.py::test_signal_error_five_times_below_gs_at_the_cost_of_efficiency`: three shapes on the 256 by 256
padded-2 grid (512 by 512 focal grid): a disc of radius 60 bins, a ring from 45 to 75 bins and a bar of 240 by 40 bins (named `line` in the
test), each with the signal region the shape dilated by 8 bins; GS (M04) and MRAF at default mixing, 45 iterations, the two starts of 16
and 24 waves (the default start is deterministic, so the starts are varied instead of seeds); the error ratio GS over MRAF must be at least
5 for both starts, and the MRAF efficiency below the GS efficiency for both. `::test_thin_line_is_resolution_limited` pins the thin-line
limit and `::test_thin_shape_is_rejected` the erosion guard.

## Evaluation that confirms or refutes it

Confirmed if the ratio of errors is at least 5 on each shape and the efficiency is lower than GS's (accuracy bought with efficiency, as in
the paper). Refuted by the thin line: for a 16-bin wide line the ratio is 3.2 because the error floor is the shape edge, not the method; the
5x criterion is therefore met for shapes wider than the resolution cell and the thin-line limit is recorded as a result.

## Measured result

Acceptance run of 2026-10-28 (E2 report D3 and D5), 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), starts 16
and 24 waves, 45 iterations:

| Target | Error GS | Error MRAF | Ratio [min, max] |
|---|---|---|---|
| Disc, radius 60 bins | 0.390 | 0.027 | 14.5 [12.4, 16.6] |
| Ring, 45 to 75 bins | 0.285 | 0.036 | 7.9 [7.8, 8.0] |
| Bar, 240 by 40 bins | 0.484 | 0.040 | 12.1 [10.4, 13.9] |
| Line, 16 bins wide | not reported | not reported | 3.2 (resolution limited) |

Efficiency: GS 0.97 to 0.99, MRAF 0.18. Published (768 by 768, six targets): error 0.015 to 0.039 against 0.21 to 0.36 for GS, efficiency
0.18 to 0.45 against 0.96 to 0.99.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C04 only, a disc of 15
um radius scored on the case's crosstalk device with its own optics in `data/derived/manifests/`):

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.186 (0.186 to 0.186) | 205 (205 to 205) |

The bake value is not the acceptance value: the signal rms error of M08 on C04 is 205 percent (GS: 45 percent) while the acceptance test on the
ideal device gives 0.027 against 0.390. The cause is not established in the sources: the cases differ in several respects at once (the disc
radius is 30 bins in C04 against 60 in the test, the margin is 3 bins against 8, and the hologram is scored through the device with crosstalk
and 8-bit phase). A single-factor comparison was not run.

## Limits and failure modes

Efficiency 0.18 at the default mixing; thin features are resolution limited; the start is a DinHot choice; the device is not part of the
model (a hologram optimized on the ideal device is scored on the device in the bake). Not covered: offset-MRAF variants.

## References

- Pasienski and DeMarco 2008, Opt. Express 16, 2176, https://doi.org/10.1364/OE.16.002176 ; https://arxiv.org/abs/0712.0794
- Holland et al., the same rule with a parameter $p$, as recorded in the research dossier (no URL was recorded: not established)
