# Case C04_disc_crosstalk, Disc potential with the crosstalk model

- **Category:** Shaped and 3D
- **Source:** synthetic (the parameters are stated; no measured sample is used)
- **Question:** What does a uniform disc potential cost on a device with pixel crosstalk, and how much of it does a crosstalk-aware method recover?

## Why this case exists

Shaped potentials are the other half of the task (ring and disc lattices, box traps). The case runs the same shape with the crosstalk model on and off (the reader switches the device) so the cost of the device is seen directly.

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
| Target | shaped field: kind = shaped, shape = disc, radius_um = 15.0, signal_margin_bins = 3 |
| Seed, budget | 20261028, 30 iterations |
| Reference method | M13 (the one whose maps the replay shows) |
| Device | 8 bits, crosstalk sigma 1.24 and q 1.8 on 3 by 3 sub-pixels, fill factor 1.0, flicker 0.0 rad |

### Methods

The ladder rows valid for the case, each checked against the registered method description at bake time (a method that does not take the case's target is listed as skipped, never silently absent):

- [M04](../../frameworks/M04_gerchberg-saxton.md), Gerchberg-Saxton
- [M08](../../frameworks/M08_mraf.md), MRAF
- [M10](../../frameworks/M10_conjugate-gradient.md), Conjugate-gradient minimization
- [M11](../../frameworks/M11_wirtinger-adam.md), Wirtinger gradient descent with Adam
- [M13](../../frameworks/M13_crosstalk-aware-cg.md), Device-aware CG with pixel crosstalk
- [M18](../../frameworks/M18_ot-initialized-mraf.md), Optimal-transport initialized MRAF

## Expected results

A uniform disc of 15 um radius on a device with pixel crosstalk (sigma 1.24, q 1.80, 8 bits). The crosstalk-aware method reaches a lower error than the same optimizer without the model, at the cost of efficiency. The published band is an error below 2 percent with efficiency 15 to 40 percent; the case's own band is wide on purpose: efficiency 0.05 to 0.9, relative standard deviation up to 30 percent.

### Expected ranges (checked by the bake)

Basis of the bands: **measured**, 3 seeds (the case seed and the next ones), range = mean plus or minus the wider of
10 percent of the mean and the seed spread, clipped to the domain.
The values are in `data-pipeline/pipeline/cases/measured_ranges.json` (`data-pipeline/pipeline/ranges.py`); every method range is keyed `<method>.<metric>`,
so it is never applied to another method. The bake fails when a result is outside its range (`data-pipeline/pipeline/core/expect.py`).
This section is written by `scripts/write_case_ranges.py`.
The seeds of M04, M08, M18 give the same value (the method does not depend on the seed here), so the band is the 10 percent floor.

| Key | Range | Measured on the 3 seeds | Meaning |
|---|---|---|---|
| `M04.efficiency` | 0.8257 to 1 | 0.917482, 0.917482, 0.917482 | fraction of the input power in the trap peaks |
| `M04.signal_efficiency` | 0.8331 to 1 | 0.925714, 0.925714, 0.925714 | fraction of the input power in the signal region of the shaped field |
| `M04.signal_rms_error_pct` | 40.42 to 49.4 | 44.9081, 44.9081, 44.9081 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |
| `M08.efficiency` | 0.1668 to 0.2039 | 0.185377, 0.185377, 0.185377 | fraction of the input power in the trap peaks |
| `M08.signal_efficiency` | 0.1676 to 0.2049 | 0.18625, 0.18625, 0.18625 | fraction of the input power in the signal region of the shaped field |
| `M08.signal_rms_error_pct` | 184.2 to 225.1 | 204.624, 204.624, 204.624 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |
| `M10.efficiency` | 0.3445 to 0.421 | 0.376011, 0.380187, 0.392107 | fraction of the input power in the trap peaks |
| `M10.signal_efficiency` | 0.3508 to 0.4287 | 0.383003, 0.387391, 0.398843 | fraction of the input power in the signal region of the shaped field |
| `M10.signal_rms_error_pct` | 66.58 to 196.2 | 105.314, 118.713, 170.118 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |
| `M11.efficiency` | 0.1489 to 0.1894 | 0.177778, 0.172032, 0.15754 | fraction of the input power in the trap peaks |
| `M11.signal_efficiency` | 0.1521 to 0.1922 | 0.180857, 0.174871, 0.160797 | fraction of the input power in the signal region of the shaped field |
| `M11.signal_rms_error_pct` | 62.72 to 76.66 | 68.5996, 68.4706, 71.9978 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |
| `M13.efficiency` | 0.3364 to 0.4111 | 0.373336, 0.373179, 0.374709 | fraction of the input power in the trap peaks |
| `M13.signal_efficiency` | 0.3428 to 0.4189 | 0.380649, 0.380241, 0.381671 | fraction of the input power in the signal region of the shaped field |
| `M13.signal_rms_error_pct` | 24.19 to 29.57 | 27.7419, 27.2436, 25.6635 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |
| `M18.efficiency` | 0.3781 to 0.4622 | 0.420149, 0.420149, 0.420149 | fraction of the input power in the trap peaks |
| `M18.signal_efficiency` | 0.3802 to 0.4647 | 0.422476, 0.422476, 0.422476 | fraction of the input power in the signal region of the shaped field |
| `M18.signal_rms_error_pct` | 23.96 to 29.28 | 26.6199, 26.6199, 26.6199 | RMS fractional error of the shaped field over its measure region after the scale fit, in percent |

## Validation anchor

Schroff et al. 2023, Sci. Rep. 13, 3252 (RMS error below 2 percent, efficiency 15 to 40 percent), https://doi.org/10.1038/s41598-023-30296-6

The anchor is the published result the case is set against; where the case's optics differ from the source's (a Gaussian beam against a flat one, 256 against 768 pixels), the card of the method says
what transfers. If the engine's output contradicts the anchor, that is a defect to report, not to hide.

## What each App group shows for this case

The App has up to six groups (Hologram, Focal plane, Traps, Convergence, Dynamics, Aberrations); the views a case shows follow the blocks of its record. For this case:

| Group | What it shows |
|---|---|
| Hologram | the phase mask ideal, quantized to 8 bits and crosstalk-blurred |
| Focal plane | the focal intensity with the disc and the diffraction orders |
| Convergence | signal-region error against iteration for the shaped-field methods |

## Notes

The bands are provisional. The target is a shaped field, so the point-trap methods do not apply; M17 was listed here while the learned model was pending; it is the three-plane volume method and takes point voxels (case C14), not a field, so it is no longer a method of this case.
