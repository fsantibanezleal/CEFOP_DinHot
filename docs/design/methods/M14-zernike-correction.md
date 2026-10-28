# M14: Zernike correction and sensorless modal recovery

| Item | Value |
|---|---|
| Ladder row | M14, tier classical (SDD, Method ladder) |
| Family, lane | aberration control, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/control/m14_zernike.py` (`SPEC` line 42, `MODES` line 45, `run` line 60); basis in `data-pipeline/pipeline/model/holo/core/zernike.py` |
| Gate | `tests/methods/control/test_m14_zernike.py` |
| Live port | `frontend/src/engine/holo/methods/control.ts` (`m14`, line 115) |
| Card | [M14](../../frameworks/M14_zernike-correction.md); physics component [P03](../../frameworks/P03_zernike.md) |

## Tier and role

The established practice of removing the optical system's aberration from a tweezer array: the aberration phase is added to the final
SLM phase, so a correction is the opposite wavefront added to the hologram. It is a classical baseline for two reasons: the additive
model with a Zernike set is the one of the large-array experiments (Nogrette et al. 2014, https://arxiv.org/abs/1402.5329; Ebadi et al.
2021, https://arxiv.org/abs/2012.12281), and a global Zernike set is exactly what BS-4 improves on (a hologram that is robust to what
the global set leaves). The sensorless search (no wavefront sensor, only the camera) is DinHot's implementation of a merit-function
modal search; no primary source for the parabola search was opened (not established).

## Problem it answers

Given the unknown wavefront $2\pi\sum_j c_j Z_j$ that the optics add to the displayed phase, recover the coefficients from the camera
alone, and display the hologram with the opposite wavefront added.

## Inputs and outputs

- Inputs: `setup`, a `Target` of kind `traps`, `budget` (`iterations` counts sweeps), `rng`, optional `init` (a base hologram), `mode`
  (`recover` or `correct`), `injected` (the system's coefficients in waves, Noll order, at most 21), `known` (for `correct`),
  `camera` (an `EmulatedCamera`), `modes`, `trial_waves`, `base_iterations`. `mode='correct'` without `known` raises a `ValueError`;
  modes must be distinct Noll indices in 1 to 21; coefficients must be finite.
- Output: `Result` with `phi` (the displayed phase, wrapped), one `history` entry per sweep (the ideal trap fields of the corrected
  system, plus `coef_rms_error` in waves over the searched modes when `injected` is given), `fields`, and `meta` (`coefficients`, a
  vector of length 21 with zeros outside the searched modes; `base_efficiency`; `uncorrected_efficiency`; `sweeps`; `elapsed_s`).

## The method

The displayed hologram is the base hologram minus the correction, and the focal field includes the system's wavefront:

$$\phi_{shown} = \phi_{base} - 2\pi\sum_j \hat c_j Z_j,\qquad E = \mathcal F\big[A\,e^{\,i(\phi_{shown} + 2\pi\sum_j c_j Z_j)}\big]$$

The base hologram is the weighted GS of M06 with `base_iterations` iterations in the point form (`m14_zernike.py` line 81), or `init`. The
basis is orthonormal over the disc inscribed in the SLM, in waves (`core/zernike.py` module docstring: $Z_n^m = N_n^m R_n^{|m|}\,\{\cos,\sin\}$,
unit rms over the disc, so the rms wavefront error is the root sum of squares of the coefficients).

`mode='correct'`: the `known` coefficients are subtracted, exact when `known` equals `injected` (test to 1e-9).
`mode='recover'` (default): the merit is the summed measured trap intensity $M(\hat c) = \sum_m I_m$ from the emulated camera
(`core/camera.py`, default: ideal gains, no noise, no roll-off, seeded from `rng`, line 112). Under the Marechal approximation
$M \propto \exp[-(2\pi\sigma)^2]$, with $\sigma$ the residual wavefront rms in waves, so $\ln M$ is a parabola in each coefficient
(UNVERIFIED against Noll 1976: the paper was not opened; the approximation is quoted from the physics research record). One sweep
visits the modes of `modes`; for each it evaluates $M$ at $\hat c_j - \delta$, $\hat c_j$, $\hat c_j + \delta$, fits the parabola
to $\ln M$ and moves to its vertex,

$$\text{step} = \delta\,\frac{y_- - y_+}{2\,(y_- - 2 y_0 + y_+)},\quad y = \ln M,\ \text{clipped to } \pm 2\delta$$

(lines 129 to 132), or, when the three points are not concave, to the best of the three (line 134). The modes are not exactly
orthogonal under the Gaussian beam and the off-axis traps, so the sweep repeats, and stops when the largest step of a sweep is below
$10^{-4}$ waves (line 140) or the sweep cap is reached. Tip, tilt and piston (Noll 1 to 3) are excluded: they move the traps or do not
change them. Cost: $3 \times 8 + 1$ camera frames per sweep.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `mode` | `recover` | `m14_zernike.py` line 60 | the sensorless search is the method of the ladder row |
| `modes` | Noll 4 to 11 (`MODES = tuple(range(4, 12))`) | line 45 | defocus, astigmatism, coma, trefoil and primary spherical; the set of the ladder row |
| `trial_waves` $\delta$ | 0.06 | line 61 | DinHot's choice: about the size of the injected modes of the acceptance set (0.06 to 0.12 waves); not tuned against a source |
| `base_iterations` | 30 | line 62 | DinHot's choice: M06 at 30 iterations, the count at which Di Leonardo et al. 2007 report the GSW row |
| step clip | $\pm 2\delta$ | line 132 | guard against a flat parabola |
| stop | largest step below $10^{-4}$ waves | line 140 | numerical |
| camera | `EmulatedCamera(seed=<first draw of rng>, gain_rms=0.0, rolloff=False)` | line 112 | an ideal camera unless one is passed |

## Complexity and lane

Per sweep: 25 camera evaluations, each a focal field by FFT ($O(P\log P)$ with $P = n_{fft}^2$). Lane `live` (`SPEC`, line 42); the
TypeScript port (`control.ts`, line 115) agrees with the Python fixtures to 2.3e-13 (T1 report D2), and in the bake the case C09
(aberrated) runs M14 with the case's aberration as `injected` (`SYSTEM_WAVEFRONT`, `data-pipeline/pipeline/stages/infer.py` line 65).

## Acceptance criterion and gate

Ladder row: recovers an injected set of Noll modes 4 to 11 within 5 percent of their amplitude. Gate
`tests/methods/control/test_m14_zernike.py::test_modal_search_recovers_noll_4_to_11_within_5_percent`: seeds 1 to 3; the injected set
has Noll modes 4 to 11 with random signs and amplitudes 0.06 to 0.12 waves (rms about 0.26 waves, Strehl about 0.07 uncorrected);
`Budget(6)` sweeps on the 10x10 task; every mode's relative error at most 0.05, the unsearched coefficients exactly zero, and the final
efficiency at least 0.98 of the aberration-free base. Companion tests: a known aberration is subtracted exactly, partial knowledge
corrects partially, and recovery with camera noise 1e-4 and gain error 0.05 stays within 10 percent of the injected rms.

## Evaluation that confirms or refutes it

Confirmed if every searched mode is recovered within 5 percent and the efficiency returns to the aberration-free value; refuted if the
merit's Gaussian assumption fails (strong aberrations), which would show as a mode stuck or the efficiency short of 0.98 of the base.
The noise test bounds the other failure: a noisy merit moves the vertex of the parabola.

## Measured result

Acceptance run of 2026-10-28 (E2 report D4 and D5): 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pitch
12.5 um), 3 seeds, 5 sweeps in E2's table (the test allows 6):

| Quantity | Measured | Conditions |
|---|---|---|
| Worst per-mode relative error | 0.0018, 0.0023, 0.0012 | injected Noll 4 to 11, amplitudes 0.06 to 0.12 waves, ideal camera |
| Efficiency after recovery | 1.0000 of the aberration-free base | uncorrected: 0.13 to 0.30 of the base |
| With camera noise 1e-4 and gain error 0.05 | coefficient error under 10 percent of the injected rms | seed 2 |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; case C09 only; the
case has its own optics and aberration, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C09 | 4 | 0.799 (0.786 to 0.805) | 0.994 (0.987 to 0.999) | 0.344 (0.0818 to 0.722) |

## Limits and failure modes

- UNVERIFIED: the Noll ordering beyond $j = 11$ and the signs ($j = 12$ to 21 follow a rule stated in `core/zernike.py` that was not
  checked against Noll 1976).
- The merit assumes a roughly Gaussian response in each coefficient; strong aberrations break it.
- The camera is an emulation; the recovery is shown against stated errors, not an instrument.
- A global set cannot correct aberrations that vary across the field (the gap BS-4 starts from).

## References

- Nogrette et al. 2014, Phys. Rev. X 4, 021034, https://arxiv.org/abs/1402.5329
- Ebadi et al. 2021, https://arxiv.org/abs/2012.12281
- Noll 1976, J. Opt. Soc. Am. 66, 207, https://doi.org/10.1364/JOSA.66.000207 (not opened, UNVERIFIED)
