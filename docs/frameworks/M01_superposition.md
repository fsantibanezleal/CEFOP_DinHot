# M01, Superposition of prisms and lenses

| Item | Value |
|---|---|
| Family | analytic baseline |
| Lane | live (TypeScript port); also run by the benchmark |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m01_superposition.py`, `SPEC` line 20, `run` line 24 |
| Anchor | Di Leonardo, Ianni and Ruocco 2007, Table 1 |

## Purpose

The simplest hologram for $M$ traps: add the single-trap holograms (a prism per lateral offset, a lens per axial offset, a
spiral per vortex charge) and keep the phase of the sum. It costs $N \times M$ operations and needs no iteration, which is why
it is the first rung of the ladder and the reference every other method has to beat.

## Equations

$$\phi_j = \arg \sum_m \sqrt{w_m}\; e^{\,i\Delta_j^m}$$

with $\Delta_j^m$ the single-trap delay of [P01](P01_forward-models-and-metrics.md) and $w_m$ the target weight (all 1 in the
source). No randomness: `rng` is unused and the result is identical for every seed. Source: Di Leonardo, Ianni and Ruocco 2007,
Table 1, https://doi.org/10.1364/OE.15.001913 . Published on the 10 by 10 task (768 by 768 pixels, 8 bit): efficiency 0.29,
uniformity 0.01, relative standard deviation 257 percent.

## Implementation

Defaults: none. History has one entry (one pass). A shaped-field target is refused with a `ValueError` naming the supported kind
(the missing-data rule shared by every trap-only method).

## Acceptance criterion and test

On the 10 by 10 task with a flat beam, efficiency within 0.10 of 0.29 and uniformity below 0.05:
`tests/methods/baseline/test_m01_superposition.py::test_acceptance_10x10_matches_published_trend`. Further tests: determinism and
independence of the seed, and the single-trap hologram being a grating with unit field.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Published | Conditions |
|---|---|---|---|
| Efficiency | 0.281 | 0.29 | test setup (850 nm, f 250 mm, pitch 12.5 um), 256 by 256 pixels padded 2, 10 by 10 task 8 bins apart, deterministic |
| Uniformity | 0.0003 | 0.01 | same |

## Limits

Most of the light goes to the zero order and to spurious interference orders; uniformity is essentially zero. It is a baseline,
not a method to use for arrays.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
