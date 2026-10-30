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
| `M01.efficiency` | 0.1 to 0.6 | 0.328038, 0.328038, 0.328038 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 241.9 to 295.7 | 268.793, 268.793, 268.793 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0 to 0.25 | 0.000275066, 0.000275066, 0.000275066 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.4 to 0.95 | 0.748511, 0.73952, 0.720278 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 34.22 to 47.1 | 37.4001, 43.8379, 40.7397 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0 to 0.3 | 0.199351, 0.201726, 0.147702 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M03.efficiency` | 0.009093 to 0.01111 | 0.00994056, 0.0103849, 0.00998588 | fraction of the input power in the trap peaks |
| `M03.rel_std_pct` | 44.22 to 57.72 | 54.2525, 51.1586, 47.4979 | relative standard deviation of the trap intensities, in percent |
| `M03.uniformity` | 0.03575 to 0.08993 | 0.076802, 0.0620008, 0.0497132 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.8 to 1 | 0.817436, 0.812128, 0.821133 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 14.89 to 22.09 | 19.9715, 19.1273, 16.3748 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.3 to 0.9 | 0.50641, 0.577994, 0.639783 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M05.efficiency` | 0.7318 to 0.8944 | 0.818234, 0.805436, 0.815609 | fraction of the input power in the trap peaks |
| `M05.rel_std_pct` | 10.65 to 14.55 | 11.8091, 13.7612, 12.2335 | relative standard deviation of the trap intensities, in percent |
| `M05.uniformity` | 0.5954 to 0.7972 | 0.737876, 0.636967, 0.714126 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.8 to 1 | 0.804899, 0.797766, 0.799084 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.7508 to 1.548 | 1.01918, 1.01531, 1.41398 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.9 to 1 | 0.970475, 0.974705, 0.971 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.7126 to 0.871 | 0.79743, 0.786095, 0.791856 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 1.976 | 0.0127528, 0.0283098, 1.48154 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8906 to 1 | 0.999629, 0.999299, 0.969773 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

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
