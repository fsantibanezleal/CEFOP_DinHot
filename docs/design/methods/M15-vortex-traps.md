# M15: Laguerre-Gaussian vortex traps

| Item | Value |
|---|---|
| Ladder row | M15, tier classical (SDD, Method ladder) |
| Family, lane | modes (weighted GS with orbital angular momentum), live |
| Targets, dimensions | traps with a vortex charge, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m15_vortex.py` (`SPEC` line 32, `ring_phase_profile` line 46, `run` line 71) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` |
| Gate | `tests/methods/control/test_m15_vortex.py` |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m15`, line 287) |
| Card | [M15](../../frameworks/M15_vortex-traps.md) |

## Tier and role

The established way to give a trap orbital angular momentum: one more term in the delay of the point-trap model, so that vortex
traps (a ring of light with a dark centre) mix freely with plain traps in one hologram. It is a classical baseline because it is part
of the first formulation of the point-trap model (Di Leonardo, Ianni and Ruocco 2007, text after Eq. (2),
https://doi.org/10.1364/OE.15.001913) and was demonstrated in a trap array by Polin, Hovhannisyan and Sorensen 2005 (12 vortices of
charge 8 inside a 51-trap array, https://doi.org/10.1364/OPEX.13.005831).

## Problem it answers

Equalize the powers of traps that carry a vortex charge, in the same hologram as the other traps, and verify that the phase of the
focal field winds the right number of times around each trap.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps` in which at least one `Trap.charge` is non-zero, or the keyword `charge` (a non-zero
  integer that overrides all traps), `budget`, `rng`, optional `init`. A target with no charged trap and no `charge` raises a
  `ValueError` (`m15_vortex.py` line 78). Only the point form exists (charged traps are off the FFT bins).
- Output: `Result` with `phi`, one `history` entry per iteration, `fields` (the trap fields of the charged traps, recomputed at line
  82), `meta` including `traps`. `ring_phase_profile(phi, setup, trap, radius_bins=None)` is the measurement of the acceptance
  quantity: it returns `winding`, `sign`, `radius_bins`, `max_error`, `rms_error` and `ring_intensity`.

## The method

The delay of a charged trap carries one more term (Di Leonardo et al. 2007, text after Eq. (2)):

$$\Delta_j^m = \frac{\pi z_m}{\lambda f^2}(x_j^2+y_j^2) + \frac{2\pi}{\lambda f}(x_jx_m + y_jy_m) + l_m\operatorname{atan2}(y_j, x_j).$$

The field $V_m$ of a charged trap is the overlap of the focal field with the vortex mode of charge $l_m$ (it is the projection that is
equalized; the intensity at the centre of the trap is dark, tested by `::test_charged_trap_has_a_dark_centre`). The hologram is the
weighted GS of M06 (Eq. (18) of the same paper; `core.forward.point_trap_backproject` carries the charges): `run` calls
`_gs.run_traps` with the point form and `rule_gsw` (`m15_vortex.py` line 80), so the traps' mode powers equalize.

The acceptance quantity: on a ring of `radius_bins` around the trap (48 points, `_N_RING`, line 35; default radius the one of maximum
mean intensity among 0.5 to 5 bins in steps of 0.25, line 54) the focal phase $\psi_k$ is sampled; the total winding is the sum of the
wrapped phase steps, which is $2\pi l$ times a fixed sign, and the maximum error is the largest deviation of $\psi_k$ from the best-fit
line $\pm l\theta_k + c$ (lines 56 to 66). The field at a ring point is the plain (charge 0) point-trap projection there. The sign
convention: the field winding has the sign of the charge.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `charge` | `None` (charges from `Trap.charge`) | `m15_vortex.py` line 71 | interface choice |
| hologram rule | M06 weighted GS, point form | line 80 | Di Leonardo et al. 2007, Eq. (18) |
| ring points | 48 | line 35 | DinHot's choice, not sourced |
| ring radius | maximum mean intensity among 0.5, 0.75, ..., 5 bins | line 54 | DinHot's choice: the radius of the bright ring |

## Complexity and lane

The point form costs $N_{pix}$ per trap per iteration (a dense delay for a charged trap, one trap at a time, `core/forward.py`
`_dense_delay`). Lane `live` (`SPEC`, line 32); the port agrees with the Python fixtures to 1.8e-11 (T1 report D2, the largest observed
difference of the method group). In the bake the cases C05 and C06 run M15.

## Acceptance criterion and gate

Ladder row: the ring phase winds by $2\pi l$ with an error under 0.1 rad. Gate `tests/methods/control/test_m15_vortex.py`:

- `::test_isolated_vortex_ring_phase_within_0_1_rad`: one charged trap at the origin, $l = 1, 2, 3, -2$, seeds 1 and 2, `Budget(5)`;
  $|\text{winding} - 2\pi l| < 10^{-6}$ and the maximum deviation below 0.1 rad;
- `::test_vortex_array_ring_phase`: four vortices ($l = 1, 2, 3, -2$) 24 bins apart in one hologram, `Budget(20)`, seeds 1 and 2; the
  winding exact, the rms error below 0.1 rad and the maximum below 0.2 (the array bound is looser than the ladder, see the measured
  result);
- `::test_winding_sign_convention_is_the_same_for_every_charge`, `::test_charge_keyword_overrides_and_equalises_power`,
  `::test_no_vortex_is_rejected_and_deterministic`.

## Evaluation that confirms or refutes it

Confirmed if the winding is exactly $2\pi l$ and the maximum deviation from the $l\theta$ line stays below 0.1 rad for an isolated
vortex; refuted if the winding is off by an integer (a lost or doubled charge) or the deviation exceeds the bound. In an array the
ladder's bound of 0.1 rad is met by the rms error and not by every member's maximum.

## Measured result

Acceptance run of 2026-10-28 (E2 report D4 and D5), 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), 2
seeds:

| Case | Winding | Maximum deviation from the $l\theta$ line (rad) |
|---|---|---|
| Isolated vortex, $l = 1, 2, 3, -2$ | exactly $2\pi l$ | 0.033 median [0.028, 0.060] |
| Four vortices in one hologram, 24 bins apart | exactly $2\pi l$ | rms 0.038 [0.028, 0.071]; maximum 0.082 [0.050, 0.132] |

One array member (an off-axis trap with $l = 2$) exceeds 0.1 rad in its maximum (0.12 to 0.13). The array test therefore asserts rms
below 0.1 and maximum below 0.2; the ladder's 0.1 rad holds for the isolated case.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; the cases C05 and C06
have their own optics and vortex sets, listed in `data/derived/manifests/`; the values equal those of M06 on the same cases, because for a target whose traps already carry charges M06 chooses the point form
and runs the same weighted GS as M15):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C05 | 30 | 0.892 (0.89 to 0.895) | 0.977 (0.966 to 0.985) | 0.924 (0.71 to 1.29) |
| C06 | 30 | 0.705 (0.7 to 0.708) | 0.997 (0.997 to 0.998) | 0.129 (0.0875 to 0.169) |

## Limits and failure modes

Charged traps are point-form only (no FFT form, so no GPU path). The array maximum above 0.1 rad in one member. The model is scalar (the high-NA case C07 carries a validity flag, SDD). The vortex phase is a pure $l\theta$ term: the model carries
the azimuthal charge only, not a radial index.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
