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
- [M17](../../frameworks/M17_unsupervised-cnn-hologram.md), Unsupervised CNN hologram
- [M18](../../frameworks/M18_ot-initialized-mraf.md), Optimal-transport initialized MRAF

## Expected results

A uniform disc of 15 um radius on a device with pixel crosstalk (sigma 1.24, q 1.80, 8 bits). The crosstalk-aware method reaches a lower error than the same optimizer without the model, at the cost of efficiency. The published band is an error below 2 percent with efficiency 15 to 40 percent; the case's own band is wide on purpose: efficiency 0.05 to 0.9, relative standard deviation up to 30 percent.

### Expected ranges (checked by the bake)

Basis of the bands: **provisional: set from the physical limits of the case, to be replaced by a measured band with its margin at the first bake of the real methods**. A key is a metric of the reference method, or `<method>.<metric>` for another method of the case. The bake fails when a result is outside its range
(`data-pipeline/pipeline/core/expect.py`).

| Key | Range | Meaning |
|---|---|---|
| `efficiency` | 0.05 to 0.9 | efficiency, the fraction of the input power in the trap peaks (traps) or in the signal region (shaped fields), 0 to 1 |
| `rel_std_pct` | 0 to 30 | relative standard deviation of the trap intensities, in percent |

No canonical bake of the twelve cases is committed yet: the measured values of the real methods on this case are shown by the Experiments page when the bake has run for the build, and this card
does not quote a number the bake has not produced.

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

The bands are provisional. The target is a shaped field, so the point-trap methods do not apply; the learned model M17 is a candidate and is listed, with its measurements pending.
