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

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.3 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 30 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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
