# Case C10_rearrangement, Rearrangement sequence, 100 sites

- **Category:** Dynamics and controls
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Can the atoms of a randomly loaded array be moved into a defect-free pattern without crossings, and does every moving trap stay lit?

## Why this case exists

Dynamics and control: the sorting step of a neutral-atom machine. It is the case for the Hungarian assignment (M16, linear phase interpolation) and the flicker-bounded sequence (B2).

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
| Target | 100 traps; x from -18 to 18 um, y from -18 to 18 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M16 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Rearrangement | loading probability 0.55, alpha 1.5, 10 steps per move, 36 central target sites (6 by 6) |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M16](../../frameworks/M16_rearrangement.md), Hungarian assignment and linear phase interpolation
- [B2](../../frameworks/B2_flicker-bounded-sequence.md), Flicker-bounded sequence

## Expected results

A 10 by 10 site array loaded at 55 percent (52 sites are loaded at the case seed, by the portable generator); Hungarian assignment with cost d to the 1.5 moves the surplus atoms into the central 6 by 6 target without crossings, and the hologram of every intermediate frame keeps the moving trap lit. Bands: final filling 0.9 to 1, lowest transient 0.1 to 1.5, efficiency 0.3 to 1.

### Expected ranges (checked by the bake)

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.3 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `min_transient` | 0.1 to 1.5 | lowest intensity of a moving trap relative to its mean |
| `final_filling` | 0.9 to 1 | filling of the target pattern after the last move, 0 to 1 |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

## Validation anchor

Barredo et al. 2016, Science 354, 1021; Endres et al. 2016; Ebadi et al. 2021; Lee, Kim and Ahn 2017 (Hungarian assignment); linear phase interpolation, arXiv 2501.01391, https://arxiv.org/abs/1704.07074

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Dynamics | the rearrangement frames, the assignment paths and the filling |
| Convergence | the lowest transient intensity of the moving traps against step |

## Notes

The bands are provisional. 52 atoms cover the 36 target sites. The transient band is wide: the unit tests of the methods measured 0.87 (median) for the linear phase interpolation and 0.92 for the flicker-bounded sequence, and the bake replaces this band with a measured one.
