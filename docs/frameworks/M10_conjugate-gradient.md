# M10, Conjugate-gradient minimization

| Item | Value |
|---|---|
| Family | optimization |
| Lane | both (small sizes live, full size baked) |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/optim/m10_cg.py`, `SPEC` line 38, `run` line 93; shared `_common.py` |
| Anchor | Harte, Bruce, Belmonte and Arnold, Opt. Express 22, 26548 (2014) |

## Purpose

Minimise an intensity cost over all pixel phases at once with a gradient method. The gradient of the cost costs two Fourier
transforms, so it is cheap; the powered cost suppresses optical vortices that the basic cost leaves in shaped potentials.

## Equations

The SLM field is $E_{in} = A_j e^{i\phi_j}$, the focal field $E_{out}$ its zero-padded Fourier transform, and the cost over the signal
region (the noise region is free):

$$C_t = \sum_{nm}\big(T_{nm} - |\tilde\psi_{nm}|^2\big)^t, \qquad
\frac{\partial C_t}{\partial \phi_{rs}} = 2t\,\operatorname{Re}\big(i\,\psi_{rs}^*X_{rs}\big), \qquad
X_{rs} = \sum_{nm}(T_{nm} - I_{nm})^{t-1}\,\tilde\psi_{nm}^*\,e^{+2\pi i(rn+sm)/N}$$

(Harte et al. 2014, Eqs. (1) to (11), https://doi.org/10.1364/OE.22.026548 , arXiv 1408.0188). $t = 2$ is the basic cost; the
powered cost $t = 4$ suppresses vortices (Harte: 26 percent error with $t = 2$; sequential $t = 4$ then $t = 2$ gives 0.07 percent on a
ring and power-law target after 13000 iterations). Optimizer: Fletcher-Reeves conjugate gradient, $\gamma_i = g_i\cdot g_i/g_{i-1}\cdot g_{i-1}$
(Harte Eqs. (3) to (5)), with a strong-Wolfe line search (cubic interpolation, $c_1 = 10^{-4}$, $c_2 = 0.1$, after Nocedal and Wright,
Numerical Optimization, Algorithms 3.5 and 3.6); the source does not state the line search. The cost is normalised by $\sum T^t$.

## Implementation

Defaults (`run`, line 93, and the module docstring): `t = None` means stages $(4, 2)$ with an equal share of the iterations each for
shaped fields and $t = 2$ for traps; `efficiency` target 0.4 for fields and 0.9 for traps (Harte: 45 to 64 percent in the trapping
region); a start of uniform random phases from `rng` (`init` overrides). The model is the ideal device: M13 is the device-aware
variant, and the caller scores M10 on a device with [P02](P02_device-model.md). `DEFAULT_LATTICE_ITERATIONS = 1500` (line 40).

## Acceptance criterion and test

The analytic gradient matches finite differences; a square lattice reaches below 1 percent error:
`tests/methods/optim/test_m10_cg.py::test_acceptance_square_lattice_below_one_percent_error`. The gradient checks run on a shaped
target and on traps for $t = 2$ and 4 and through the crosstalk operator.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Reference | Conditions |
|---|---|---|---|
| Gradient against finite differences | largest relative error 1.76e-7 ($t = 2$ field), 8.5e-8 ($t = 4$), 4.5e-8 and 1.4e-7 with crosstalk | limit 1e-5 | 4 cases, 6 directions |
| Square lattice error | 0.55 and 0.51 percent | Harte 0.58 percent at 4000 iterations | 2 seeds, 1500 iterations, $t = 2$ |

## Limits

- The strong-Wolfe line search is DinHot's choice; the source does not state one.
- The ideal-device model: scoring on a real device loses uniformity (the reason for M13).
- Cost grows with the pixel count; the full-size runs are baked.

## References

- Harte, Bruce, Belmonte and Arnold 2014, Opt. Express 22, 26548, https://doi.org/10.1364/OE.22.026548
- Nocedal and Wright, Numerical Optimization (line search algorithms 3.5 and 3.6)
