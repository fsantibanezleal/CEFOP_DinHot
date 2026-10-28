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

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.05 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 40 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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
