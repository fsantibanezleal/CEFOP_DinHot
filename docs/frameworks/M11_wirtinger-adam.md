# M11, Wirtinger gradient descent with Adam

| Item | Value |
|---|---|
| Family | optimization |
| Lane | both (small sizes live, full size baked) |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/optim/m11_wirtinger_adam.py`, `SPEC` line 35, `run` line 41; shared `_common.py` |
| Anchor | Chakravarthula et al., ACM TOG 38(6), 213 (2019) |

## Purpose

Treat the hologram as a differentiable program: any linear forward model (the point-trap form, the FFT form, a device) can be
optimised with a first-order method as long as the gradient with respect to the phase is available. It is the bridge between the
classical iterative methods and learned holography.

## Equations

Minimise $f(|P(H(\phi))|^2, I) + \|\phi\|^2$ over the phase with a differentiable propagation $P$ and $H = c\,e^{i\phi}$. The gradient of the
real loss with respect to the complex field is the Wirtinger derivative $\partial L/\partial z^*$, pulled back through $P$ by the chain rule:

$$\frac{\partial L}{\partial \phi_j} = 2\operatorname{Re}\!\big(i\,f_j\,\overline{(P^H G)_j}\big), \qquad G = \frac{\partial L}{\partial z^*} = L'(I)\,z$$

(Chakravarthula et al. 2019, Eqs. (5) to (8), https://doi.org/10.1145/3355089.3356539 ). The paper uses L-BFGS for quadratic losses and
Adam with learning rate 0.001 for learned losses. Here the loss is the quadratic intensity loss $C_2 = \sum(I_m - T_m)^2/\sum T_m^2$ with the
design efficiency 0.9 for traps and 0.4 for fields; the $\|\phi\|^2$ term has weight zero (a phase penalty has no role for a phase-only
hologram of traps). Adam (Kingma and Ba 2015): $\beta_1 = 0.9$, $\beta_2 = 0.999$, $\epsilon = 10^{-8}$.

## Implementation

Defaults (`m11_wirtinger_adam.py`, lines 37 and 38): `PAPER_LR = 0.001` is recorded and `DEFAULT_LR = 1.0` is used. The paper's rate would
move a pixel at most 0.03 rad in 30 iterations. Start: uniform random phases from `rng` (`init` overrides). The model is the ideal device
unless `device` is given (traps then on FFT bins with $z = 0$).

## Acceptance criterion and test

Lower trap-intensity error than M04 at equal iterations on the 10 by 10 task:
`tests/methods/optim/test_m11_wirtinger_adam.py::test_acceptance_lower_trap_intensity_error_than_gs_at_equal_iterations`. The gradient is
checked on a set with $z$ offsets, a vortex and non-uniform weights.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | M11 | M04 (GS) | Conditions |
|---|---|---|---|
| Relative standard deviation of $I_m/w_m$ (percent) | 2.54, 2.46, 2.26 | 17.79, 17.98, 18.82 | 3 seeds, 30 iterations, 256 by 256 padded 2, 10 by 10 task |

Learning-rate tuning record (separate tuning seeds 11 to 13, median $\sigma$ in percent): lr 0.5 gives 2.92, **1.0 gives 2.42**, 2.0 gives 2.40,
4.0 gives 14.0. 2.0 ties within 1 percent and the smaller step is kept. On the test seeds 1 to 3: lr 0.01 gives 90 to 108, 0.03 gives 68 to 75, 0.1 gives
10 to 15, 0.3 gives 3.9 to 4.8, 1.0 gives 2.3 to 2.5.

## Limits

First-order, 30 iterations stop at a few percent; the tuned rate is specific to this loss and these grids.

## References

- Chakravarthula, Peng, Kollin, Fuchs, Heide and Wetzstein 2019, "Wirtinger Holography for Near-Eye Displays", ACM TOG 38(6), 213,
  https://doi.org/10.1145/3355089.3356539
- Kingma and Ba 2015, Adam (named in the module; not re-read)
