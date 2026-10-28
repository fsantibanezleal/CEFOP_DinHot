# Case C07_high_na, High numerical aperture, 5 x 5

- **Category:** Device and optics
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** What changes when the numerical aperture is high, and where does the scalar model stop being valid?

## Why this case exists

The honesty case. The engine is scalar (Fraunhofer and angular spectrum); at a numerical aperture of 1.2 in water the real focus is vectorial. The case runs the same array with the manifest flag that says so.

## Formalization

The record below is the case's params record (catalog row params-record). It is written by the `cases` command of `data-pipeline/run.py` from `data-pipeline/pipeline/cases/library.py`
into `data/examples/cases.json`; contract 1 reads it back and refuses it with a reason if it breaks the schema or a range
([the data contracts](../../architecture/08_data-contracts.md)).

| Parameter | Value |
|---|---|
| Wavelength | 1064 nm |
| Focal length | 2.4 mm |
| Numerical aperture, immersion index | 1.2, 1.33 |
| SLM | 256 by 256 pixels, pitch 10 um, padding 2 (FFT grid 512 by 512) |
| Input beam | gaussian, waist fraction 1.0 |
| Focal bin, Fourier unit, half field | 0.499 um, 0.997 um, 127.68 um |
| Target | 25 traps; x from -6 to 6 um, y from -6 to 6 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M07 (the one whose maps the replay shows) |
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
- [M09](../../frameworks/M09_direct-search.md), Direct search
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [B3](../../frameworks/B3_learned-warm-start.md), Learned warm start for phase-fixed WGS
- [B4](../../frameworks/B4_aberration-robust-hologram.md), Aberration-robust hologram
- [B5](../../frameworks/B5_pareto-front.md), Efficiency-uniformity Pareto front

## Expected results

Twenty-five traps at NA 1.2 in water. The scalar model is used past its validity (the contract-1 flag is raised from NA 0.7): the manifest carries the flag and the trap shape is not the vectorial one. The case band is efficiency 0.5 to 1, relative standard deviation up to 15 percent.

### Expected ranges (checked by the bake)

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.5 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 15 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

## Validation anchor

Leutenegger et al. 2006 for the vectorial correction (equations not read in this build); no published band, https://doi.org/10.1364/OE.14.011277

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Focal plane | the scalar focal intensity with the validity flag shown |
| Traps | per-trap intensity |

## Notes

The bands are provisional. No vectorial lane exists in the engine in this build: the high-NA case carries a validity flag, and a vectorial lane is built only from equations read at the source. The Richards-Wolf forms and the Debye form of Leutenegger et al. 2006 were read in the research record, but no numeric threshold of scalar failure was found in the sources read (UNVERIFIED). This case stays a scalar case, labelled as such.
