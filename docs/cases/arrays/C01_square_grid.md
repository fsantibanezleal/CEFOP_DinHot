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

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B3.efficiency` | 0.7093 to 0.867 | 0.816826, 0.777438, 0.770161 | fraction of the input power in the trap peaks |
| `B3.rel_std_pct` | 0 to 0.0131 | 3.83909e-06, 0.00982507, 1.34917e-05 | relative standard deviation of the trap intensities, in percent |
| `B3.uniformity` | 0.9 to 1 | 1, 0.999861, 1 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B4.efficiency` | 0.6996 to 0.8551 | 0.805461, 0.768276, 0.758424 | fraction of the input power in the trap peaks |
| `B4.rel_std_pct` | 0.2421 to 0.9291 | 0.421908, 0.569562, 0.76539 | relative standard deviation of the trap intensities, in percent |
| `B4.uniformity` | 0.8923 to 1 | 0.993906, 0.991041, 0.98936 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `B5.efficiency` | 0.7207 to 0.8808 | 0.816826, 0.815305, 0.770161 | fraction of the input power in the trap peaks |
| `B5.rel_std_pct` | 0 to 0.1239 | 1.44669e-11, 0.0929418, 3.97365e-10 | relative standard deviation of the trap intensities, in percent |
| `B5.uniformity` | 0.8996 to 1 | 1, 0.998562, 1 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.4084 to 0.4991 | 0.453725, 0.453725, 0.453725 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 57.46 to 70.23 | 63.847, 63.847, 63.847 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.1471 to 0.1798 | 0.163409, 0.163409, 0.163409 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6502 to 0.7946 | 0.744199, 0.714368, 0.708646 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 12.05 to 57.32 | 25.5131, 48.1454, 30.4024 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.2736 to 0.816 | 0.644418, 0.373233, 0.61682 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M03.efficiency` | 0.08358 to 0.1022 | 0.0930225, 0.0941424, 0.0914339 | fraction of the input power in the trap peaks |
| `M03.rel_std_pct` | 1.893 to 6.873 | 5.71608, 3.22621, 4.20713 | relative standard deviation of the trap intensities, in percent |
| `M03.uniformity` | 0.8352 to 1 | 0.909127, 0.959668, 0.915274 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.7161 to 0.8753 | 0.819262, 0.778693, 0.789197 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 0.8589 to 33.53 | 7.34144, 20.5691, 23.679 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.54 to 0.9557 | 0.879438, 0.6716, 0.692596 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M05.efficiency` | 0.7262 to 0.8875 | 0.818674, 0.817719, 0.784192 | fraction of the input power in the trap peaks |
| `M05.rel_std_pct` | 0 to 21.36 | 5.31835, 3.86006, 16.6202 | relative standard deviation of the trap intensities, in percent |
| `M05.uniformity` | 0.7175 to 1 | 0.91118, 0.931517, 0.77608 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7211 to 0.8814 | 0.816828, 0.816692, 0.770242 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0 to 0.02596 | 0.00233013, 0.00554262, 0.019249 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8999 to 1 | 0.999965, 0.999909, 0.999656 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.7093 to 0.867 | 0.816826, 0.777439, 0.770161 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 0.01291 | 0.000690884, 0.00962696, 0.00023168 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.9 to 1 | 0.999988, 0.999861, 0.999996 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M09.efficiency` | 0.5852 to 0.7153 | 0.685333, 0.631753, 0.633713 | fraction of the input power in the trap peaks |
| `M09.rel_std_pct` | 0.0006662 to 0.0008142 | 0.000742459, 0.000761875, 0.000716327 | relative standard deviation of the trap intensities, in percent |
| `M09.uniformity` | 0.9 to 1 | 0.999989, 0.999987, 0.999986 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.1388 to 0.1932 | 0.152016, 0.179207, 0.166817 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 32.28 to 71.04 | 63.1374, 43.7583, 48.0833 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0.0606 to 0.5005 | 0.175326, 0.395272, 0.271044 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M11.efficiency` | 0.7068 to 0.8639 | 0.786206, 0.785224, 0.784598 | fraction of the input power in the trap peaks |
| `M11.rel_std_pct` | 0 to 2.689 | 1.33637, 1.92972, 0.494067 | relative standard deviation of the trap intensities, in percent |
| `M11.uniformity` | 0.8815 to 1 | 0.976025, 0.970037, 0.992206 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M12.efficiency` | 0.7312 to 0.8937 | 0.81117, 0.811546, 0.81474 | fraction of the input power in the trap peaks |
| `M12.rel_std_pct` | 16.31 to 19.93 | 17.7117, 17.5563, 19.0878 | relative standard deviation of the trap intensities, in percent |
| `M12.uniformity` | 0.657 to 0.803 | 0.7493, 0.751651, 0.688965 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `boltzmann_tv` | 0.03595 to 0.04397 | 0.0382792, 0.0422874, 0.0393148 | total variation between the position histogram and the Boltzmann law, 0 is a perfect match |
| `fc_ratio` | 0.8613 to 1.124 | 0.919889, 1.00676, 1.05126 | fitted corner frequency over the expected one (bead), or fitted over expected trap frequency (atom) |
| `feedback_final_rel_std_pct` | 0 to 1.022 | 0.0236, 0.019, 0.7702 | measured spread after the camera loop, in percent |
| `feedback_initial_rel_std_pct` | 5.911 to 13.57 | 9.1161, 8.1364, 11.9642 | measured spread before the camera loop, in percent |

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
