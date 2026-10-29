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

Basis of the bands: **anchor**. The keys without a method name are the published bands of the validation anchor, kept as
declared (they apply to the reference method); the `<method>.<metric>` keys are measured and added where the anchor declares
nothing: 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of 10 percent of the mean
and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B3.efficiency` | 0.713 to 0.8714 | 0.797685, 0.788096, 0.790871 | fraction of the input power in the trap peaks |
| `B3.rel_std_pct` | 0 to 1.213 | 0.0137721, 0.847503, 0.276191 | relative standard deviation of the trap intensities, in percent |
| `B3.uniformity` | 0.8933 to 1 | 0.999616, 0.983652, 0.994398 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B4.efficiency` | 0.7 to 0.8556 | 0.782997, 0.773785, 0.776568 | fraction of the input power in the trap peaks |
| `B4.rel_std_pct` | 0.7664 to 0.9367 | 0.867379, 0.834774, 0.852543 | relative standard deviation of the trap intensities, in percent |
| `B4.uniformity` | 0.8805 to 1 | 0.975742, 0.97829, 0.980916 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B5.efficiency` | 0.7226 to 0.8832 | 0.797685, 0.810737, 0.800334 | fraction of the input power in the trap peaks |
| `B5.rel_std_pct` | 0 to 1.657 | 4.38793e-08, 1.12951, 0.453452 | relative standard deviation of the trap intensities, in percent |
| `B5.uniformity` | 0.8898 to 1 | 1, 0.976006, 0.989895 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.2526 to 0.3087 | 0.280665, 0.280665, 0.280665 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 247 to 301.8 | 274.408, 274.408, 274.408 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.0002515 to 0.0003073 | 0.000279394, 0.000279394, 0.000279394 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6615 to 0.8085 | 0.747508, 0.737744, 0.719754 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 33.39 to 46.15 | 35.9176, 42.302, 41.0893 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.04769 to 0.2902 | 0.221772, 0.184613, 0.100499 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M03.efficiency` | 0.008594 to 0.01108 | 0.00903621, 0.0101941, 0.0102791 | fraction of the input power in the trap peaks |
| `M03.rel_std_pct` | 48.26 to 58.99 | 53.6104, 52.3795, 54.8811 | relative standard deviation of the trap intensities, in percent |
| `M03.uniformity` | 0 to 0.1528 | 0.0438313, 0.118442, 0.0295858 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.7349 to 0.8982 | 0.818428, 0.812474, 0.818727 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 13.78 to 20.77 | 19.4828, 15.9878, 16.3678 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.4309 to 0.7049 | 0.488107, 0.625073, 0.59055 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M05.efficiency` | 0.7325 to 0.8953 | 0.817815, 0.81151, 0.812476 | fraction of the input power in the trap peaks |
| `M05.rel_std_pct` | 10.36 to 15.52 | 11.9326, 12.3743, 14.5153 | relative standard deviation of the trap intensities, in percent |
| `M05.uniformity` | 0.6444 to 0.7875 | 0.741704, 0.711418, 0.694724 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7224 to 0.883 | 0.805825, 0.800984, 0.801312 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.5456 to 1.759 | 0.858898, 1.4658, 1.13272 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8742 to 1 | 0.977388, 0.969956, 0.966595 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.713 to 0.8714 | 0.797684, 0.788095, 0.790872 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 1.212 | 0.0139209, 0.848173, 0.269946 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8933 to 1 | 0.999613, 0.983633, 0.994461 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M09.efficiency` | 0.5842 to 0.714 | 0.657677, 0.653501, 0.635997 | fraction of the input power in the trap peaks |
| `M09.rel_std_pct` | 0.01229 to 0.01502 | 0.0131756, 0.014308, 0.0134884 | relative standard deviation of the trap intensities, in percent |
| `M09.uniformity` | 0.8997 to 1 | 0.999661, 0.999609, 0.999673 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.2334 to 0.2852 | 0.259251, 0.253577, 0.265124 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 34.7 to 47.48 | 44.4191, 38.0264, 40.8258 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0.001011 to 0.0712 | 0.0189844, 0.0352554, 0.0540804 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M11.efficiency` | 0.6863 to 0.8388 | 0.76265, 0.762043, 0.763015 | fraction of the input power in the trap peaks |
| `M11.rel_std_pct` | 2.248 to 2.748 | 2.6042, 2.49446, 2.39494 | relative standard deviation of the trap intensities, in percent |
| `M11.uniformity` | 0.836 to 1 | 0.921112, 0.923441, 0.942244 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M12.efficiency` | 0.7251 to 0.8862 | 0.813791, 0.802263, 0.800928 | fraction of the input power in the trap peaks |
| `M12.rel_std_pct` | 17.83 to 21.79 | 19.2096, 20.7835, 19.4476 | relative standard deviation of the trap intensities, in percent |
| `M12.uniformity` | 0.459 to 0.6478 | 0.6109, 0.516493, 0.532813 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `efficiency` | 0.6 to 1 | declared (anchor) | fraction of the input power in the trap peaks |
| `feedback_final_rel_std_pct` | 0 to 3 | 1.3371, 0.0208, 0.1355 | measured spread after the camera loop, in percent |
| `feedback_initial_rel_std_pct` | 10 to 30 | 20.1121, 18.4063, 19.4962 | measured spread before the camera loop, in percent |
| `rel_std_pct` | 0 to 10 | declared (anchor) | relative standard deviation of the trap intensities, in percent |
| `uniformity` | 0.8 to 1 | declared (anchor) | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

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
