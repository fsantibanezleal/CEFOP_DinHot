# M19: Multi-plane GS (volumetric 3D Gerchberg-Saxton)

| Item | Value |
|---|---|
| Ladder row | M19, tier classical (SDD, Method ladder: "Multi-plane GS", volumetric 3D GS of Whyte and Courtial) |
| Family, lane | GS, both (live at small size, baked at full size) |
| Targets, dimensions | traps (point voxels), 3D only |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m19_multiplane.py` (`SPEC` line 47, `_plan` line 55, `_sphere_index` line 82, `run` line 92) |
| Gate | `tests/methods/baseline/test_m19_multiplane.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m19`, line 184) |
| Card | [M19](../../frameworks/M19_volumetric-3d-gs.md) |

## Tier and role

The established method for placing traps at several depths from one hologram, in the form of Whyte and Courtial 2005: a 3D Gerchberg-
Saxton between a real-space volume (the target) and a k-space field restricted to the Ewald sphere, which is a 3D Fourier pair and not a
plane-by-plane propagation. It is a classical baseline because it is the reference volumetric method for point targets, because it
is the baseline of the learned multi-plane network M17 (the hybrid is compared with M19 at equal wall-clock), and because the point-trap
3D form of M06 (an axial term in the delay) is the cheaper alternative it is measured against in the 3x3x3 lattice. Source: Whyte and
Courtial, New J. Phys. 7, 117 (2005), https://doi.org/10.1088/1367-2630/7/1/117, Eqs. (1) to (7) (the author PDF was read in the gap
study).

## Problem it answers

A hologram for point traps spread over several planes, with the physical constraint that the k-space field of a hologram lies on the
Ewald sphere, so that the planes interact through one hologram rather than being propagated independently.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` with point voxels (one voxel per trap; two traps on one voxel raise a `ValueError`,
  line 76), `budget`, `rng`, optional `init` (shape `n_pix` by `n_pix`), `dz_m` (the axial voxel pitch in metres), `nz` (the number of
  axial elements). A target on a single depth needs `dz_m` (line 60). A trap outside the lateral voxel grid raises a `ValueError`
  (line 73). `device` is ignored.
- Output: `Result` with `phi`, one `history` entry per iteration, `fields` (the point-trap model of the voxel-snapped traps, an
  independent evaluation: `fields` equals `core.forward.point_trap_fields(phi, setup, meta['snapped'])`, tested), and `meta` (`snapped`,
  `dz_m`, `nz`, `iterations`).

## The method

The k-space constraint is the Ewald sphere $k_0^2 = k_x^2 + k_y^2 + k_z^2$ with $k_z > 0$; in the discrete implementation, for each
$(k_x, k_y)$ only the $k_z$ element nearest to $\sqrt{k_0^2 - k_x^2 - k_y^2}$ carries the field, all others are zero (a hemisphere one
element thick). One iteration (Whyte and Courtial 2005, Eqs. (1) to (7)):

