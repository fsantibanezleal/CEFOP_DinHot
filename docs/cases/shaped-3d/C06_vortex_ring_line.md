# Case C06_vortex_ring_line, Vortex ring plus a line of traps

- **Category:** Shaped and 3D
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Can extended structures (a ring of vortices) and point-like ones (a line of plain traps) be balanced in one hologram?

## Why this case exists

A mixed target with no published band. It tests whether the weighted methods equalise the mode power of charged traps next to plain traps, which the point-trap model with a vortex term does by construction.

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
| Target | 25 traps; x from -24 to 24 um, y from -25 to 30 um, one plane (z = 0); 16 vortex traps (charges [1]) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M07 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M09](../../frameworks/M09_direct-search.md), Direct search
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M15](../../frameworks/M15_vortex-traps.md), Laguerre-Gaussian vortex traps

## Expected results

A ring of sixteen charge-1 vortex traps (radius 10 um, centred 20 um from the axis) and a line of nine plain traps with equal power (spacing 6 um, 25 um below the axis). No published band exists in the sources read; the band is computed: efficiency 0.3 to 1, relative standard deviation up to 30 percent.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01, M07 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `M01.efficiency` | 0.5343 to 0.653 | 0.593632, 0.593632, 0.593632 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 24.52 to 29.97 | 27.2487, 27.2487, 27.2487 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.4964 to 0.6068 | 0.5516, 0.5516, 0.5516 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6234 to 0.762 | 0.69519, 0.692209, 0.690758 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 5.624 to 13.41 | 12.0826, 8.288, 8.18747 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.7495 to 0.916 | 0.801369, 0.853527, 0.843411 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.6362 to 0.7776 | 0.710088, 0.707843, 0.702871 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 6.265 to 10.19 | 7.33149, 8.05321, 9.29198 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.7736 to 0.9455 | 0.856235, 0.86115, 0.861292 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.6341 to 0.7751 | 0.708163, 0.705873, 0.699782 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.04065 to 0.2122 | 0.168413, 0.128204, 0.0826456 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8978 to 1 | 0.996815, 0.997342, 0.998394 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.6305 to 0.7707 | 0.704284, 0.701511, 0.696003 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 2.5e-12 | 4.35071e-14, 1.16024e-12, 1.60669e-12 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.9 to 1 | 1, 1, 1 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M09.efficiency` | 0.5779 to 0.7063 | 0.640127, 0.643566, 0.642508 | fraction of the input power in the trap peaks |
| `M09.rel_std_pct` | 0.002127 to 0.002741 | 0.00262162, 0.00231416, 0.00236633 | relative standard deviation of the trap intensities, in percent |
| `M09.uniformity` | 0.9 to 1 | 0.999947, 0.999948, 0.999954 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.1388 to 0.1852 | 0.1672, 0.147808, 0.171028 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 30.05 to 60.24 | 48.509, 51.0079, 35.9138 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0 to 0.196 | 0.0300585, 0.0112414, 0.145098 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M15.efficiency` | 0.6341 to 0.7751 | 0.708163, 0.705873, 0.699782 | fraction of the input power in the trap peaks |
| `M15.rel_std_pct` | 0.04065 to 0.2122 | 0.168413, 0.128204, 0.0826456 | relative standard deviation of the trap intensities, in percent |
| `M15.uniformity` | 0.8978 to 1 | 0.996815, 0.997342, 0.998394 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

## Validation anchor

Polin et al. 2005 show independent control of brightness and topology; no published band for this mix (computed only), https://doi.org/10.1364/OPEX.13.005831

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Focal plane | the focal intensity showing the dark centres of the ring traps |
| Traps | per-trap intensity for the ring and for the line |

## Notes

The bands are provisional. The ring traps are 3.9 um apart along the ring, a few focal bins; the dark centres of the charge-1 traps must stay resolved.
