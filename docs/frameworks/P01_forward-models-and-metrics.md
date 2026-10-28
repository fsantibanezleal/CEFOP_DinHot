# P01, Forward models, geometry and metrics

Physics component. The canonical Python engine computes the light that a phase hologram sends to the focal plane in two
equivalent forms, propagates a focal field in depth, and scores the result with three metrics. Every method of the ladder
runs on this layer; the TypeScript live engine is held to it by parity tests.

| Item | Value |
|---|---|
| Modules | `data-pipeline/pipeline/model/holo/core/geometry.py`, `forward.py`, `metrics.py`, `modes.py`, `traps.py`, `types.py` |
| Tests | `tests/engine/test_geometry.py`, `test_forward.py`, `test_metrics.py`, `test_modes.py`, `test_traps.py`, `test_types_registry.py` |
| Used by | all 24 methods, the bake, the benchmark protocol, the notebooks |

## Purpose

A phase-only SLM of $n_{pix} \times n_{pix}$ pixels (pitch $p$) sits in the pupil plane of a lens of focal length $f$. The
light in the focal plane is the Fraunhofer transform of the SLM field. A method chooses the phase $\phi_j$ of every pixel;
the forward model says what that choice does at each trap, and the metrics say how good it is.

## Equations

### Geometry and sampling

The input beam amplitude $A_j$ is normalised so that $\sum_j A_j^2 = N_{pix} = n_{pix}^2$. For the Gaussian beam the
intensity is $\exp(-2 r^2 / w^2)$ with $w = w_{frac}\, n_{pix}\, p / 2$ (`geometry.py`, `input_amplitude`, line 68). Pixel
centres are at $(j - (n_{pix}-1)/2)\,p$, centred on the optical axis.

One bin of the zero-padded FFT in the focal plane and the unaliased half-window are

$$\Delta x = \frac{\lambda f}{\mathrm{pad}\; n_{pix}\, p}, \qquad X_{1/2} = \frac{\lambda f}{2 p}$$

(`focal_bin_m`, line 81; `half_field_m`, line 86). The FFT grid has $\mathrm{pad}\, n_{pix}$ bins, so it spans the replica
period $\lambda f / p$ of the pixel sampling. A trap farther than $X_{1/2}$ from the axis is refused with `OutOfFieldError`
naming the trap and the bound (case C11 exists to prove it). Source of the sampling relation: Schroff et al. 2023, Methods
(8.32 um per bin for $N = 1024$, $p = 12.5$ um, $f = 250$ mm, pad 2), https://doi.org/10.1038/s41598-023-30296-6 ; the
unaliased half-window is derived from it in DinHot's research record, not quoted from the paper.

### Point-trap form

For a trap $m$ at $(x_m, y_m, z_m)$ with vortex charge $l_m$ the delay at pixel $j$ is

$$\Delta_j^m = \frac{\pi z_m}{\lambda f^2}\,(x_j^2 + y_j^2) + \frac{2\pi}{\lambda f}\,(x_j x_m + y_j y_m) + l_m \operatorname{atan2}(y_j, x_j)$$

and the trap field and intensity are

$$V_m = \frac{1}{N_{pix}} \sum_j A_j\, e^{\,i(\phi_j - \Delta_j^m)}, \qquad I_m = |V_m|^2 .$$

$I_m$ is the fraction of the input power in the peak of trap $m$. Source: Di Leonardo, Ianni and Ruocco 2007, Eqs. (1) to
(4), https://doi.org/10.1364/OE.15.001913 . Traps without a vortex use a separable evaluation (a matrix product over chunks
of traps, memory $O(\mathrm{chunk}\cdot n_{pix})$); traps with a vortex use the dense evaluation, one trap at a time
(`forward.py`, `point_trap_projection`, line 73). `point_trap_backproject` (line 103) is the adjoint direction
$F_j = \sum_m c_m e^{+i\Delta_j^m}$ that every weighted Gerchberg-Saxton update takes the argument of.

### FFT form

The centred, zero-padded, orthonormal FFT of the SLM field, multiplied by the linear phase that moves its origin to the
optical axis, gives the focal field $E$ (`fft_focal_field`, line 133). Parseval holds: $\sum |E|^2 = N_{pix}$. At a trap on a
bin with $z = 0$ and no vortex,

$$V_m = E[\text{bin}]\;\frac{\mathrm{pad}}{n_{pix}}$$

exactly (the factor is $n_{fft} / N_{pix}$), which is what `trap_fields_from_fft` (line 275) returns. Source for the
transform: Schroff et al. 2023, Methods, Eq. (7).

### Angular spectrum and axial cut

A focal field is propagated by $\Delta z$ with the transfer function