$$K[k_x,k_y,k_z^{\rm sphere}] = A_j e^{i\phi_j},\quad U = \mathcal F_{3D}K,\quad U' = a_m e^{i\arg U}\ \text{at the target voxels, 0 elsewhere},\quad
\phi_j = \arg\,(\mathcal F_{3D}^{-1}U')[k_x,k_y,k_z^{\rm sphere}]$$

and the SLM amplitude is reset to the beam; $a_m = \sqrt{w_m}$. The hologram is the k-space phase on the sphere projected onto the SLM
plane (their Fig. 1 and Section 5.1).

Mapping to the DinHot engine (derived in the module, not in the source): SLM pixel $j$ is the lateral frequency $\xi = (x_j, y_j)/(\lambda f)$;
the lateral voxel is one FFT bin times `pad`, $dx = \lambda f/(n_{pix}\,p)$, so a trap at $x_m$ sits on voxel $\operatorname{round}(x_m/dx)$
(lines 70 and 71); in $z$ the voxel pitch is `dz_m` and the carrier $k_0 z$ is removed (baseband), so the sphere element is

$$i_z = \operatorname{round}\Big(n_z\,dz\,\frac{1-\sqrt{1-s}}{\lambda_m}\Big)\bmod n_z,\quad s = (\lambda_m\xi)^2,\ \lambda_m = \lambda/n_{imm}$$

(`_sphere_index`, lines 82 to 89), which in the paraxial limit is the lens term $\pi z\rho^2/(\lambda f^2)$ of the point-trap model. One iteration
is a 3D FFT pair on a volume of `nz` by `n_pix` by `n_pix` complex128 (lines 116 to 123). The lateral origin is put on the optical axis
by a linear ramp (line 101). The start is the SR hologram of the snapped traps (line 107).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `dz_m` | the smallest gap between the distinct plane depths of the target | `m19_multiplane.py` lines 57 to 61 | DinHot's rule: the finest axial structure that the target contains |
| `nz` | the next power of two of at least 32 and of $8\,\max|i_z| + 1$ | line 66 (`_next_pow2`, line 51) | DinHot's rule: the 3D FFT length; 32 gives a volume of 33.6 MB at 256 by 256 pixels |
| per-plane weighting | none | n/a | the source has none (UNVERIFIED: the paper reports a weak experimental match, a secondary statement that was not read) |

## Complexity and lane

One iteration is two 3D FFTs on `nz` by `n_pix` by `n_pix` (about 0.3 s at $n_z = 32$ on the 256 by 256 grid, module docstring); the volume
is 33.6 MB at $n_z = 32$. The depth extent $n_z\,dz$ is a period: the sphere elements wrap modulo $n_z$ at the corners of the square SLM
(periodic replicas of the volume, $n_z\,dz$ apart). The axial placement error at depth $z$ is about $\pi z/(n_z\,dz)$ rad (0.05 rad at
40 mm for $n_z\,dz = 1.28$ m). Axial resolution is set by the aperture: the depth of field is about $2\lambda/NA^2$ with
$NA = n_{pix}\,p/(2f)$ (about 40 mm at the test setup), so planes closer than that cannot be told apart by any hologram. Lane `both`
(`SPEC`, line 47): the port runs it at small size live; parity worst difference 6.0e-14 (T1 report D2). Test runtime: about 37 s on the
development machine (E2 report).

## Acceptance criterion and gate

Ladder row: on a three-plane target, every plane mean within 25 percent of the overall mean. The SDD does not define "the plane intensity
band"; the test defines it as stated here. Gate `tests/methods/baseline/test_m19_multiplane.py::test_acceptance_three_planes_within_the_band`:
three planes at $-40$, 0 and $+40$ mm, a 5 by 5 grid of traps on each (spacing 6 voxels, the planes shifted laterally by 3 voxels),
`dz_m` = 40 mm, 20 iterations, seeds 1 and 2; the mean intensity of every plane within 25 percent of the mean over all traps, and the
final efficiency above 0.3. The within-plane uniformity is reported, not bounded. Companion tests: the reported fields equal the
point-trap model of the snapped traps; a single off-plane trap is focused (efficiency above 0.7 of the beam ceiling); the efficiency
rises over the iterations; determinism and validation (two traps on one voxel are refused).

## Evaluation that confirms or refutes it

Confirmed if no plane is starved or dominant and the hologram is efficient (above 0.3); refuted if a plane leaves the 25 percent band,
which would mean the Ewald-sphere constraint does not couple the planes as the source describes. The within-plane spread is not part
of the criterion and is high (below).

## Measured result

Acceptance run of 2026-10-28 (E2 report D3 and D5): three planes at $-40$, 0, $+40$ mm, 25 traps each, 20 iterations, 2 seeds, 256 by 256
padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um):

| Quantity | Measured |
|---|---|
| Plane mean over overall mean | 0.938, 0.987, 1.075 and 0.926, 1.034, 1.039 (worst deviation 7.5 percent) |
| Within-plane relative standard deviation | 18 to 22 percent |
| Efficiency | 0.856 |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C05 only, a
three-plane array with vortices, with its own optics in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C05 | 30 | 0.526 (0.512 to 0.538) | 0.0153 (0.00121 to 0.0273) | 62.4 (62.1 to 62.6) |

## Limits and failure modes

- The within-plane relative standard deviation is 18 to 22 percent in the acceptance test and 62 percent in the bake (C05): the method
  equalizes the planes, not the traps. M06's 3D point-trap form reaches a relative standard deviation of 0.7 to 1.3 percent on the same
  case.
- Memory: the volume grows with `nz`; planes closer than the depth of field cannot be separated.
- The axial placement is rounded to the sphere element (error $\pi z/(n_z\,dz)$ rad); the axial period is $n_z\,dz$.
- No plane-by-plane variant exists in this build; no per-plane weighting.

## References

- Whyte and Courtial 2005, New J. Phys. 7, 117, https://doi.org/10.1088/1367-2630/7/1/117
- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913 (the point-trap 3D form used as comparison)
