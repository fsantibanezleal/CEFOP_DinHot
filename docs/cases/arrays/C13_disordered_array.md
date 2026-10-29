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

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `B3.efficiency` | 0.6524 to 0.7973 | 0.722975, 0.724918, 0.726627 | fraction of the input power in the trap peaks |
| `B3.rel_std_pct` | 0.1349 to 0.3824 | 0.30232, 0.178562, 0.295053 | relative standard deviation of the trap intensities, in percent |
| `B3.uniformity` | 0.8941 to 1 | 0.992314, 0.99575, 0.992367 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M01.efficiency` | 0.5364 to 0.6556 | 0.595988, 0.595988, 0.595988 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 22.31 to 27.26 | 24.7845, 24.7845, 24.7845 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.3209 to 0.3923 | 0.35661, 0.35661, 0.35661 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6225 to 0.7608 | 0.689413, 0.69193, 0.693555 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 12.44 to 15.2 | 13.4839, 14.0124, 13.9613 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.531 to 0.649 | 0.58437, 0.572461, 0.613135 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.6679 to 0.8163 | 0.7404, 0.742444, 0.743498 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 9.87 to 12.06 | 11.1677, 11.1136, 10.6177 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.5802 to 0.7091 | 0.642473, 0.639939, 0.651522 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.664 to 0.8116 | 0.735956, 0.737755, 0.739711 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.5151 to 0.8065 | 0.739155, 0.649765, 0.593482 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.88 to 1 | 0.973611, 0.977699, 0.982035 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M07.efficiency` | 0.6524 to 0.7973 | 0.722975, 0.724918, 0.726627 | fraction of the input power in the trap peaks |
| `M07.rel_std_pct` | 0.1366 to 0.3794 | 0.300401, 0.178985, 0.294567 | relative standard deviation of the trap intensities, in percent |
| `M07.uniformity` | 0.8941 to 1 | 0.992333, 0.995731, 0.992403 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M12.efficiency` | 0.6693 to 0.818 | 0.742994, 0.744222, 0.743637 | fraction of the input power in the trap peaks |
| `M12.rel_std_pct` | 17.46 to 21.33 | 20.1589, 19.4514, 18.5754 | relative standard deviation of the trap intensities, in percent |
| `M12.uniformity` | 0.3433 to 0.5641 | 0.381499, 0.491899, 0.487811 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `feedback_final_rel_std_pct` | 0.35 to 0.5742 | 0.4433, 0.5275, 0.4154 | measured spread after the camera loop, in percent |
| `feedback_initial_rel_std_pct` | 19.97 to 24.4 | 21.9947, 22.0293, 22.5333 | measured spread before the camera loop, in percent |

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
