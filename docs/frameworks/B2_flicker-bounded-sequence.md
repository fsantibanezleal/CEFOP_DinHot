# B2, Flicker-bounded phase-continuous hologram sequence (beyond the published state of the art)

| Item | Value |
|---|---|
| Family | beyond, dynamic |
| Lane | baked |
| Targets, dimensions | traps with destination positions, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/beyond/b2_flicker_bounded.py`, `SPEC` line 52, `run` line 107 |
| Gap | linear phase interpolation does not optimise its intermediate frames |

## Purpose

When traps move, the intermediate holograms decide whether a moving trap flickers dark. B2 optimises every intermediate frame, with the trap phases locked to
a smooth trajectory, so the minimum transient intensity of a moving trap stays high.

## The gap

Linear phase interpolation (LPI, https://arxiv.org/abs/2501.01391 ) interpolates the position, amplitude and optical phase of every tweezer between two endpoint
holograms and inverts the transform at each step, so the intermediate holograms are never individually optimised; their trap intensities are uneven and the
interference of the transient spots makes the intensity dip. The paper observes that at 11 kHz sampling the WGS spot nearly vanished several times while the LPI
spot stayed above 70 percent.

## Method

For a trajectory $x_m(s)$, $s = 0..S$ and trap phases $\theta_m(s)$ smooth in $s$, every frame is the phase-fixed weighted GS of [M07](M07_phase-fixed-wgs.md) with the trap phases locked to the trajectory:

$$c_m = w_m a_m e^{i\theta_m(s)}, \qquad w_m \leftarrow w_m\langle r\rangle/r_m, \qquad \phi_j = \arg\sum_m c_m e^{+i\Delta_j^m(x_m(s))}$$

started from the previous frame's hologram and weights (a warm start, a few iterations per frame). The positions follow the minimal-jerk profile
$x_m(s) = x_m(0) + (x_m(S) - x_m(0))(10\tau^3 - 15\tau^4 + 6\tau^5)$, $\tau = s/S$. The phases are $\theta_m(s) = \theta_m(0) + \operatorname{wrap}(\theta_m^{end} - \theta_m(0))\,h(\tau)$
with the same $h$ (default: phases held), and `run` raises `ValueError` if the phase step per frame exceeds `phase_velocity_max` (default 0.3 rad; the LPI paper:
slips of several tenths of pi barely mattered, near pi lost atoms). The optimisation drops the penalty form of the research loss for the hard lock, its $\lambda\to\infty$ limit.

**Transient intensity (UNVERIFIED model).** Between frames $s$ and $s+1$ the displayed SLM field is modelled as the blend $f_a = A[(1-a)e^{i\phi_s} + a e^{i\phi_{s+1}}]$, $a\in[0,1]$,
and trap $m$ is read at its trajectory point $x_m(s+a)$: $I_m(s,a) = |V_m(f_a; x_m(s+a))|^2$. `transient_min_ratio` returns for each trap $\min_{s,a} I_m(s,a)/\operatorname{mean}_s I_m(s)$. The source gives
the LPI paper's measurement, not its transient equation. Not modelled: the SLM refresh rate and the temporal response of the device.

## Implementation

Defaults (`b2_flicker_bounded.py`, lines 54 to 56): `frames = 13` (the 6 by 6 to 4 by 4 sort), `frame_iterations = 10`, `phase_velocity_max = 0.3`, `n_fix = 12`; frame 0 is a cold
phase-fixed WGS of `budget.iterations` iterations. `target` holds the initial traps and `destination` the final positions with the same ids (`None`: a static sequence). Point-trap form,
ideal device.

## Acceptance criterion and test

Minimum transient intensity of a moving trap at least 0.9 of its mean, against LPI:
`tests/methods/beyond/test_b2_flicker_bounded.py::test_acceptance_transient_intensity_at_least_0_9_and_above_lpi`.

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | B2 | LPI baseline of the test | Conditions |
|---|---|---|---|
| Moving-trap minimum ratio | 0.919, 0.920, 0.923 | 0.724, 0.537, 0.551 | 3 seeds, 13 frames, 256 by 256 padded 2 |
| Per-frame relative standard deviation | at most 0.17 percent | 24 to 29 percent | same |

The LPI baseline in the test is written from the text of arXiv 2501.01391 (independent endpoint holograms, wrapped phase interpolation, superposition at every step) and scored
by the same function. The paper reports above 0.70 for LPI on hardware; the test's LPI scores lower under the DinHot transient model above, so the two numbers are not the same measurement.

## Limits

The transient model is DinHot's (UNVERIFIED); the comparison is against DinHot's implementation of LPI, not the authors' code.

## References

- Linear phase interpolation, https://arxiv.org/abs/2501.01391
- Kim et al. 2019, https://doi.org/10.1364/OL.44.003178
