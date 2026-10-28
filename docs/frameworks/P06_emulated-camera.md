# P06, Emulated camera

Physics component. The camera-in-the-loop method (M12) needs something to measure with. DinHot has no hardware, so the camera
is an emulation whose every error is a stated parameter.

| Item | Value |
|---|---|
| Module | `data-pipeline/pipeline/model/holo/core/camera.py` |
| Tests | `tests/engine/test_camera.py` |
| Used by | M12, M14 (sensorless recovery), the C01, C02, C03 feedback driver |

## Purpose

A feedback result on this camera shows that the loop works against these errors, not against a real instrument. A measured
hardware loop (a real SLM and camera) is a documented frontier of the product, not part of this build.

## Model

Measured trap intensities, in the units of $I_m = |V_m|^2$ (a fraction of the input power), are read from the centred focal
field $E$ as $|E|^2\,\mathrm{pad}^2/n_{pix}^2$ at the bin nearest to each trap, then:

- `blur_bins`: Gaussian blur (sigma in FFT bins) of the intensity map, evaluated as a normalised weighted average over a
  $\pm\lceil 3\sigma\rceil$ window around each trap bin.
- `rolloff`: multiplies each trap by the pixel-aperture envelope at its bin (the diffraction-efficiency roll-off of an ideal
  point-sampled hologram). It must not be combined with a field already produced by the device model, which carries the envelope.
- `gain_rms`: each trap id has a fixed multiplicative gain $\exp(s z - s^2/2)$ with $s$ = `gain_rms` and $z$ the first normal of a
  stream seeded from the seed and the trap id: log-normal with mean 1 and relative rms about `gain_rms`. It is drawn once per
  trap id, independent of the order and composition of the trap set.
- `noise_rms`: additive Gaussian noise per measurement, in the units of $I_m$, from the camera's own stream, so successive frames
  differ and a fresh camera with the same seed repeats the sequence. Results are clipped at 0.

(`camera.py`, class `EmulatedCamera`, line 34.) The Nogrette feedback case reads the published open-loop spread of 19 percent
rms as the camera gain error (Nogrette et al. 2014, https://arxiv.org/abs/1402.5329 ).

## Implementation

- Entrypoint: `camera.EmulatedCamera(seed, gain_rms=0.05, noise_rms=0.0, blur_bins=0.0, rolloff=True, fill_factor=1.0)` and
  `.measure(e, setup, traps, rng=None)`. The M12 default camera is `gain_rms = 0.19` without roll-off.
- Case settings (`data-pipeline/pipeline/cases/library.py`): C01 `gain_rms` 0.1, C02 0.19 (gain 0.7, 20 steps), C03 0.22 (gain 0.9,
  3 steps).

## Acceptance criterion and test

An ideal camera reads the true intensities, gains are per trap, seeded and independent of the trap order, noise is additive,
stateful and seeded, and the roll-off equals the pixel envelope (`tests/engine/test_camera.py::test_ideal_camera_reads_true_intensities`,
`::test_gains_are_per_trap_seeded_and_order_independent`, `::test_noise_is_additive_stateful_and_seeded`,
`::test_rolloff_matches_pixel_envelope`, `::test_validation_and_documented_emulation`).

## Measured values

None beyond the exact-property tests above; the camera has no accuracy to measure, it is the stated error model. The effect on
a loop is in [M12](M12_closed-loop-wgs.md).

## Limits

- Emulation, not a sensor model: no exposure, saturation, read-out noise correlation or pixel response.
- The gain error is static per trap; a drifting gain is not modelled.

## References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Kim et al. 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178
