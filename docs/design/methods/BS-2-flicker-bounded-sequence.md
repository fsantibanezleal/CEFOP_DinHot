# BS-2: Flicker-bounded phase-continuous sequence (engine id B2)

| Item | Value |
|---|---|
| Ladder row | BS-2, tier beyond (SDD, Method ladder and Beyond the state of the art) |
| Family, lane | beyond, dynamic, baked |
| Targets, dimensions | traps with destination positions, 2D and 3D (`SPEC.dims` is `(2, 3)`; the acceptance test is 2D) |
| Module | `data-pipeline/pipeline/model/holo/methods/beyond/b2_flicker_bounded.py` (`SPEC` line 52, `min_jerk` line 59, `trajectory` line 70, `transient_min_ratio` line 88, `run` line 107) |
| Gate | `tests/methods/beyond/test_b2_flicker_bounded.py` |
| Live port | none (lane `baked`; `getMethod('B2')` raises `NotLive`) |
| Card | [B2](../../frameworks/B2_flicker-bounded-sequence.md) |
| Outcome | hypothesis confirmed in DinHot's transient model on the acceptance task (0.916 to 0.926 against the test's LPI at 0.551 to 0.709 after the 2026-10-29 rule corrections; 0.919 to 0.923 against 0.537 to 0.724 before), with the measured scope of the update below; the model is UNVERIFIED |

## Tier and role

Beyond the state of the art: DinHot's own proposal.

**Hypothesis.** The linear phase interpolation (LPI) of the sequence interpolates the position, amplitude and optical phase of every tweezer between two endpoint holograms and inverts the
transform at each step, so the intermediate holograms are never individually optimized. Optimizing every intermediate frame, with the trap phases locked to a smooth trajectory, keeps the
minimum transient intensity of a moving trap at least 0.9 of its mean and above the LPI sequence's, with a per-frame spread no worse than LPI's.

