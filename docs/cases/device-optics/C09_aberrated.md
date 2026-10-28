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

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.2 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 40 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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
