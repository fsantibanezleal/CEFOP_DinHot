# M19, Volumetric 3D Gerchberg-Saxton (multi-plane)

| Item | Value |
|---|---|
| Family | GS |
| Lane | both (live at small size, baked at full size) |
| Targets, dimensions | traps, 3D only |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m19_multiplane.py`, `SPEC` line 47, `run` line 92 |
| Anchor | Whyte and Courtial, New J. Phys. 7, 117 (2005) |

## Purpose

Place traps at several depths from one hologram. Whyte and Courtial's 3D GS is not plane-by-plane propagation: it is a 3D Fourier
pair between a real-space volume (the target) and a k-space field restricted to the Ewald sphere.

## Equations

The k-space constraint is the sphere $k_0^2 = k_x^2 + k_y^2 + k_z^2$ with $k_z > 0$; in the discrete implementation, for each
$(k_x, k_y)$ only the $k_z$ element nearest to $\sqrt{k_0^2 - k_x^2 - k_y^2}$ carries the field. One iteration:

$$K[k_x,k_y,k_z^{sphere}] = A_j e^{i\phi_j},\quad U = \mathcal{F}_{3D}K,\quad U' = a_m e^{i\arg U}\text{ at the target voxels, 0 elsewhere},\quad
\phi_j = \arg\,(\mathcal{F}_{3D}^{-1}U')[k_x,k_y,k_z^{sphere}]$$

and the SLM amplitude is reset to the beam. Targets are point voxels with $a_m = \sqrt{w_m}$. Source: Whyte and Courtial 2005, Eqs. (1)
to (7), https://doi.org/10.1088/1367-2630/7/1/117 (author PDF read).

Mapping to the DinHot engine (derived here): SLM pixel $j$ is the lateral frequency $\xi = (x_j,y_j)/(\lambda f)$; the lateral voxel
is one FFT bin times `pad`; in $z$ the voxel pitch is `dz_m` and the carrier $k_0 z$ is removed, so the sphere element is
$i_z = \operatorname{round}\big(n_z\,dz\,(1-\sqrt{1-s})/\lambda_m\big)$ with $s = (\lambda_m\xi)^2$, which in the paraxial limit is the lens term
$\pi z\rho^2/(\lambda f^2)$ of the point-trap model. The reported trap fields are the point-trap model of the voxel-snapped traps, an
independent evaluation.

## Implementation

Defaults (`run`, line 92): `dz_m` = the smallest gap between the distinct plane depths of the target; `nz` = the next power of
two of at least 32 and 8 times the largest plane index. Grid limits at 256 by 256 pixels: the volume is 256 by 256 by $n_z$ complex,
33.6 MB for $n_z = 32$; one iteration is two 3D FFTs (about 0.3 s at $n_z = 32$). The axial placement error at depth $z$ is about
$\pi z/(n_z dz)$ rad (0.05 rad at 40 mm for $n_z dz$ = 1.28 m). The depth extent $n_z dz$ is a period: the sphere elements wrap at the
corners of the square SLM. Planes closer than the depth of field $2\lambda/NA^2$ (about 40 mm at the test setup) cannot be told apart
by any hologram.

## Acceptance criterion and test

On a three-plane target, every plane mean within 25 percent of the overall mean. The SDD does not define "the plane intensity
band"; the test defines it that way: `tests/methods/baseline/test_m19_multiplane.py::test_acceptance_three_planes_within_the_band`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Plane mean over overall mean | 0.938, 0.987, 1.075 and 0.926, 1.034, 1.039 (worst deviation 7.5 percent) | 3 planes at -40, 0, +40 mm, 25 traps each, 20 iterations, 2 seeds, test setup |
| Within-plane relative standard deviation | 18 to 22 percent | same |
| Efficiency | 0.856 | same |

## Limits

- UNVERIFIED: the source reports a weak experimental match (a secondary statement, not read); the paper has no per-plane weighting,
  so none is applied.
- No plane-by-plane variant exists in this build. The test setup's plane separation (40 mm) is set by the depth of field of the
  250 mm lens; the cases use the optics of their own setups (see C05).

## References

- Whyte and Courtial 2005, New J. Phys. 7, 117, https://doi.org/10.1088/1367-2630/7/1/117
