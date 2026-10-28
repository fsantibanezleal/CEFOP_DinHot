# Case C12_calibration, Calibration: the 10 x 10 task of the baselines

- **Category:** Arrays
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Does the engine reproduce the published comparison of the analytic and Gerchberg-Saxton baselines on the 10 by 10 task?

## Why this case exists

The calibration case. Di Leonardo, Ianni and Ruocco compared superposition, random superposition, GS and weighted GS on one task; reproducing the ordering within this engine's seed spread is the evidence that the engine measures what the paper measured. A reader who doubts a number starts here.

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
| Target | 100 traps; x from -35.8596 to 35.8596 um, y from -35.8596 to 35.8596 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M06 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M03](../../frameworks/M03_random-mask.md), Random mask
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M05](../../frameworks/M05_gaa.md), Generalized adaptive additive GS
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS

## Expected results

At 8 Fourier units: superposition about 0.29 efficiency and 0.01 uniformity, random superposition 0.69 and 0.01, GS 0.94 and 0.60, weighted GS 0.93 and 0.99, each within the seed spread of this engine. The expected ranges below are set per method.

### Expected ranges (checked by the bake)

Basis of the bands: **anchor: a published result sets the band, with the margin of the seed spread**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `M06.efficiency` | 0.8 to 1 | M06: efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `M06.uniformity` | 0.9 to 1 | M06: uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |
| `M04.efficiency` | 0.8 to 1 | M04: efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `M04.uniformity` | 0.3 to 0.9 | M04: uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |
| `M02.efficiency` | 0.4 to 0.95 | M02: efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `M02.uniformity` | 0 to 0.3 | M02: uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |
| `M01.efficiency` | 0.1 to 0.6 | M01: efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `M01.uniformity` | 0 to 0.25 | M01: uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

## Validation anchor

Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, Table 1, https://doi.org/10.1364/OE.15.001913

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Convergence | metrics against iteration for the seven methods, with the published rows beside them |
| Traps | per-trap histograms by method |

## Notes

The published values are for a flat beam at 768 by 768 pixels; the case uses the product's Gaussian beam at 256 by 256, so the efficiency ceiling is 0.87 and the random-superposition uniformity measured in the unit test is 0.25 against the published 0.01 (see the cards of M02 and M04). The bands of this case are anchored to the published ordering with that margin.
