# M04, Gerchberg-Saxton (point-trap and FFT forms)

| Item | Value |
|---|---|
| Family | GS |
| Lane | live |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m04_gs.py`, `SPEC` line 19, `run` line 22; engine `_gs.py` |
| Anchor | Gerchberg and Saxton 1972; Di Leonardo, Ianni and Ruocco 2007, Table 1 |

## Purpose

Alternate between the SLM plane and the trap plane: impose the known amplitudes in each, keep the phase that comes back.
GS is the workhorse of holographic optical tweezers and the baseline of the learned model M17.

## Equations

With $V_m = \frac1N\sum_j A_j e^{i(\phi_j - \Delta_j^m)}$ and target amplitudes $a_m = \sqrt{w_m}$,

$$\phi_j^{k} = \arg \sum_m a_m\,\frac{V_m^{k-1}}{|V_m^{k-1}|}\;e^{+i\Delta_j^m}$$

started from the SR hologram of [M02](M02_random-superposition.md) (`init` overrides). Source: Di Leonardo et al. 2007, Table 1,
https://doi.org/10.1364/OE.15.001913 ; the original text of Gerchberg and Saxton 1972 was not opened (UNVERIFIED). Published:
efficiency 0.94, uniformity 0.60, relative standard deviation 17 percent after 30 iterations on the 10 by 10 task.

## Implementation

- `form = "point"` (default for traps) is the direct sum of [P01](P01_forward-models-and-metrics.md); `form = "fft"` places the
  constraint on the FFT bins of the zero-padded transform and requires traps on bins with $z = 0$ and no vortex. The two forms are
  the same map and agree to rounding.
- A shaped target (signal mask and amplitude on the FFT grid) is accepted in the FFT form and iterated as GS with a zero noise
  region (`_gs.run_field` with mixing 1), the baseline of [M08](M08_mraf.md); its default start is a Fresnel-lens phase of 20 waves
  (`_gs.py` line 150).
- Defaults: `form = "point"` for traps, `"fft"` for a field; `start_waves = 20`.

## Acceptance criterion and test

The two forms agree to 1e-9 rad (the SDD bar; the test asserts 1e-6 rad on the whole phase and 1e-9 on the metrics); 30 iterations on the 10 by 10 task with a flat beam reach efficiency at least 0.9 and uniformity
near 0.6: `tests/methods/baseline/test_m04_gs.py::test_acceptance_10x10_30_iterations_flat_beam`. With the Gaussian beam of the core
default the efficiency bar is set to 0.9 of the metric ceiling:
`::test_acceptance_10x10_30_iterations_gaussian_beam`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Beam | Efficiency | Uniformity | Conditions |
|---|---|---|---|
| Flat | 0.939 [0.933, 0.939] | 0.604 [0.557, 0.626] | 3 seeds, 30 iterations, 256 by 256 padded 2, 10 by 10 task |
| Gaussian (waist 1) | 0.815, which is 0.937 of the ceiling 0.869 | not tested | same |

The forms agree to 6e-13 rad (8 iterations, 10 by 10). The published values (0.94 and 0.60) are reproduced with a flat beam.

## Limits

- The efficiency of a Gaussian beam is capped by $(\overline{A})^2 = 0.869$ at the test setup, so the bar of 0.9 holds only for a
  flat beam.
- Uniformity stalls near 0.6: GS does not control the trap intensities. Weighted variants M05 to M07 do.
- Stagnation in local minima and ghost traps.

## References

- Gerchberg and Saxton 1972 (original text not opened, UNVERIFIED)
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
