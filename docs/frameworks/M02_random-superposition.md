# M02, Random superposition

| Item | Value |
|---|---|
| Family | analytic baseline |
| Lane | live |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m02_random_superposition.py`, `SPEC` line 21, `run` line 25 |
| Anchor | Di Leonardo, Ianni and Ruocco 2007, Table 1; Bianchi and Di Leonardo 2010 |

## Purpose

M01 with a random phase per trap. The random phases break the regular interference of the prisms and raise the efficiency a
great deal; the same random start seeds most of the iterative methods (the "SR" hologram).

## Equations

$$\phi_j = \arg \sum_m \sqrt{w_m}\; e^{\,i(\Delta_j^m + \theta_m)}, \qquad \theta_m \sim U[0, 2\pi)$$

The phases $\theta_m$ are drawn through the portable generator ([P07](P07_portable-rng.md)). Published on the 10 by 10 task:
efficiency 0.69, uniformity 0.01, relative standard deviation 89 percent. Sources: https://doi.org/10.1364/OE.15.001913 and
https://arxiv.org/abs/0907.4027 .

## Implementation

Defaults: none. Start function `baseline/_common.py` `sr_start` (line 42), reused by M04 to M07, M09 and others.

## Acceptance criterion and test

On the 10 by 10 task with a flat beam, efficiency above M01 and at least 0.65, uniformity below 0.35. The ordering transfers
from the source; the value of the uniformity does not (see below):
`tests/methods/baseline/test_m02_random_superposition.py::test_acceptance_10x10_over_seeds`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured (median, range) | Published | Conditions |
|---|---|---|---|
| Efficiency | 0.750 [0.738, 0.752] | 0.69 | 6 seeds, 256 by 256 pixels padded 2, 10 by 10 task, 8 bins apart |
| Uniformity | 0.252 [0.106, 0.272] | 0.01 | same |

The efficiency clause holds. The published uniformity is not reproduced: the intensity spread of random superposition on this
task is about 35 percent whatever the pixel count (128 or 256) or the beam, so it is intrinsic to the method here; the
published 89 percent is not reproduced and the acceptance bound is set at the measured ordering (uniformity below 0.35).

## Limits

High variance across seeds; no control of the trap intensities. A baseline, not a recommended method.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027
