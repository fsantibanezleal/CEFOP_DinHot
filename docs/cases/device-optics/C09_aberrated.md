# Case C09_aberrated, Aberrated array, with and without correction

- **Category:** Device and optics
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** What do wavefront aberrations cost an array, and does a Zernike correction recover it?

## Why this case exists

The aberration case: a system wavefront of six Noll modes (0.147 waves rms by the root sum of squares of the record's coefficients, which the case calls 0.15). It is the case for sensorless modal recovery (M14) and the robust hologram (B4).

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
| Target | 16 traps; x from -7.5 to 7.5 um, y from -7.5 to 7.5 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M14 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Aberration (Noll index: waves) | 4: 0.08, 5: 0.07, 6: 0.05, 7: 0.06, 8: -0.05, 11: 0.04 |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M14](../../frameworks/M14_zernike-correction.md), Zernike correction and sensorless recovery
- [B4](../../frameworks/B4_aberration-robust-hologram.md), Aberration-robust hologram

## Expected results

A 4 by 4 array with the injected wavefront. Methods that ignore the aberration lose depth and uniformity; the Zernike correction recovers them. The published result is a wavefront rms of 0.15 falling to 0.014 waves with the trap depth up by about 50 percent. The case band is efficiency 0.2 to 1, relative standard deviation up to 40 percent. In the unit test of M14 the sensorless search recovered Noll 4 to 11 within 0.3 percent per mode (worst measured 0.0023).

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B4.efficiency` | 0.3985 to 0.487 | 0.448389, 0.433588, 0.446296 | fraction of the input power in the trap peaks |
| `B4.rel_std_pct` | 4.071 to 6.547 | 5.50111, 4.59428, 5.83217 | relative standard deviation of the trap intensities, in percent |
| `B4.uniformity` | 0.823 to 1 | 0.90901, 0.924989, 0.909324 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.187 to 0.2286 | 0.207777, 0.207777, 0.207777 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 70.53 to 86.2 | 78.3643, 78.3643, 78.3643 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.1385 to 0.1693 | 0.153904, 0.153904, 0.153904 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.4112 to 0.5026 | 0.457634, 0.457977, 0.455183 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 13.81 to 16.88 | 14.9758, 15.7108, 15.3581 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.6605 to 0.8073 | 0.739057, 0.726877, 0.735694 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.4044 to 0.4943 | 0.453299, 0.440877, 0.453859 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 3.478 to 8.551 | 7.30763, 4.77116, 5.96436 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8148 to 0.9959 | 0.886746, 0.914662, 0.914728 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.4027 to 0.4922 | 0.452637, 0.437777, 0.451986 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 3.732 to 8.596 | 7.09303, 4.66108, 6.73869 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8127 to 0.9933 | 0.889167, 0.924499, 0.895259 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M14.efficiency` | 0.7191 to 0.8789 | 0.805082, 0.786524, 0.805337 | fraction of the input power in the trap peaks |
| `M14.rel_std_pct` | 0 to 0.9327 | 0.0773177, 0.680228, 0.231835 | relative standard deviation of the trap intensities, in percent |
| `M14.uniformity` | 0.895 to 1 | 0.998793, 0.988886, 0.995665 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

## Validation anchor

Nogrette et al. 2014, Phys. Rev. X 4, 021034, section III.D (wavefront rms 0.15 to 0.014 waves, trap depth up by about 50 percent), https://arxiv.org/abs/1402.5329

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Aberrations | the Zernike coefficient bars, the wavefront map and the Strehl estimate, before and after correction |
| Traps | per-trap intensity with and without correction |

## Notes

The bands are provisional. The record injects Noll 4, 5, 6, 7, 8 and 11 with 0.08, 0.07, 0.05, 0.06, -0.05 and 0.04 waves. Noll indices above 11 and the Noll 1976 ordering are UNVERIFIED ([P03](../../frameworks/P03_zernike.md)).
