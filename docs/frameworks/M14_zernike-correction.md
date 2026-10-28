# M14, Zernike aberration correction and sensorless modal recovery

| Item | Value |
|---|---|
| Family | aberration control |
| Lane | live |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/control/m14_zernike.py`, `SPEC` line 42, `run` line 60 |
| Anchor | Nogrette et al. 2014; Ebadi et al. 2021; Noll 1976 |

## Purpose

The optical system adds an unknown wavefront to the displayed phase. M14 subtracts a known correction, or finds it without a wavefront
sensor by moving each Zernike coefficient and watching the summed trap intensity on the camera.

## Equations

The system adds $2\pi\sum_j c_j Z_j$ (Noll coefficients in waves, [P03](P03_zernike.md)); the displayed hologram is the base hologram minus the
correction:

$$\phi_{shown} = \phi_{base} - 2\pi\sum_j \hat c_j Z_j, \qquad E = \mathcal{F}\big[A\,e^{\,i(\phi_{shown} + 2\pi\sum_j c_j Z_j)}\big]$$

(the aberration phase is always added to the final SLM phase: Nogrette et al., https://arxiv.org/abs/1402.5329 ; Ebadi et al.,
https://arxiv.org/abs/2012.12281 ). `mode = "correct"` subtracts the known coefficients, exactly when they equal the injected ones.

`mode = "recover"` (default) is a sensorless modal search with the emulated camera only. The merit is the summed measured trap intensity
$M(\hat c) = \sum_m I_m$, which the Maréchal approximation makes a Gaussian in the residual rms, $M\propto\exp[-(2\pi\sigma)^2]$ (UNVERIFIED against Noll 1976),
so $\ln M$ is a parabola in each coefficient. One sweep visits the modes (Noll 4 to 11, tip, tilt and piston excluded: they move or do not change the
traps), evaluates $M$ at $\hat c_j-\delta,\hat c_j,\hat c_j+\delta$ ($\delta$ = 0.06 waves), fits the parabola to $\ln M$ and moves to its vertex (step clipped to $\pm2\delta$; if
not concave, to the best of the three). The modes are not exactly orthogonal under the Gaussian beam and off-axis traps, so the sweep repeats; it stops when the
largest update falls below $10^{-4}$ waves. Cost: $3\times8+1$ camera frames per sweep.

## Implementation

Defaults (`run`, line 60): `mode = "recover"`, `modes = range(4, 12)` (`MODES`, line 45), `trial_waves = 0.06`, `base_iterations = 30` (the base hologram is
M06). `Budget.iterations` counts sweeps. `meta`: `coefficients` (length 21), `base_efficiency`, `uncorrected_efficiency`; `history` carries
`coef_rms_error` when `injected` is known. The default camera has ideal gains, no noise, no roll-off, seeded from `rng`.

## Acceptance criterion and test

Recovers an injected set of Noll modes 4 to 11 within 5 percent of their amplitude:
`tests/methods/control/test_m14_zernike.py::test_modal_search_recovers_noll_4_to_11_within_5_percent`; a known aberration is subtracted exactly
(`::test_known_aberration_is_subtracted_exactly`).

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Worst per-mode relative error | 0.0018, 0.0023, 0.0012 | 3 seeds, 5 sweeps; injected Noll 4 to 11, amplitudes 0.06 to 0.12 waves with random signs |
| Efficiency after recovery | 1.0000 of the aberration-free base | same (uncorrected: 0.13 to 0.30 of base) |
| With camera noise 1e-4 and gain error 0.05 | coefficient error under 10 percent of the injected rms | `::test_recovery_with_camera_noise` |

## Limits

- UNVERIFIED: Noll indices 12 to 21 and the Noll 1976 ordering ([P03](P03_zernike.md)).
- The merit assumes a roughly Gaussian response in each coefficient; strong aberrations break it.
- The camera is an emulation.

## References

- Nogrette et al. 2014, https://arxiv.org/abs/1402.5329
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Noll 1976, J. Opt. Soc. Am. 66, 207, https://doi.org/10.1364/JOSA.66.000207
