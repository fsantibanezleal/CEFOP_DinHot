# M07, Phase-fixed weighted GS

| Item | Value |
|---|---|
| Family | GS |
| Lane | live |
| Targets, dimensions | traps, 2D only |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m07_phase_fixed_wgs.py`, `SPEC` line 21, `run` line 24; engine `_gs.py` |
| Anchor | Kim, Kim, Lee and Ahn, Opt. Lett. 44, 3178 (2019) |

## Purpose

The practical state of the art for large point arrays. After a few weighted-GS iterations the phase of the field in the focal
plane is frozen, so that later iterations only adjust amplitudes; the weights stay effective and the array reaches percent-level
uniformity quickly. The same freeze is what makes camera correction (M12) converge in three steps.

## Equations

At iteration $i$ with focal-plane amplitudes $B_i(\mathbf{u}_m) = |V_m|/a_m$:

$$g_i(\mathbf{u}_m) = \frac{\langle B_i\rangle_N}{B_i(\mathbf{u}_m)}\,g_{i-1}(\mathbf{u}_m),\quad g_0 = 1,\qquad
\mathcal{F}[A_{i+1} e^{i\phi_{i+1}}] = g_i\, T\, e^{i\psi_i},\quad \psi_i = \psi_N\ (i \ge N)$$

so the focal phase $\psi$ follows the field ($\psi_i = \arg V_m$) for the first $N$ iterations and is then frozen at $\psi_N$;
$T_m = a_m = \sqrt{w_m}$. Source: Kim et al. 2019, https://doi.org/10.1364/OL.44.003178 , https://arxiv.org/abs/1903.09286 .
Published: 91.2 percent modulation efficiency on 1500 foci with $N = 12$ weighted-GS iterations before fixing, and camera
correction to 1.59 percent in three steps against 6.47 percent for conventional WGS. UNVERIFIED: the source does not define
$B_i$ (taken as the field amplitude, as in M06), nor whether the $N$-th iteration already uses the frozen phase (here it computes it).

## Implementation

Defaults (`run`, line 24): `n_fix = 12` (Kim), `form = "fft"` (the paper form; `"point"` is identical on bins). The camera
correction variant is in [M12](M12_closed-loop-wgs.md).

## Acceptance criterion and test

Fewer iterations than M06 to a relative standard deviation of 0.5 percent on a 50 by 30 array, with the phase fixed after 60
iterations (DinHot's measured default for this crowded grid):
`tests/methods/baseline/test_m07_phase_fixed_wgs.py::test_acceptance_fewer_iterations_than_gsw_on_50x30`. A second test pins the
measured stall of the source default.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Iterations to 0.5 percent, `n_fix = 60` | 64 and 64 (M06: 136 and 106) | 2 seeds, 50 by 30 array, 256 by 256 padded 2; re-measured 2026-10-30 |
| Minimum spread, `n_fix = 12` (Kim default) | stalls at 3.58 percent over 40 iterations | same grid; re-measured 2026-10-30 |
| Minimum spread against `n_fix` 12 / 20 / 30 / 40 / 60 | 3.58 / 2.13 / 0.855 / 0.080 / 0.143 percent (150 iterations, seed 1, re-measured 2026-10-30 by the studio report's `acceptance.py`; 2.9 / 1.6 / 1.5 / 0.8 / 1e-5 before the rule corrections) | same |

Mechanism: on this crowded grid (44 pixels per trap) the phase frozen after 12 iterations belongs to an unconverged hologram and
the weight update then cannot repair it. The source default of 12 is therefore not the default that meets the acceptance
criterion; the criterion is measured with 60.

## Limits

- `n_fix` is grid dependent; a larger value is needed on crowded grids. Whether the default should become grid dependent is open.
- 2D only (the focal phase freeze is defined for a plane).

## References

- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 ; https://arxiv.org/abs/1903.09286
