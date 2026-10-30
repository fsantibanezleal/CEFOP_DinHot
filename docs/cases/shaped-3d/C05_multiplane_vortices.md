# Case C05_multiplane_vortices, Three-plane array with vortices

- **Category:** Shaped and 3D
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Can traps at several depths, some of them vortices, be made equal from one hologram?

## Why this case exists

Three-dimensional manipulation and orbital angular momentum together: 51 traps on three planes 10 um apart, twelve of them optical vortices of charge 8. It is the case for the volumetric 3D GS (M19), the direct search (M09) and the vortex rule (M15).

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
| Target | 51 traps; x from -16 to 16 um, y from -13.8564 to 13.8564 um, planes z = -10, 0, 10 um; 12 vortex traps (charges [8]) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M09 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M09](../../frameworks/M09_direct-search.md), Direct search
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [M15](../../frameworks/M15_vortex-traps.md), Laguerre-Gaussian vortex traps
- [M19](../../frameworks/M19_volumetric-3d-gs.md), Volumetric 3D GS
- [B5](../../frameworks/B5_pareto-front.md), Efficiency-uniformity Pareto front

## Expected results

Direct search holds the traps near their planned relative brightness; the case band is efficiency 0.05 to 1 and relative standard deviation up to 40 percent. The published result is the traps within 5 percent after direct search.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B5.efficiency` | 0.8052 to 0.9842 | 0.8889, 0.900672, 0.894543 | fraction of the input power in the trap peaks |
| `B5.rel_std_pct` | 0.3461 to 0.9723 | 0.507178, 0.820251, 0.65014 | relative standard deviation of the trap intensities, in percent |
| `B5.uniformity` | 0.8866 to 1 | 0.988599, 0.981165, 0.985625 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.4069 to 0.4974 | 0.452161, 0.452161, 0.452161 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 71.47 to 87.35 | 79.4057, 79.4057, 79.4057 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.06732 to 0.08228 | 0.0747996, 0.0747996, 0.0747996 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6888 to 0.8419 | 0.781129, 0.734825, 0.780087 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 38.48 to 47.03 | 44.2407, 41.7446, 42.2738 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.2179 to 0.2663 | 0.249648, 0.232843, 0.24382 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.8172 to 0.9988 | 0.910685, 0.918278, 0.895113 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 13.73 to 24.97 | 22.3706, 16.7504, 18.9243 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.5429 to 0.6793 | 0.575155, 0.614726, 0.643368 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.8048 to 0.9837 | 0.890626, 0.897117, 0.895023 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0 to 2.964 | 0.495676, 2.29476, 0.70362 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8736 to 1 | 0.989372, 0.941553, 0.981203 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M09.efficiency` | 0.611 to 0.7468 | 0.698864, 0.660482, 0.677442 | fraction of the input power in the trap peaks |
| `M09.rel_std_pct` | 0.005688 to 0.007042 | 0.00608881, 0.0067656, 0.0062411 | relative standard deviation of the trap intensities, in percent |
| `M09.uniformity` | 0.8999 to 1 | 0.999862, 0.999807, 0.999853 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.1891 to 0.2311 | 0.21463, 0.206137, 0.209567 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 38.22 to 67.87 | 50.6766, 61.6454, 46.8207 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0 to 0.1137 | 0.0911055, 0.0253583, 0.0242694 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M11.efficiency` | 0.7399 to 0.9043 | 0.829609, 0.814048, 0.82264 | fraction of the input power in the trap peaks |
| `M11.rel_std_pct` | 1.594 to 1.948 | 1.79222, 1.75526, 1.76549 | relative standard deviation of the trap intensities, in percent |
| `M11.uniformity` | 0.8617 to 1 | 0.953493, 0.955439, 0.963476 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M15.efficiency` | 0.8048 to 0.9837 | 0.890626, 0.897117, 0.895023 | fraction of the input power in the trap peaks |
| `M15.rel_std_pct` | 0 to 2.964 | 0.495676, 2.29476, 0.70362 | relative standard deviation of the trap intensities, in percent |
| `M15.uniformity` | 0.8736 to 1 | 0.989372, 0.941553, 0.981203 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M19.efficiency` | 0.4731 to 0.5782 | 0.537797, 0.527583, 0.511657 | fraction of the input power in the trap peaks |
| `M19.rel_std_pct` | 56.13 to 68.6 | 62.0927, 62.553, 62.4565 | relative standard deviation of the trap intensities, in percent |
| `M19.uniformity` | 0 to 0.04135 | 0.0272664, 0.0174144, 0.0012115 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

## Validation anchor

Polin et al. 2005, Opt. Express 13, 5831 (51 traps, 12 vortices of charge 8, traps within 5 percent after direct search), https://doi.org/10.1364/OPEX.13.005831

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Focal plane | the focal intensity at each plane, the xz and yz cuts and the 3D isosurface |
| Traps | per-trap intensity by plane, vortices marked |

## Notes

The bands are provisional. At this case's optics the pupil-defined numerical aperture is n_pix p / (2 f) = 0.533, so the depth of field by the estimate of the M19 module, 2 lambda / NA squared, is about 7.5 um (derived here from the record, not measured): planes 10 um apart are barely separable by any hologram, which is the stress of the case. The twelve vortices are the slots 0, 3, 6 and 9 of each plane.
