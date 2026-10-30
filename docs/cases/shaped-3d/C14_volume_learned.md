# Case C14_volume_learned, Three-plane volume at the learned model's geometry

- **Category:** Shaped and 3D
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** On a volume of point voxels at the geometry the released cgh-net was trained for, does the network's phase compete with the volumetric GS, and what does the hybrid add?

## Why this case exists

The released multi-plane network ([M17](../../frameworks/M17_unsupervised-cnn-hologram.md), slot `cgh-net`) takes three focal planes on a 128 by 128 crop and answers for a 128 by 128 SLM with padding 1. None of the
thirteen earlier cases has that geometry (they are 256 by 256 pixels with padding 2, and C08 is 128 by 128 with padding 2), so the network never answered on a case, in the bake or in the workbench. C14 is the case
that fits the card `models/cgh-net.json`: the same SLM size and padding, the planes at -8, 0 and +8 SLM-limited Rayleigh ranges, point voxels on integer bins with equal counts per plane (the form the network and
[M19](../../frameworks/M19_volumetric-3d-gs.md) take). The reference method is M17, so the replay shows the network's maps.

## Formalization

The record below is the case's params record (catalog row params-record). It is written by the `cases` command of `data-pipeline/run.py` from `data-pipeline/pipeline/cases/library.py`
into `data/examples/cases.json`; contract 1 reads it back and refuses it with a reason if it breaks the schema or a range
([the data contracts](../../architecture/08_data-contracts.md)).

| Parameter | Value |
|---|---|
| Wavelength | 850 nm |
| Focal length | 2.56 mm (the pupil, 128 pixels of 20 um, equals 2 f NA, as for the other setups) |
| Numerical aperture, immersion index | 0.5, 1 |
| SLM | 128 by 128 pixels, pitch 20 um, padding 1 (FFT grid 128 by 128) |
| Input beam | gaussian, waist fraction 1.0 |
| Focal bin, Fourier unit, half field | 0.850 um, 0.850 um, 54.40 um |
| SLM-limited Rayleigh range | 1.082 um (`lambda f^2 / (pi R^2)`, `R = n_pix p / 2`; `learned/convert.rayleigh_range_m`) |
| Target | 48 point voxels, 16 on each of the planes z = -8, 0, +8 Rayleigh ranges (-8.658, 0, 8.658 um); plane -1 a 4 by 4 lattice at 12 bins shifted by (-6, +6) bins, plane 0 a ring of 16 voxels at 24 bins, plane +1 the lattice shifted by (+6, -6) bins; every voxel on an integer bin within 24 bins of the axis, equal weights (`volume_three_planes`, `CGH_NET_SETUP`) |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M17 (the one whose maps the replay shows) |
| Device | ideal (this case declares no device) |

The geometry is read from the card by a test (`tests/bake/test_c14.py`): the card's input shape is `[1, 3, 128, 128]`, the case's SLM and padding are the card's, the planes sit at the card's depths, the
counts per plane are equal, every voxel is on an integer bin within 60 bins, and the network input is built from the case without error.

### Methods

- [M01](../../frameworks/M01_superposition.md), Superposition of prisms and lenses
- [M02](../../frameworks/M02_random-superposition.md), Random superposition
- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M06](../../frameworks/M06_gsw.md), Weighted GS
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [M19](../../frameworks/M19_volumetric-3d-gs.md), Volumetric 3D GS
- [M17](../../frameworks/M17_unsupervised-cnn-hologram.md), Multi-plane CNN hologram (the hybrid: the network's phase, refined by M19 for what is left of the budget when that raises the volume accuracy of the network's mask)

The method set is the volumetric part of the three-dimensional set of C05 (no vortex rule, since the case has no vortex, and no direct search, which is slow on 48 voxels). M13 and M18 take fields, and B5 is a front over a different cost.

## Expected results

