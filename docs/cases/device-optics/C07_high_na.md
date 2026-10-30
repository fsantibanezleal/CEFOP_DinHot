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

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B3.efficiency` | 0.7068 to 0.8639 | 0.791194, 0.786592, 0.778201 | fraction of the input power in the trap peaks |
| `B3.rel_std_pct` | 0 to 0.01261 | 0.00890973, 0.000274514, 0.00272695 | relative standard deviation of the trap intensities, in percent |
| `B3.uniformity` | 0.8999 to 1 | 0.999815, 0.999995, 0.999951 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B4.efficiency` | 0.6892 to 0.8424 | 0.773295, 0.765725, 0.758344 | fraction of the input power in the trap peaks |
| `B4.rel_std_pct` | 0.8851 to 1.082 | 0.940948, 0.99092, 1.01837 | relative standard deviation of the trap intensities, in percent |
| `B4.uniformity` | 0.8827 to 1 | 0.978878, 0.982684, 0.980684 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B5.efficiency` | 0.719 to 0.8787 | 0.798461, 0.803296, 0.794812 | fraction of the input power in the trap peaks |
| `B5.rel_std_pct` | 0 to 1.292 | 0.245685, 0.993082, 0.395742 | relative standard deviation of the trap intensities, in percent |
| `B5.uniformity` | 0.8907 to 1 | 0.994751, 0.982093, 0.992126 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.315 to 0.3851 | 0.350047, 0.350047, 0.350047 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 104.6 to 127.8 | 116.223, 116.223, 116.223 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.05185 to 0.06337 | 0.0576088, 0.0576088, 0.0576088 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6545 to 0.7999 | 0.721231, 0.750525, 0.709864 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 28.94 to 46.48 | 33.4664, 37.4188, 42.239 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.2403 to 0.4807 | 0.3046, 0.424802, 0.352054 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M03.efficiency` | 0.03341 to 0.04084 | 0.0374461, 0.0376581, 0.0362691 | fraction of the input power in the trap peaks |
| `M03.rel_std_pct` | 10.96 to 19.3 | 15.9471, 16.8043, 12.6318 | relative standard deviation of the trap intensities, in percent |
| `M03.uniformity` | 0.5283 to 0.8232 | 0.684989, 0.597408, 0.744883 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.7298 to 0.8919 | 0.807314, 0.813961, 0.81127 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 9.07 to 27.3 | 18.7129, 22.4793, 13.3637 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.4876 to 0.8092 | 0.614498, 0.584965, 0.745748 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M05.efficiency` | 0.7217 to 0.8821 | 0.804274, 0.799457, 0.801996 | fraction of the input power in the trap peaks |
| `M05.rel_std_pct` | 10.3 to 17.87 | 12.7804, 12.9151, 16.5631 | relative standard deviation of the trap intensities, in percent |
| `M05.uniformity` | 0.6145 to 0.8356 | 0.742202, 0.771783, 0.66121 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7175 to 0.8769 | 0.801937, 0.793053, 0.796611 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0 to 1.694 | 0.574757, 0.386807, 1.31987 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8855 to 1 | 0.988432, 0.991501, 0.971786 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.7068 to 0.8639 | 0.791194, 0.786592, 0.778201 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 0.01261 | 0.00890973, 0.000274514, 0.00272695 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8999 to 1 | 0.999815, 0.999995, 0.999951 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M09.efficiency` | 0.5741 to 0.7017 | 0.637759, 0.646446, 0.629601 | fraction of the input power in the trap peaks |
| `M09.rel_std_pct` | 0.001831 to 0.003964 | 0.00263377, 0.00356201, 0.00249549 | relative standard deviation of the trap intensities, in percent |
| `M09.uniformity` | 0.9 to 1 | 0.999956, 0.99993, 0.999956 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.1705 to 0.2084 | 0.196344, 0.185278, 0.186626 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 47.92 to 78.51 | 55.6373, 63.0843, 70.9308 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0 to 0.1989 | 0.157069, 0.0393658, 0.0354441 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M11.efficiency` | 0.6897 to 0.8429 | 0.767005, 0.768947, 0.762956 | fraction of the input power in the trap peaks |
| `M11.rel_std_pct` | 1.257 to 3.724 | 2.00147, 2.2345, 3.23477 | relative standard deviation of the trap intensities, in percent |
| `M11.uniformity` | 0.8519 to 1 | 0.958417, 0.94644, 0.934936 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

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
