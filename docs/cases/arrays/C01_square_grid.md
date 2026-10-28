# Case C01_square_grid, Small square grid, 3 x 3

- **Category:** Arrays
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Can nine equal traps be made, and does a bead in the central trap behave as the computed stiffness says?

## Why this case exists

The smallest array: every method runs in a fraction of a second and the trap-by-trap picture is readable. It is the first case a reader meets, and the one that closes the loop from hologram to particle (the spectral oracle) on a small, exact example.

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
| Target | 9 traps; x from -4 to 4 um, y from -4 to 4 um, one plane (z = 0) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M06 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Camera feedback | gain 0.7, 5 steps, camera gain error 0.1 rms |
| Particle | particle = bead, trap_id = 4, power_mw = 10.0, bead_radius_um = 0.5, n_particle = 1.59, viscosity_pa_s = 0.00089, temperature_k = 295.0, n_steps = 131072, dt_s = 5e-05 |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M03](../../frameworks/M03_random-mask.md), Random mask
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M05](../../frameworks/M05_gaa.md), Generalized adaptive additive GS
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M09](../../frameworks/M09_direct-search.md), Direct search
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [B3](../../frameworks/B3_learned-warm-start.md), Learned warm start for phase-fixed WGS
- [B4](../../frameworks/B4_aberration-robust-hologram.md), Aberration-robust hologram
- [B5](../../frameworks/B5_pareto-front.md), Efficiency-uniformity Pareto front
- [M12](../../frameworks/M12_closed-loop-wgs.md), Closed-loop WGS on an emulated camera

## Expected results

A weighted hologram reaches a relative standard deviation of a few percent with an efficiency above 0.6; one camera step brings the spread under 5 percent. A 0.5 um bead in the central trap fits a Lorentzian whose corner frequency is the trap stiffness over 2 pi gamma (the fitted-over-expected ratio is held between 0.8 and 1.2) and its position histogram follows the Boltzmann law of the computed potential.

### Expected ranges (checked by the bake)

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.6 to 1 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `uniformity` | 0.85 to 1 | uniformity u = 1 minus (max minus min) over (max plus min) of the trap intensities, 1 is perfect |
| `rel_std_pct` | 0 to 8 | relative standard deviation of the trap intensities, in percent |
| `feedback_final_rel_std_pct` | 0 to 5 | measured spread after the camera loop, in percent |
| `fc_ratio` | 0.8 to 1.2 | fitted corner frequency over the expected one (bead), or fitted over expected trap frequency (atom) |
| `boltzmann_tv` | 0 to 0.15 | total variation between the position histogram and the Boltzmann law, 0 is a perfect match |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

## Validation anchor

Nogrette et al. 2014, Phys. Rev. X 4, 021034 (3 x 3 array, occupancy about 0.5 per trap), https://arxiv.org/abs/1402.5329

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Convergence | metrics against iteration for the methods of the case, and the camera feedback curve (5 steps at gain 0.7) |
| Dynamics | the bead trace in trap 4, its power spectrum with the Lorentzian fit, and the Boltzmann check |

## Notes

The bands are provisional, set from the physical limits of the case. The published anchor is a 3 by 3 array with occupancy about 0.5 per trap; the occupancy is not simulated here. The particle driver uses the bead parameters of the record, a power of 10 mW and a time step of 5e-5 s.
