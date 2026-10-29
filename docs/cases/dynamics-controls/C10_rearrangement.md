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

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B2.efficiency` | 0.7141 to 0.8728 | 0.79825, 0.790868, 0.791195 | fraction of the input power in the trap peaks |
| `B2.rel_std_pct` | 0 to 0.08159 | 8.15731e-14, 0.0611935, 3.85724e-13 | relative standard deviation of the trap intensities, in percent |
| `B2.uniformity` | 0.8997 to 1 | 1, 0.999112, 1 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7225 to 0.8831 | 0.805592, 0.801876, 0.800878 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.8111 to 1.149 | 0.923721, 1.09287, 0.924172 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8783 to 1 | 0.977946, 0.973097, 0.976615 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.7129 to 0.8713 | 0.797153, 0.78952, 0.789723 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 0.05331 | 0.0116927, 0.0427627, 0.0122543 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8995 to 1 | 0.999648, 0.999269, 0.999513 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M16.efficiency` | 0.7415 to 0.9062 | 0.823226, 0.825055, 0.8233 | fraction of the input power in the trap peaks |
| `final_filling` | 0.9 to 1.1 | 1, 1, 1 | fraction of the target sites filled after the rearrangement |
| `min_transient` | 0.8849 to 1.081 | 0.989672, 0.980201, 0.979635 | lowest intensity of a moving trap over the sequence, over the mean trap intensity |

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
