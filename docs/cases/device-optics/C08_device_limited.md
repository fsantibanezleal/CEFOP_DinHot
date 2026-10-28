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

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.1 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 40 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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
