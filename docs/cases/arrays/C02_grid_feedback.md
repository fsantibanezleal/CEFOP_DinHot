# Case C02_grid_feedback, Grid with camera feedback, 10 x 10

- **Category:** Arrays
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** How far can a camera feedback loop bring the depth spread of a 10 by 10 array, and how fast?

## Why this case exists

The published feedback result of Nogrette et al. is the anchor of the product's camera-in-the-loop emulator: the open-loop spread of 19 percent rms (the emulated camera's gain error) falls to the order of 1.4 percent in 20 steps at gain 0.7. It is also the case the App opens on.

## Formalization

The record below is the case's params record (catalog row params-record). It is written by the `cases` command of `data-pipeline/run.py` from `data-pipeline/pipeline/cases/library.py`
into `data/examples/cases.json`; contract 1 reads it back and refuses it with a reason if it breaks the schema or a range
([the data contracts](../../architecture/08_data-contracts.md)).

| Parameter | Value |
|---|---|
| Wavelength | 850 nm |
| Focal length | 6 mm |
| Numerical aperture, immersion index | 0.5, 1.0 |
| SLM | 256 by 256 pixels, pitch 20 um, padding 2 (FFT grid 512 by 512) |
| Input beam | gaussian, waist fraction 1.0 |
| Focal bin, Fourier unit, half field | 0.498 um, 0.996 um, 127.50 um |
| Target | 100 traps; x from -18 to 18 um, y from -18 to 18 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M07 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Camera feedback | gain 0.7, 20 steps, camera gain error 0.19 rms |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M03](../../frameworks/M03_random-mask.md), Random mask
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M05](../../frameworks/M05_gaa.md), Generalized adaptive additive GS
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M09](../../frameworks/M09_direct-search.md), Direct search
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [B3](../../frameworks/B3_learned-warm-start.md), Learned warm start for phase-fixed WGS
- [B4](../../frameworks/B4_aberration-robust-hologram.md), Aberration-robust hologram
- [B5](../../frameworks/B5_pareto-front.md), Efficiency-uniformity Pareto front
- [M12](../../frameworks/M12_closed-loop-wgs.md), Closed-loop WGS on an emulated camera

## Expected results

One hundred traps whose measured depths spread by 19 percent rms before feedback. Twenty closed-loop steps at gain 0.7 bring the measured spread to the order of 1.4 percent, a 15-fold reduction. The bake fails if the initial spread is outside 10 to 30 percent or the final spread above 3 percent.

### Expected ranges (checked by the bake)

Basis of the bands: **anchor: a published result sets the band, with the margin of the seed spread**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.6 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `uniformity` | 0.8 to 1 | uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |
| `rel_std_pct` | 0 to 10 | relative standard deviation of the trap intensities, in percent |
| `feedback_initial_rel_std_pct` | 10 to 30 | measured spread before the camera loop, in percent |
| `feedback_final_rel_std_pct` | 0 to 3 | measured spread after the camera loop, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

## Validation anchor

Nogrette et al. 2014, Phys. Rev. X 4, 021034, section III.E and Fig. 9 (19 percent rms to 1.4 percent in 20 iterations at gain 0.7), https://arxiv.org/abs/1402.5329

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Convergence | the camera feedback curve, spread against feedback step, next to the open-loop value |
| Traps | per-trap intensity before and after feedback |

## Notes

This is the one case with an anchor band for its main quantity. The camera is an emulation ([P06](../../frameworks/P06_emulated-camera.md)); the result shows that the loop works against stated errors, not against an instrument. The App opens on this case (the library constant DEFAULT_CASE).