Measured, not published. The released network ran on this case (the bake used the real graph through onnxruntime: the manifest says `cgh-net: real`, and a direct run reports provenance `real`); its refinement by M19 did not raise the
volume accuracy of the network's mask, so the hybrid returned the network's phase alone (`refine_kept` false). On the trap metrics of this record the network trails the volumetric GS: M17 puts 0.396 of the power in the
voxels with a relative spread of 36.4 percent, M19 0.752 with 15.3 percent and M06 0.785 with 0.32 percent (the case seed; the three seeds are in the table below). The network was trained on the plane images
(the loss is 1 minus the plane accuracy), not on the voxel intensities, so these are numbers its training did not optimise; the metric it did optimise is in `data/derived/models/metrics.json`.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M01, M17 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `M01.efficiency` | 0.4497 to 0.5497 | 0.49969, 0.49969, 0.49969 | fraction of the input power in the trap peaks |
| `M01.rel_std_pct` | 61.99 to 75.77 | 68.8828, 68.8828, 68.8828 | relative standard deviation of the trap intensities, in percent |
| `M01.uniformity` | 0.1765 to 0.2157 | 0.196123, 0.196123, 0.196123 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M02.efficiency` | 0.6255 to 0.7645 | 0.699423, 0.698246, 0.687363 | fraction of the input power in the trap peaks |
| `M02.rel_std_pct` | 21.69 to 29.81 | 27.748, 23.6871, 25.8101 | relative standard deviation of the trap intensities, in percent |
| `M02.uniformity` | 0.3429 to 0.5711 | 0.407475, 0.52154, 0.441986 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M04.efficiency` | 0.7177 to 0.8771 | 0.795099, 0.799208, 0.797861 | fraction of the input power in the trap peaks |
| `M04.rel_std_pct` | 13.76 to 20.06 | 15.2559, 17.0559, 18.4063 | relative standard deviation of the trap intensities, in percent |
| `M04.uniformity` | 0.5628 to 0.749 | 0.701345, 0.658146, 0.608205 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M06.efficiency` | 0.7068 to 0.8638 | 0.785107, 0.786051, 0.784787 | fraction of the input power in the trap peaks |
| `M06.rel_std_pct` | 0.2123 to 0.7594 | 0.315173, 0.588728, 0.553653 | relative standard deviation of the trap intensities, in percent |
| `M06.uniformity` | 0.8893 to 1 | 0.992467, 0.984935, 0.986909 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M10.efficiency` | 0.2685 to 0.3582 | 0.341177, 0.296337, 0.302437 | fraction of the input power in the trap peaks |
| `M10.rel_std_pct` | 24 to 36.02 | 26.0924, 32.1051, 31.829 | relative standard deviation of the trap intensities, in percent |
| `M10.uniformity` | 0 to 0.5526 | 0.339586, 0.368688, 0.07834 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M11.efficiency` | 0.6793 to 0.8302 | 0.755456, 0.753814, 0.754949 | fraction of the input power in the trap peaks |
| `M11.rel_std_pct` | 1.814 to 2.217 | 2.04891, 1.94607, 2.05107 | relative standard deviation of the trap intensities, in percent |
| `M11.uniformity` | 0.8602 to 1 | 0.959287, 0.956475, 0.951481 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M17.efficiency` | 0.3565 to 0.4357 | 0.396124, 0.396124, 0.396124 | fraction of the input power in the trap peaks |
| `M17.rel_std_pct` | 32.76 to 40.04 | 36.3997, 36.3997, 36.3997 | relative standard deviation of the trap intensities, in percent |
| `M17.uniformity` | 0.3372 to 0.4121 | 0.374653, 0.374653, 0.374653 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |
| `M19.efficiency` | 0.6745 to 0.8244 | 0.751541, 0.749043, 0.747809 | fraction of the input power in the trap peaks |
| `M19.rel_std_pct` | 12.91 to 18.73 | 15.2506, 17.5581, 14.65 | relative standard deviation of the trap intensities, in percent |
| `M19.uniformity` | 0.6242 to 0.7629 | 0.71348, 0.673568, 0.693457 | 1 minus (max minus min) over (max plus min) of the weighted trap intensities, 1 is perfect |

## Validation anchor

Eybposh et al. 2020, Opt. Express 28, 26636 (DeepCGH: a U-Net hologram for volumes, trained unsupervised on the plane images), https://doi.org/10.1364/OE.399624

Context, not a band: the paper's volumes, SLM and accuracy measure differ from this build's, so the case declares no range around a published number. If the engine's output contradicts the source beyond that
difference, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Hologram | the phase mask of the reference method, here the network's |
| Focal plane | the focal intensity at each plane, the xz and yz cuts and the 3D isosurface |
| Traps | per-voxel intensity by plane |

## Notes

Lane: precompute (the hybrid's refinement runs the volumetric GS and exceeds the 1500 ms live budget, so M17 is baked on this case; the network pass alone takes about 20 ms). The bake of this case must run where
onnxruntime is installed (`data-pipeline/requirements.txt` pins it): with the model released and onnxruntime absent, M17 refuses to run
(`methods/learned/_slot.py`) instead of answering with the M19 baseline under its own id. The trace is under the 256 KiB budget.
