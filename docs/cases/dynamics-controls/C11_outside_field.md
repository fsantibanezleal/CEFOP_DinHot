# Case C11_outside_field, A trap outside the field of view (refused)

- **Category:** Dynamics and controls
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** What does the product do with a trap it cannot make?

## Why this case exists

The refusal case. A trap beyond the unaliased field of view lies in the replica of the grid, so any hologram that places light there also places it inside the field. The product refuses the case at the door, names the bound, and never computes it. A deck without an explicit control is incomplete.

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
| Target | 1 traps; x from 200 to 200 um, y from 0 to 0 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M06 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS

## Expected results

One trap at 200 um against a half field of 127.5 um. Contract 1 rejects the record with the field's bounds in the reason; the case index lists it as refused, no manifest and no trace exist, and the App shows the reason instead of a result.

### Expected ranges (checked by the bake)

Basis of the bands: **provisional**, declared in the case library. The case is refused by contract 1 and never computed,
so these bands are never checked; they state what a valid record of this kind would be held to.

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0 to 1 | fraction of the input power in the trap peaks |

## Validation anchor

Derived from the pixel relation of Schroff et al. 2023 (replica period lambda f / p); an error state, not a metric, https://doi.org/10.1038/s41598-023-30296-6

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| All groups | none: the case is refused before any computation, and the case selector shows the refusal with the field bound |

## Notes

The expected band is an error state, not a metric. The reference method and the method list are declared so the record is well formed; they are never run.