$$H = \exp\!\Big(2\pi i\,\frac{\Delta z}{\lambda_m}\sqrt{1 - (\lambda_m \xi_x)^2 - (\lambda_m \xi_y)^2}\Big),\quad
\xi_x^2 + \xi_y^2 < \lambda_m^{-2}, \quad H = 0 \text{ otherwise}$$

with $\lambda_m = \lambda / n_{imm}$; evanescent components are removed (`angular_spectrum`, line 296; `axial_cut`, line 309,
which synthesises only the requested row). The cut assumes the scalar, paraxial model, so the $z$ position of a displaced
trap is exact only for $|z| \ll f$. Source: Schroff et al. 2023, Supplementary Eqs. (S2) to (S4). The band-limited variant of
Matsushima and Shimobaba (2009), https://doi.org/10.1364/OE.17.019662 , is not implemented: the plain form is valid for
short distances.

### Metrics

With $I_m$ the trap intensities (divided by the target weights $w_m$ when the weights differ),

$$e = \sum_m I_m, \qquad u = 1 - \frac{\max I - \min I}{\max I + \min I}, \qquad \sigma = 100\,\frac{\operatorname{std}(I)}{\operatorname{mean}(I)}\ \text{percent}$$

(`metrics.py`, lines 47, 52, 61; the population standard deviation, divisor $M$). Uniformity $u = 1$ is perfect. Polin et al.
2005 use the same ratio without the leading $1-$, which is a non-uniformity: the two must not be mixed. `power_budget`
(line 84) accounts for where the rest of the power goes: `traps`, `zero_order`, `ghosts` (everything else on the grid,
including folded replicas) and `remainder` (zero for the plain FFT form by Parseval).

### Elementary phases

`modes.py` holds the three terms of $\Delta_j^m$ as phase masks wrapped to $[0, 2\pi)$: `vortex_phase` (line 16), `lens_phase`
(line 26, the Fresnel term that moves a trap along the axis) and `grating_phase` (line 34, the blazed grating that moves it
sideways).

## Implementation

- Entrypoints: `forward.point_trap_fields(phi, setup, traps)`, `forward.fft_focal_field(phi, setup)`,
  `metrics.efficiency`, `uniformity`, `rel_std`, `traps.square_grid`, `hex_lattice`, `ring`, `random_min_spacing`,
  `lattice_3d`, `snap_to_bins`, `check_in_field`.
- Defaults of `Setup` (`geometry.py`, line 24): `pad = 2`, `beam = "gaussian"`, `waist_frac = 1.0`. The cases fix the optics
  per setup (see the case cards); the live grid is 256 by 256 pixels padded to 512 by 512.
- The method interface (`types.py`): `Budget`, `Target` (traps or a shaped field with its signal mask), `Result`, `MethodSpec`;
  see [the method interface and registry](../architecture/09_method-interface-and-registry.md).

## Acceptance criterion and test

The two forms are the same map: at on-bin traps the FFT and point-trap values agree to 1e-9 relative on 32, 64, 256 and 512
pixel grids (`tests/engine/test_forward.py::test_fft_and_point_trap_agree_on_bins`, `::test_agreement_on_real_grids`);
total power is conserved to 1e-12 relative (`::test_parseval_fft`); the point-trap form matches an explicit evaluation of the
delay formula with $z$ and a vortex to 1e-12 (`::test_point_trap_matches_brute_force_with_z_and_vortex`); the back-projection
is the adjoint of the projection (`::test_backproject_is_adjoint_of_projection`); the angular spectrum matches an analytic
Gaussian beam at one Rayleigh range to 5e-3 (`::test_angular_spectrum_matches_gaussian_beam`).

## Measured values (DinHot measurements, engine test run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| FFT versus point-trap agreement | below 1e-9 relative | on-bin traps, 32, 64, 256, 512 pixel grids |
| Parseval | 1e-12 relative | FFT propagation |
| Memory of 1024 traps | peak 16.8 MB, 0.08 s | 512 by 512 FFT grid, `tracemalloc`, `test_memory_under_one_gb_for_1024_traps_on_512` |

## Limits

- Scalar model. The high numerical aperture case (C07) carries a validity flag; the vectorial focus is not implemented.
- The grid spans one replica period: replicas fold onto it and are counted as ghosts in the power budget.
- The metric ceiling of a Gaussian beam is $(\overline{A})^2$ (0.87 at the test setup), so an efficiency of 0.9 is reachable
  only with a flat beam.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027 (metric definitions)
- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
- Matsushima and Shimobaba 2009, Opt. Express 17, 19662, https://doi.org/10.1364/OE.17.019662 (not implemented)
