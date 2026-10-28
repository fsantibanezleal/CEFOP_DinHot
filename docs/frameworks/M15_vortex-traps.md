# M15, Laguerre-Gaussian vortex traps

| Item | Value |
|---|---|
| Family | modes |
| Lane | live |
| Targets, dimensions | traps with a vortex charge, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/control/m15_vortex.py`, `SPEC` line 32, `run` line 71 |
| Anchor | Di Leonardo et al. 2007; Polin et al. 2005 |

## Purpose

A trap can carry orbital angular momentum: a ring of light with a dark centre that rotates trapped particles or holds atoms in a
ring. The point-trap model carries the charge as one more term in the delay, so vortex traps mix freely with plain traps in one hologram.

## Equations

The delay of a charged trap carries one more term (Di Leonardo et al. 2007, text after Eq. (2), https://doi.org/10.1364/OE.15.001913 ; Polin et al.
2005 make 12 vortices of charge 8 inside a 51-trap array, https://doi.org/10.1364/OPEX.13.005831 ):

$$\Delta_j^m = \frac{\pi z_m}{\lambda f^2}(x_j^2+y_j^2) + \frac{2\pi}{\lambda f}(x_jx_m + y_jy_m) + l_m\operatorname{atan2}(y_j, x_j)$$

and the field $V_m$ of a charged trap is the overlap of the focal field with the vortex mode of charge $l_m$ (it is the projection that is equalised;
the intensity at the centre of the trap is dark). The hologram is the weighted GS of [M06](M06_gsw.md) (the back-projection carries the charges), so
the traps' mode powers equalise.

## Implementation

Defaults (`run`, line 71): `charge = None`; charges come from `Trap.charge`, and `charge=` overrides all traps (the vortex of that charge at every
trap). A target with no charged trap and no `charge` raises `ValueError`. `ring_phase_profile` (line 46) measures the acceptance quantity: the phase of
the focal field on a ring of `radius_bins` around the trap (default: the radius of maximum mean intensity between 0.5 and 5 bins), its total
winding (the sum of wrapped phase steps, $2\pi l$ times a fixed sign) and the maximum deviation from the best-fit line $\pm l\theta + c$. Only the point
form exists (charged traps are off the FFT bins). The sign convention: the field winding has the sign of the charge.

## Acceptance criterion and test

The ring phase winds by $2\pi l$ with an error under 0.1 rad:
`tests/methods/control/test_m15_vortex.py::test_isolated_vortex_ring_phase_within_0_1_rad` and `::test_vortex_array_ring_phase`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Case | Winding | Maximum deviation from the $l\theta$ line (rad) | Conditions |
|---|---|---|---|
| Isolated vortex, $l = 1, 2, 3, -2$ | exactly $2\pi l$ | 0.033 median [0.028, 0.060] | 2 seeds, 256 by 256 padded 2 |
| Four vortices in one hologram, 24 bins apart | exactly $2\pi l$ | rms 0.038 [0.028, 0.071]; maximum 0.082 [0.050, 0.132] | same |

One array member (an off-axis trap with $l = 2$) exceeds 0.1 rad in its maximum (0.12 to 0.13); the array test therefore asserts rms below 0.1 and
maximum below 0.2. The criterion of 0.1 rad is met in the isolated case; in the array it is met by the rms, not by every member's maximum.

## Limits

Charged traps are point-form only (no FFT form); the array maximum above.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Polin, Hovhannisyan and Sorensen 2005, Opt. Express 13, 5831, https://doi.org/10.1364/OPEX.13.005831