**The gap.** The LPI paper (https://arxiv.org/abs/2501.01391) observes that at 11 kHz sampling the weighted-GS spot nearly vanished several times while the LPI spot stayed above 70 percent; its
intermediate holograms are not optimized, so their trap intensities are uneven, and phase slips near $\pi$ lost atoms while slips of several tenths of $\pi$ barely mattered (gap study, algorithms
dossier D5.1 B2). No source optimizes the frames of a trap trajectory.

## Problem it answers

Move traps without a moving trap dimming enough to lose its atom, with every frame a good hologram on its own.

## Inputs and outputs

- Inputs: `setup`, `target` of kind `traps` holding the initial traps (a shaped field raises a `ValueError` naming `traps`), `destination` (a `TrapSet` with the same ids in the same order; `None`:
  a static sequence), `frames` (at least 2), `frame_iterations`, `end_phases`, `phase_velocity_max`, `n_fix`, `budget` (`iterations` is the number of iterations of the cold frame 0), `rng`,
  optional `init`. Point-trap form, ideal device.
- Output: `Result` whose `phi` is the last frame; `history` one entry per frame; `fields` the last frame's trap fields; `meta`: `frames` (all holograms), `transient_ratio` (per trap),
  `moving` (the traps with a displacement), `theta0`, `frame_iterations`, `n_frames`.
- `run` raises a `ValueError` when the phase step per frame exceeds `phase_velocity_max` (`b2_flicker_bounded.py` lines 129 to 131); the destination must hold the same ids.

## The method

For a trajectory $x_m(s)$, $s = 0..S$, and trap phases $\theta_m(s)$ smooth in $s$, every frame is the phase-fixed weighted GS of Kim et al. 2019 (M07) with the trap phases locked to the trajectory,

$$c_m = w_m\,a_m\,e^{i\theta_m(s)},\qquad w_m \leftarrow w_m\langle r\rangle/r_m,\qquad \phi_j = \arg\sum_m c_m\,e^{+i\Delta_j^m(x_m(s))},$$

started from the previous frame's hologram and weights (a warm start of a few iterations per frame; `run`, lines 136 to 148). Positions follow the minimal-jerk profile
$x_m(s) = x_m(0) + (x_m(S) - x_m(0))(10\tau^3 - 15\tau^4 + 6\tau^5)$, $\tau = s/S$ (`min_jerk`, line 59). The phases are
$\theta_m(s) = \theta_m(0) + \operatorname{wrap}(\theta_m^{end} - \theta_m(0))\,h(\tau)$ with the same $h$; by default $\theta^{end} = \theta(0)$ (phases held). Frame 0 is a cold phase-fixed WGS of
`budget.iterations` iterations (`n_fix` capped at the budget), later frames use `frame_iterations`. The optimization drops the penalty form of the research record's loss,
$\lambda\sum(\arg V - \theta)^2$, for the hard lock, its $\lambda\to\infty$ limit.

**Transient intensity (UNVERIFIED model).** Between frames $s$ and $s+1$ the displayed SLM field is modelled as the blend $f_a = A\,[(1-a)e^{i\phi_s} + a\,e^{i\phi_{s+1}}]$, $a\in[0, 1]$ (the liquid crystal
relaxing between the two holograms), and trap $m$ is read at its trajectory point $x_m(s+a)$: $I_m(s, a) = |V_m(f_a; x_m(s+a))|^2$. `transient_min_ratio` returns for each trap
$\min_{s,a} I_m(s, a)/\operatorname{mean}_s I_m(s)$ over 10 sub-steps per frame interval (lines 88 to 104). Both B2 and the LPI baseline of the test are scored by this same function. The source gives
the LPI paper's measurement, not its transient equation. Not modelled: the SLM refresh rate and the temporal response of the device.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `frames` | 13 | `b2_flicker_bounded.py` line 54 | the research record's 6 by 6 to 4 by 4 sort (the acceptance test moves a 4 by 4 lattice, below) |
| `frame_iterations` | 10 | line 55 | DinHot's choice: a few warm iterations per frame (a mutation with 0 makes the acceptance test fail, ratio 3e-6) |
| `phase_velocity_max` | 0.3 rad per frame | line 56 | the LPI paper: slips of several tenths of $\pi$ barely mattered, near $\pi$ lost atoms; 0.3 rad is DinHot's bound |
| `n_fix` | 12 | line 110 | Kim's $N$ (M07), capped at `budget.iterations` for frame 0 |
| substeps of the transient model | 10 | line 88 | DinHot's choice |

## Complexity and lane

$S$ warm-started runs, $O(S\,K\,N_{pix}\,M)$ in the point form. The LPI paper reports under 200 microseconds per hologram on an RTX 4090 for its own method; DinHot does not rely on it. Lane `baked`
(`SPEC`, line 52). The acceptance test takes about 21 s on the development machine (E3 report).

## Acceptance criterion and gate

Ladder row: minimum transient intensity of a moving trap at least 0.9 of its mean, against LPI. Gate
`tests/methods/beyond/test_b2_flicker_bounded.py::test_acceptance_transient_intensity_at_least_0_9_and_above_lpi`: a 4 by 4 lattice at 8 bins on 256 by 256 padded 2, the two right-hand columns move
4 bins in $x$ (8 moving traps), 13 frames, `Budget(30)`, seeds 1 to 3. The LPI baseline is written in the test from the text of arXiv 2501.01391 (independent endpoint holograms of phase-fixed WGS with 30
iterations each, positions, amplitudes and optical phases read from them, linear interpolation with the wrapped phase difference, the superposition at every step, no per-frame optimization). For every
seed: B2's `transient_ratio` over the moving traps at least 0.9 and above LPI's, `n_frames` equal to 13, and B2's largest per-frame relative standard deviation at most LPI's largest. Other tests: the
minimal-jerk profile, the wrap and the trajectory endpoints, the phase-velocity bound is enforced, a static sequence keeps the phases locked, determinism.

## Evaluation that confirms or refutes it

Confirmed if B2's minimum transient ratio is at least 0.9 and above LPI's, with the frames individually uniform; refuted if LPI's frames were as good (the proposal would add nothing) or if the ratio of B2
fell below 0.9. Because both are scored with the same UNVERIFIED blend model, the comparison is internally fair and not a statement about a real SLM.

## Measured result

Acceptance run of 2026-10-28 (E3 report D3 and D5), 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch 12.5 um), 3 seeds:

| Quantity | B2 | LPI baseline of the test |
|---|---|---|
| Moving-trap minimum ratio (seeds 1, 2, 3) | 0.919, 0.920, 0.923 | 0.724, 0.537, 0.551 |
| Per-frame relative standard deviation | at most 0.17 percent | 24 to 29 percent |

The paper reports above 0.70 for LPI on hardware; the test's LPI scores lower under DinHot's transient model, so the two numbers are not the same measurement. The M16 sequence (an LPI) scores 0.870 median
[0.748, 0.963] on its own 7 by 7 to 3 by 3 sort under its frame-position measure, which also differs. Outcome: confirmed within the model.

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C10 only, a rearrangement, with its optics in `data/derived/manifests/C10_rearrangement.json`;
the table shows B2's final hologram as the bake scores it):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C10 | 13 | 0.797 (0.793 to 0.8) | 1 (0.999 to 1) | 0.0103 (5.95e-14 to 0.0309) |

The case driver (`data-pipeline/pipeline/stages/rearrangement.py`) records a case-level `min_transient` of 0.958 to 0.985 over the 3 seeds, the lowest moving-trap intensity relative to the mean over the moving
frames; the measured file does not name the method of that driver, so it is not claimed for B2.

## Limits and failure modes

- The transient model is DinHot's (UNVERIFIED); the comparison is against DinHot's implementation of LPI, not the authors' code, and without a measured flicker curve the benefit is simulation only.
- The SLM temporal response (liquid-crystal relaxation) and the refresh rate are not modelled.
- Phase velocity is bounded by hand (0.3 rad per frame); a trajectory needing more raises a `ValueError`.
- The phases are held by default; the case of changing end phases is bounded but tested only for the bound.
- A comparison against independent weighted GS per step was dropped in the M16 work: with 9 traps the weighted GS equalizes every step and shows no flicker (median 0.96), unlike the 11 kHz camera observation of the paper.

## References

- Linear phase interpolation, https://arxiv.org/abs/2501.01391
- Kim, Kim, Lee and Ahn 2019, Opt. Lett. 44, 3178, https://doi.org/10.1364/OL.44.003178 (the phase-fixed WGS)
- Lee, Kim and Ahn 2017, Phys. Rev. A 95, 053424, https://doi.org/10.1103/PhysRevA.95.053424 (the assignment of the sort)

## Update after the corrections of 2026-10-29

Measured scope, with one assignment shared by B2 and linear phase interpolation (LPI) and the transient model of the acceptance test: the claim holds when the peak step per frame is at most 0.2 Fourier units (`b2_flicker_bounded.frames_for_move`). Acceptance task (moves of 4 bins, 13 frames, seeds 1 to 3): B2 0.916 to 0.926 of the mean, LPI 0.551 to 0.709. C10's long sort (17 moving traps, the longest 29 bins, seeds 1 to 6): at 25 frames LPI leads in every seed (0.514 to 0.588 against 0.328 to 0.418); B2 needs the end phases and 137 frames to reach 0.899 to 0.919 (median 0.905, 5 of 6 seeds at least 0.9), where LPI reaches 0.678 to 0.756; with held phases B2 collapses to 0. Long moves of the acceptance lattice (two columns moved 12 or 20 bins, 8 seeds, the frames of `frames_for_move`): median 0.933 and 0.936, 6 of 8 seeds at least 0.9; the seeds below stay below with twice the frames, so the limit there is the phase path that the end phases prescribe, not the frame count (`tests/methods/beyond/test_b2_flicker_bounded.py::test_long_moves_meet_the_claim_on_most_seeds_with_the_frames_of_the_move`). Measured 2026-10-29 after the GS family of the beyond methods was made the ladder methods' own rules (M06 and M07 project the start's field unweighted, as slmsuite does). The transient model is not verified in absolute terms.
