# M13, Device-aware conjugate gradient with pixel crosstalk

| Item | Value |
|---|---|
| Family | optimization, device-aware |
| Lane | baked |
| Targets, dimensions | traps and shaped fields, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/optim/m13_crosstalk_cg.py`, `SPEC` line 36, `run` line 41 |
| Anchor | Schroff, La Rooij, Haller and Kuhr, Sci. Rep. 13, 3252 (2023) |

## Purpose

An SLM pixel is not an island: neighbouring pixels blur into each other. A method that optimises the hologram through that blur
reaches a lower error on the device than the same optimizer that ignores it.

## Equations

Each SLM pixel is upsampled to $3\times3$ computational pixels and the phase is convolved with a kernel before the Fourier transform:

$$\tilde\phi = K * \phi_{\uparrow3}, \qquad K = \mathcal{F}^{-1}\Big\{\exp\Big[-\frac{|\kappa_x|^q + |\kappa_y|^q}{\sigma^q}\Big]\Big\}, \qquad \sigma = 1.24\ \mathrm{px}^{-1},\ q = 1.80$$

(Schroff et al. 2023, Methods, Eq. (4), https://doi.org/10.1038/s41598-023-30296-6 , arXiv 2212.10507). The paper's cost is
$C = s\sum_S(\tilde T - \tilde I)^2$ with normalised $\tilde T, \tilde I$, Polak-Ribiere CG and the gradient by autodiff. Here the cost is Harte's $C_t$ of
[M10](M10_conjugate-gradient.md) on the device's focal field, optimised by the same Fletcher-Reeves and strong-Wolfe CG, and the
gradient is the closed form: the adjoint of the crosstalk operator is the convolution with the reversed kernel followed by the sum over each
$3\times3$ block (`core.device.crosstalk_adjoint`, see [P02](P02_device-model.md)), so the TypeScript port needs no autodiff.

## Implementation

Defaults: the model is the `device` passed in (crosstalk, pixel aperture and the quantizer, straight-through: quantized in the forward pass,
identity in the backward pass; flicker is dropped). With `device=None` M13 is M10 bit for bit (tested). `SCHROFF_DEVICE` (line 38) is
the published kernel. A vortex or axial trap on a device raises `ValueError`. Published (Schroff Table 1): large disc 1.9 percent error with the
model against 2.7 without, efficiency 28 against 34 percent, run time about 6 times longer.

## Acceptance criterion and test

On the crosstalk device, lower error than M10 without the model on a large disc:
`tests/methods/optim/test_m13_crosstalk_cg.py::test_acceptance_lower_error_than_m10_on_the_crosstalk_device_for_a_large_disc`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | M13 | M10 (no model) | Conditions |
|---|---|---|---|
| Signal-region error | 0.241 (efficiency 0.535) | 1.38 (efficiency 0.507) | 1 seed, 100 iterations, large disc on the crosstalk device, 64 pixel SLM padded 2 |

A pruned zero-padded transform makes the crosstalk forward and adjoint 2.4 times cheaper than the plain upsampled FFT pair (256 pixels:
0.14 s forward, 0.13 s adjoint).

## Limits

- UNVERIFIED: the unit of $k$ in the kernel (cycles per SLM pixel is assumed; see [P02](P02_device-model.md)).
- One seed in the acceptance test; the benchmark protocol repeats it over 20 seeds.
- Baked: a gradient run on the 3 by 3 upsampled grid is too heavy for the live budget at full size.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
