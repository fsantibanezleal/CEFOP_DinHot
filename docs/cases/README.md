# Cases and the coverage matrix

Fourteen cases in four categories. A case is a params record (catalog row params-record): an optical setup, a device, a target (a list of traps or a shaped potential), an aberration,
the method set, a seed, and for the dynamic cases the particle and the rearrangement. The records live in `data-pipeline/pipeline/cases/library.py` and are written to
`data/examples/cases.json`. Each case declares numeric expected ranges for its metrics (`data-pipeline/pipeline/core/expect.py` fails the bake outside them), a bilingual band, a
real or synthetic flag and a published anchor. The App shows ONE selected case; the Experiments and Benchmark pages show cross-case summaries by category and never mix them into the App.

All fourteen cases are synthetic: the parameters are stated and no measured sample is used. Two optical setups carry most of them, and two cases have their own:

| Setup | Wavelength | Focal length | NA | SLM | Focal bin | Half field |
|---|---|---|---|---|---|---|
| Atom (C01 to C04, C09 to C13) | 850 nm | 6 mm | 0.5 in air | 256 by 256 at 20 um, padding 2 | 0.498 um | 127.50 um |
| Bead (C05 to C07) | 1064 nm | 2.4 mm | 1.2 in water (1.33) | 256 by 256 at 10 um, padding 2 | 0.499 um | 127.68 um |
| C08 | 850 nm | 3 mm | 0.5 in air | 128 by 128 at 20 um, padding 2 | 0.498 um | 63.75 um |
| C14 (the geometry of the released cgh-net) | 850 nm | 2.56 mm | 0.5 in air | 128 by 128 at 20 um, padding 1 | 0.850 um | 54.40 um |

## The coverage matrix

| Id | Category | Target | Axis it covers | Reference | Band basis | Anchor |
|---|---|---|---|---|---|---|
| [C01_square_grid](arrays/C01_square_grid.md) | Arrays | 3 by 3 traps, 4 um | smallest array, bead in a trap, spectral oracle | M06 | provisional | Nogrette 2014 |
| [C02_grid_feedback](arrays/C02_grid_feedback.md) | Arrays | 10 by 10 traps, 4 um | camera feedback (19 percent to about 1.4 percent) | M07 | anchor | Nogrette 2014 |
| [C03_large_array](arrays/C03_large_array.md) | Arrays | 32 by 32 = 1024 traps, 5 um | scale, atom in a trap, feedback in 3 steps | M07 | provisional | Kim 2019 |
| [C12_calibration](arrays/C12_calibration.md) | Arrays | 10 by 10 traps at 8 Fourier units | calibration: the published baseline rows | M06 | anchor | Di Leonardo 2007 |
| [C13_disordered_array](arrays/C13_disordered_array.md) | Arrays | 819 traps at random on integer FFT bins, at least 5 bins (2.49 um) apart | disorder: unequal neighbour distances at scale, feedback in 5 steps | M07 | provisional | Kim 2019 (1.2 percent after 5 steps, context) |
| [C04_disc_crosstalk](shaped-3d/C04_disc_crosstalk.md) | Shaped and 3D | disc of 15 um radius | shaped potential, crosstalk on and off | M13 | provisional | Schroff 2023 |
| [C05_multiplane_vortices](shaped-3d/C05_multiplane_vortices.md) | Shaped and 3D | 51 traps on 3 planes, 12 vortices of charge 8 | 3D and orbital angular momentum | M09 | provisional | Polin 2005 |
| [C06_vortex_ring_line](shaped-3d/C06_vortex_ring_line.md) | Shaped and 3D | ring of 16 vortices and a line of 9 traps | mixed extended and point-like structure | M07 | provisional | Polin 2005 (no band) |
| [C14_volume_learned](shaped-3d/C14_volume_learned.md) | Shaped and 3D | 48 voxels on 3 planes at -8, 0, +8 Rayleigh ranges (a lattice, a ring, a shifted lattice) | the learned model answers: a 128 by 128 SLM with padding 1, the cgh-net card's planes | M17 | provisional | Eybposh 2020 (context) |
| [C07_high_na](device-optics/C07_high_na.md) | Device and optics | 5 by 5 traps, 3 um | scalar model past its validity (NA 1.2) | M07 | provisional | Leutenegger 2006 (no band) |
| [C08_device_limited](device-optics/C08_device_limited.md) | Device and optics | 8 by 8 traps, 5 um | 4-bit phase, crosstalk, fill factor 0.85, flicker | B1 | provisional | Schroff 2023 (parameters) |
| [C09_aberrated](device-optics/C09_aberrated.md) | Device and optics | 4 by 4 traps, 5 um | Zernike aberration with and without correction | M14 | provisional | Nogrette 2014 |
| [C10_rearrangement](dynamics-controls/C10_rearrangement.md) | Dynamics and controls | 10 by 10 sites, 36-site target | assignment and moving traps | M16 | provisional | Barredo 2016, Lee 2017 |
| [C11_outside_field](dynamics-controls/C11_outside_field.md) | Dynamics and controls | one trap at 200 um | negative control: refused, never computed | M06 (declared, not run) | provisional | derived pixel relation |

"Band basis" says what sets the expected ranges: **anchor** means a published result sets them with the margin of the seed spread; **provisional** means they were set from the physical limits of the
case and are replaced by measured bands with their margin at the first bake of the real methods (`EXPECT_BASIS` in the library). The provisional bands of the cases baked so far were replaced by measured ones (three seeds, `data-pipeline/pipeline/cases/measured_ranges.json`), C13 and C14 included.

## Categories and what they stand for

| Category | Cases | What a reader learns |
|---|---|---|
| Arrays | C01, C02, C03, C12, C13 | how well the methods equalise many point traps, from nine to a thousand, in a lattice and in a disordered set, and how a camera loop and a particle test the result |
| Shaped and 3D | C04, C05, C06, C14 | extended potentials, traps at several depths, optical vortices, what the device costs a shaped field, and a volume at the geometry the released network answers for |
| Device and optics | C07, C08, C09 | where the model stops (high NA), what a real SLM costs, what aberrations cost and what correction recovers |
| Dynamics and controls | C10, C11 | moving traps without dimming, and the refusal of a task the optics cannot do |

Controls: C12 is the calibration against a published table; C11 is the negative control (a trap outside the field is refused with the bound, no manifest, no trace). A case set without
explicit controls is incomplete.

## Variants

On every case the reader picks the method among the ladder rows valid for the case and the device (ideal or the case's own). A method is computed live where its lane is live and replayed from the bake
where it is baked ([the live lane](../architecture/04_live-lane.md)). The trap editor (add, drag, delete) changes the case's target live; it is a control of the case, never a separate surface.

## Case card format

Each card has: the header (category, source, the question), Why this case exists, Formalization (the parameter table and the method list), Expected results (the prose and the table of ranges), Validation anchor,
What each App group shows, and Notes. The cards are generated from the case library for the parameter tables, so a table cannot disagree with the code.

## Gaps declared

- The disordered 819-trap set of Kim et al. is C13; its coordinates are not published, so the set is DinHot's own seeded draw with the same count and the same kind of constraint (integer bins, a minimum spacing).
- C07 is a scalar case with a validity flag; no vectorial lane exists in this build.
- The canonical bake holds thirteen baked cases and C11, refused by contract 1. M17 answers with the released graph on C14 (the only case at the network's geometry: 128 by 128 pixels, padding 1); B3 runs with its random-start baseline, since no warm-start model is released (its record says baseline). Every card states the ranges the bake checks, measured on three seeds and written by `scripts/write_case_ranges.py`.
