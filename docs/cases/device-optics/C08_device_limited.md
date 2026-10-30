# Case C08_device_limited, Device-limited array, 4-bit phase and crosstalk

- **Category:** Device and optics
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** What does a real device cost a trap array, and what does a device-aware method win back?

## Why this case exists

Quantization to 4 bits, pixel crosstalk, a fill factor of 0.85 and phase flicker together. It is the case for the device model ([P02](../../frameworks/P02_device-model.md)) and for B1, the device-aware weighted GS.

## Formalization

The record below is the case's params record (catalog row params-record). It is written by the `cases` command of `data-pipeline/run.py` from `data-pipeline/pipeline/cases/library.py`
into `data/examples/cases.json`; contract 1 reads it back and refuses it with a reason if it breaks the schema or a range
([the data contracts](../../architecture/08_data-contracts.md)).

| Parameter | Value |
|---|---|
| Wavelength | 850 nm |
| Focal length | 3 mm |
| Numerical aperture, immersion index | 0.5, 1.0 |
| SLM | 128 by 128 pixels, pitch 20 um, padding 2 (FFT grid 256 by 256) |
| Input beam | gaussian, waist fraction 1.0 |
| Focal bin, Fourier unit, half field | 0.498 um, 0.996 um, 63.75 um |
| Target | 64 traps; x from -17.5 to 17.5 um, y from -17.5 to 17.5 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | B1 (the one whose maps the replay shows) |
| Device | 4 bits, crosstalk sigma 1.24 and q 1.8 on 3 by 3 sub-pixels, fill factor 0.85, flicker 0.05 rad |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M13](../../frameworks/M13_crosstalk-aware-cg.md), Device-aware CG with pixel crosstalk
- [B1](../../frameworks/B1_device-aware-wgs.md), Device-aware weighted GS
- [B4](../../frameworks/B4_aberration-robust-hologram.md), Aberration-robust hologram

## Expected results

An 8 by 8 array on a device with 4-bit phase, pixel crosstalk, a fill factor of 0.85 and flicker of 0.05 rad rms. The device-aware weighted GS recovers uniformity that the ideal-model methods lose. The case band is efficiency 0.1 to 1, relative standard deviation up to 40 percent. In the unit test of B1 (a different task, 10 by 10 on a crosstalk device) the device-aware method reached a spread 49 times below phase-fixed WGS.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B1.efficiency` | 0.5894 to 0.7204 | 0.651959, 0.65069, 0.662057 | fraction of the input power in the trap peaks |
| `B1.rel_std_pct` | 5.363 to 7.629 | 7.04366, 6.53407, 5.9105 | relative standard deviation of the trap intensities, in percent |
| `B1.uniformity` | 0.7762 to 0.9486 | 0.847098, 0.853563, 0.886535 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B4.efficiency` | 0.6026 to 0.7365 | 0.666374, 0.672037, 0.670147 | fraction of the input power in the trap peaks |
| `B4.rel_std_pct` | 11.65 to 14.24 | 13.5564, 12.5261, 12.7619 | relative standard deviation of the trap intensities, in percent |
| `B4.uniformity` | 0.6453 to 0.7887 | 0.73047, 0.714561, 0.705836 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.6279 to 0.7674 | 0.69205, 0.697549, 0.703241 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 17.88 to 30.66 | 21.6183, 23.1809, 28.0094 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.2985 to 0.6293 | 0.538766, 0.47958, 0.373332 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.6199 to 0.7577 | 0.682286, 0.695114, 0.689058 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 11.78 to 15.5 | 14.3443, 12.487, 14.0836 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.661 to 0.8079 | 0.74533, 0.73333, 0.724637 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.6105 to 0.7462 | 0.674921, 0.680548, 0.679575 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 11.89 to 14.54 | 13.4238, 13.0504, 13.17 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.6439 to 0.787 | 0.684915, 0.730176, 0.731392 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.2802 to 0.3425 | 0.316147, 0.314019, 0.304 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 26.44 to 38.03 | 29.686, 35.4839, 31.5312 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0 to 0.6493 | 0.272599, 0.0403927, 0.439034 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M13.efficiency` | 0.1229 to 0.7132 | 0.455512, 0.546926, 0.251742 | fraction of the input power in the trap peaks |
| `M13.rel_std_pct` | 0 to 54.66 | 23.6766, 11.3059, 40.7317 | relative standard deviation of the trap intensities, in percent |
| `M13.uniformity` | 0 to 0.976 | 0.349082, 0.684537, 0.0795869 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

## Validation anchor

Crosstalk parameters from Schroff et al. 2023; the 4-bit, fill-factor and flicker effects have no published source in this build (computed only), https://doi.org/10.1038/s41598-023-30296-6

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Hologram | the phase mask ideal, quantized and crosstalk-blurred, and the device effects panel |
| Focal plane | the focal intensity with zero order and replicas |
| Traps | per-trap intensity on the device against the ideal model |

## Notes

The bands are provisional. The crosstalk parameters are those of Schroff et al. 2023; the 4-bit, fill-factor and flicker effects have no published source for this device in the research record (computed only), and the unit of the kernel's k is UNVERIFIED. The grid is 128 pixels at 3 mm focal length (half field 63.75 um).
