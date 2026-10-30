# Case C03_large_array, Large array, 32 x 32 = 1024 traps

- **Category:** Arrays
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Does the large-array state of the art, phase-fixed WGS plus a few camera steps, hold at a thousand traps, and what does an atom in one trap feel?

## Why this case exists

Scale: 1024 traps at 5 um is the regime of the neutral-atom arrays that motivate the product. It is the case where the live budget is tested hardest and where the cheap methods show their limits.

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
| Target | 1024 traps; x from -77.5 to 77.5 um, y from -77.5 to 77.5 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M07 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Camera feedback | gain 0.9, 3 steps, camera gain error 0.22 rms |
| Particle | particle = atom, trap_id = 528, power_mw = 3000.0, mass_amu = 87.0, detuning_thz = -31.5, temperature_k = 5e-05, n_steps = 50000, dt_s = 1e-07 |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M12](../../frameworks/M12_closed-loop-wgs.md), Closed-loop WGS on an emulated camera
- [B3](../../frameworks/B3_learned-warm-start.md), Learned warm start for phase-fixed WGS

## Expected results

A thousand and twenty-four equal traps. Phase-fixed weighted GS plus three adaptive camera steps bring a 22 percent measured spread to the percent level (the bake fails above 4 percent). A rubidium atom (87 amu) in trap 528 oscillates at the radial frequency the computed intensity curvature predicts (the fitted-over-expected ratio is held between 0.8 and 1.2).

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B3.efficiency` | 0.7147 to 0.8736 | 0.794122, 0.79376, 0.794539 | fraction of the input power in the trap peaks |
| `B3.rel_std_pct` | 0 to 0.8925 | 0.199007, 0.669813, 0.396127 | relative standard deviation of the trap intensities, in percent |
| `B3.uniformity` | 0.8895 to 1 | 0.994788, 0.982785, 0.987564 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.1694 to 0.207 | 0.18822, 0.18822, 0.18822 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 832.5 to 1018 | 925.014, 925.014, 925.014 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 9.464e-08 to 1.157e-07 | 1.05155e-07, 1.05155e-07, 1.05155e-07 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6684 to 0.817 | 0.74231, 0.743693, 0.742106 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 34.76 to 42.49 | 39.1338, 39.1088, 37.6284 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.01722 to 0.1625 | 0.0789683, 0.058961, 0.13158 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.7359 to 0.8995 | 0.816674, 0.817046, 0.819415 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 16.03 to 19.59 | 18.6828, 17.6689, 17.0756 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.4268 to 0.5568 | 0.454922, 0.500563, 0.519907 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7247 to 0.8858 | 0.806281, 0.804689, 0.804761 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.8581 to 1.434 | 1.27682, 1.17164, 0.989044 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8647 to 1 | 0.958116, 0.960653, 0.963624 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.7147 to 0.8736 | 0.794122, 0.793758, 0.79454 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 0.8831 | 0.198701, 0.662816, 0.395529 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8896 to 1 | 0.994818, 0.982945, 0.987554 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M12.efficiency` | 0.7285 to 0.8903 | 0.809228, 0.810427, 0.808553 | fraction of the input power in the trap peaks |
| `M12.rel_std_pct` | 17.8 to 21.76 | 20.307, 19.8325, 19.198 | relative standard deviation of the trap intensities, in percent |
| `M12.uniformity` | 0.3422 to 0.539 | 0.376503, 0.474908, 0.470433 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `fc_ratio` | 0.8746 to 1.069 | 0.982652, 0.96439, 0.968395 | fitted corner frequency over the expected one (bead), or fitted over expected trap frequency (atom) |
| `feedback_final_rel_std_pct` | 0.9545 to 2.037 | 1.4434, 1.7924, 1.2512 | measured spread after the camera loop, in percent |
| `feedback_initial_rel_std_pct` | 20.08 to 24.54 | 22.3086, 22.2245, 22.4033 | measured spread before the camera loop, in percent |

## Validation anchor

Kim et al. 2019, Opt. Lett. 44, 3178 (22 percent to 1.4 percent in three steps); Ebadi et al. 2021 for the array size, https://doi.org/10.1364/OL.44.003178

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Convergence | metrics against iteration and the camera loop (3 steps at gain 0.9) |
| Dynamics | the atom trace, its spectrum and the radial frequency read from the potential |

## Notes

The SDD names the 32 by 32 lattice and the disordered 819-trap set of Kim et al.; the lattice is this case, and the disordered set is its own case, [C13_disordered_array](C13_disordered_array.md) (a params record holds one target), and the odd seeds of benchmark G6. The atom trace of the producer's development run oscillated at 102.4 kHz against 105.1 kHz expected for a depth of 892 uK (planted test methods, not the canonical bake).
