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

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.4 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 15 | relative standard deviation of the trap intensities, in percent |
| `feedback_initial_rel_std_pct` | 10 to 35 | measured spread before the camera loop, in percent |
| `feedback_final_rel_std_pct` | 0 to 4 | measured spread after the camera loop, in percent |
| `fc_ratio` | 0.8 to 1.2 | fitted corner frequency over the expected one (bead), or fitted over expected trap frequency (atom) |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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

The SDD names the 32 by 32 lattice and the disordered 819-trap set of Kim et al.; the case library implements the 32 by 32 lattice only (the disordered set is in neither the case nor the benchmark protocol, whose schema holds one target per geometry). The atom trace of the producer's development run oscillated at 102.4 kHz against 105.1 kHz expected for a depth of 892 uK (planted test methods, not the canonical bake).
