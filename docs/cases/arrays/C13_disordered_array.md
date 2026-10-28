# Case C13_disordered_array, Disordered array, 819 traps

- **Category:** Arrays
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** Does the feedback-corrected uniformity of a lattice hold when the same number of traps sits at random positions with unequal neighbour distances, and which methods keep it?

## Why this case exists

The disordered 819-trap array is the geometry Kim et al. 2019 used to show that adaptive feedback equalises a pattern with no symmetry. The SDD names it next to the 32 by 32 lattice of
[C03](C03_large_array.md); a params record holds one target, so it is a case of its own. A lattice has equal neighbour distances; here the distances are unequal, so the light that
leaks between traps differs trap by trap and a method cannot rely on a regular pattern. The case also feeds the odd seeds of benchmark group G6.

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
| Target | 819 traps on integer FFT bins, |x| and |y| at most 100 bins (49.8 um), at least 5 bins (2.49 um) apart, one plane (z = 0); random sequential addition, seed 20261847 (`disordered_set`, `DISORDERED_819`) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M07 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |
| Camera feedback | gain 0.9, 5 steps, camera gain error 0.22 rms |
| Particle | none (this case declares no dynamics block) |

The coordinates of Kim et al. are not published: the set is DinHot's own draw with the same count and the same constraint, so the case is set against that paper's result as context, not as a reproduction.

### Methods

The same set as [C03](C03_large_array.md), because every trap is on a bin and the FFT form applies:

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M07](../../frameworks/M07_phase-fixed-wgs.md), Phase-fixed weighted GS
- [M12](../../frameworks/M12_closed-loop-wgs.md), Closed-loop WGS on an emulated camera
- [B3](../../frameworks/B3_learned-warm-start.md), Learned warm start for phase-fixed WGS (flagged missing in the manifest: the learned model is not registered in this build)

## Expected results

Eight hundred and nineteen equal traps. Phase-fixed weighted GS leaves a relative spread of 0.1 to 0.3 percent in the ideal model, and five adaptive camera steps bring the 22 percent measured
spread (camera gain error 0.22 rms) to about 0.5 percent. Kim et al. 2019 report 1.2 +- 0.11 percent after five steps on 819 disordered foci; the value here is lower, and the two are not
comparable: this build's camera emulator has no read noise, the beam is Gaussian and the traps are DinHot's own draw. The comparison is context.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next two), range = mean plus or minus the wider of 10 percent of the mean and the seed spread, clipped to the domain
(`data-pipeline/pipeline/ranges.py`, values in `data-pipeline/pipeline/cases/measured_ranges.json`). Every method range is keyed `<method>.<metric>`, so it is never applied to another
method. The case's library basis stays `provisional` because no published band sets these numbers. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `M01.efficiency` | 0.5364 to 0.6556 | 0.596, 0.596, 0.596 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 22.31 to 27.26 | 24.78, 24.78, 24.78 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.3209 to 0.3923 | 0.3566, 0.3566, 0.3566 | 1 minus the relative spread, 0 to 1 |
| `M02.efficiency` | 0.6225 to 0.7608 | 0.6894, 0.6919, 0.6936 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 12.44 to 15.2 | 13.48, 14.01, 13.96 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.531 to 0.649 | 0.5844, 0.5725, 0.6131 | 1 minus the relative spread, 0 to 1 |
| `M04.efficiency` | 0.6679 to 0.8163 | 0.7404, 0.7424, 0.7435 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 9.87 to 12.06 | 11.17, 11.11, 10.62 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.5802 to 0.7091 | 0.6425, 0.6399, 0.6515 | 1 minus the relative spread, 0 to 1 |
| `M06.efficiency` | 0.6641 to 0.8117 | 0.736, 0.7379, 0.7397 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.5962 to 0.7287 | 0.695, 0.656, 0.6363 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8823 to 1 | 0.9772, 0.9814, 0.9824 | 1 minus the relative spread, 0 to 1 |
| `M07.efficiency` | 0.6523 to 0.7973 | 0.7229, 0.7249, 0.7265 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0 to 0.4033 | 0.1031, 0.3096, 0.1778 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8954 to 1 | 0.9977, 0.9913, 0.9958 | 1 minus the relative spread, 0 to 1 |
| `M12.efficiency` | 0.6691 to 0.8178 | 0.7431, 0.7444, 0.7428 | fraction of the input power in the trap peaks |
| `M12.rel_std_pct` | 17.47 to 21.35 | 20.19, 19.44, 18.6 | relative standard deviation of the trap intensities, in percent |
| `M12.uniformity` | 0.3449 to 0.5596 | 0.3834, 0.4907, 0.4827 | 1 minus the relative spread, 0 to 1 |
| `feedback_final_rel_std_pct` | 0.4279 to 0.5635 | 0.5222, 0.5104, 0.4544 | measured spread after the 5 camera steps, in percent |
| `feedback_initial_rel_std_pct` | 19.95 to 24.39 | 21.98, 22.01, 22.52 | measured spread before the camera loop, in percent |

## Validation anchor

Kim et al. 2019, Opt. Lett. 44, 3178 (819 disordered foci, non-uniformity 1.2 +- 0.11 percent after five adaptive steps; a flat beam and a 768-pixel device, not this build's), https://doi.org/10.1364/OL.44.003178

Context, not a band: the case declares no range around 1.2 percent, because this build's camera emulator and beam differ from the source's. If the engine's output contradicts the source
beyond that difference, that is a defect to report, not to hide.

## What each App group shows for this case

| Group | What it shows |
|---|---|
| Convergence | metrics against iteration and the camera loop (5 steps at gain 0.9) |

## Notes

Lane: precompute (the run exceeds the 1500 ms live budget; the trace is under the 256 KiB budget). The trap set is the same draw as the odd seeds of benchmark G6
(`DISORDERED_819`), so the case and the benchmark describe one geometry.
