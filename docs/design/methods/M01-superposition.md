# M01: Superposition of prisms and lenses

| Item | Value |
|---|---|
| Ladder row | M01, tier classical (SDD, Method ladder) |
| Family, lane | analytic, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m01_superposition.py` (`SPEC` line 20, `run` line 24) |
| Gate | `tests/methods/baseline/test_m01_superposition.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m01`, line 24), parity in `frontend/src/engine/holo/methods.parity.test.ts` |
| Card | [M01](../../frameworks/M01_superposition.md) |

## Tier and role

The established analytic method: the hologram of $M$ traps is the sum of the single-trap holograms, a prism for each lateral
offset, a lens for each axial offset and a spiral for each vortex charge, with the phase of the sum kept. It is a baseline of the
ladder for two reasons: it is the oldest and cheapest rung (no iteration, cost $N \times M$), and it is the reference that every
other method has to beat on efficiency or uniformity. The source is Di Leonardo, Ianni and Ruocco 2007, Table 1
(https://doi.org/10.1364/OE.15.001913), the row "S".

## Problem it answers

Produce a phase-only hologram for a set of point traps in one pass, with no feedback and no random numbers. It answers "what does
the plain sum of the single-trap holograms give", which is the zero point against which an iterative or optimized hologram is
measured.

## Inputs and outputs

- Input `setup`: the optical setup of `core/geometry.py` (wavelength, focal length, pitch, `n_pix`, `pad`, beam). Input `target`:
  a `Target` of kind `traps` (a `TrapSet` of positions in metres, an optional $z$, an optional vortex charge and a weight). A
  shaped-field target is refused with a `ValueError` that names the supported kind (the missing-data rule shared by every
  trap-only method, `_common.require_kinds`, `data-pipeline/pipeline/model/holo/methods/baseline/_common.py` line 25).
- `device` is accepted and ignored (the ideal device). `rng` is unused (the result is identical for every seed). `init` is ignored.
  `budget` is accepted for the common interface and not consumed (one pass).
- Output: a `Result` whose `phi` is a float64 array of shape `n_pix` by `n_pix` in radians, in $(-\pi, \pi]$ (`np.angle`); `fields`
  are the complex trap fields $V_m$ of the point-trap model; `history` has one entry (the keys `iteration`, `efficiency`,
  `uniformity`, `rel_std`, `time_s` of `core.types.HISTORY_KEYS`); `meta` carries `method`.

## The method

With $\Delta_j^m$ the delay from SLM pixel $j$ at $(x_j, y_j)$ to trap $m$ at $(x_m, y_m, z_m)$ with charge $l_m$
(Di Leonardo et al. 2007, Eqs. (1) to (4); the same form in Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027),

$$\Delta_j^m = \frac{\pi z_m}{\lambda f^2}\,(x_j^2 + y_j^2) + \frac{2\pi}{\lambda f}\,(x_j x_m + y_j y_m) + l_m \operatorname{atan2}(y_j, x_j),$$

the field at a trap and the metrics are

$$V_m = \frac1{N_{pix}}\sum_j A_j\, e^{\,i(\phi_j - \Delta_j^m)},\quad I_m = |V_m|^2,\qquad
e = \sum_m I_m,\quad u = 1 - \frac{\max I - \min I}{\max I + \min I},\quad \sigma = 100\,\frac{\operatorname{std}(I)}{\operatorname{mean}(I)}$$

(`core/forward.py` module docstring; `core/metrics.py` lines 47, 52, 61). The update rule of M01 (Table 1 of the source, with the
target weights $w_m$ of DinHot, all 1 in the source) is

$$\phi_j = \arg \sum_m \sqrt{w_m}\; e^{\,i\Delta_j^m}.$$

The module evaluates the sum with `point_trap_backproject` on the amplitudes $\sqrt{w_m}$ (`m01_superposition.py` line 28) and then
the fields with `point_trap_fields` (line 29). The sum is the adjoint direction $F_j = \sum_m c_m e^{+i\Delta_j^m}$ of the point-trap
projection, so the rule is the first half of one Gerchberg-Saxton step with all trap phases equal to zero.

## Defaults

None. The module has no tunable keyword (`run`, line 24: only the interface arguments). The target weights come from the
`TrapSet`.

## Complexity and lane

Cost $N \times M$ complex terms (Di Leonardo et al. 2007, Table 1), no iteration. Lane `live` (`SPEC`, line 20): the TypeScript port
runs it in the Web Worker; the parity test compares it with fixtures written by the Python engine (worst observed phase difference
for M01: 1.5e-13, T1 report D2; tolerance 1e-9 rad). The benchmark protocol runs it as a one-pass method; its committed rows are the
only method rows already in `data/derived/benchmark/results.json` (63 rows, geometries G1 to G5, method M01 alone, state partial).

## Acceptance criterion and gate

Ladder row: on the 10x10 task with a flat beam, efficiency within 0.10 of 0.29 and uniformity below 0.05. Gate:
`tests/methods/baseline/test_m01_superposition.py::test_acceptance_10x10_matches_published_trend`, which runs M01 on the 10x10 task
(10 by 10 square grid, traps on FFT bins, 8 bins apart) on the 256 by 256 padded-2 grid and asserts the two bounds. Companion tests:
the result is deterministic and independent of the seed, a single-trap hologram is a grating with unit field, and a shaped target is
refused.

## Evaluation that confirms or refutes it

The classical row is confirmed if the plain superposition reproduces the published low efficiency and almost no uniformity, which
fixes the zero point of the ladder; it is refuted if the engine gives a materially higher uniformity or an efficiency outside the
0.10 band, since that would mean the point-trap model differs from the published one. The oracle behind it is the agreement of the
FFT and point-trap forms (`tests/engine/test_forward.py::test_fft_and_point_trap_agree_on_bins`) and the published Table 1 row
(efficiency 0.29, uniformity 0.01, relative standard deviation 257 percent on 768 by 768 pixels, 8 bit).

## Measured result

Acceptance run of 2026-10-28 (E2 report D1 and D5): 10x10 task, 256 by 256 padded 2, test setup (850 nm, focal length 250 mm, pixel
pitch 12.5 um, Gaussian beam of waist fraction 1, `tests/methods/conftest.py` line 18), deterministic (no seed).

| Quantity | Measured | Published (Di Leonardo 2007, Table 1) |
|---|---|---|
| Efficiency | 0.281 | 0.29 |
| Uniformity | 0.0003 | 0.01 |

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; M01 has no random
number, so the three seeds agree; each case has its own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 1 | 0.454 (0.454 to 0.454) | 0.163 (0.163 to 0.163) | 63.8 (63.8 to 63.8) |
| C02 | 1 | 0.281 (0.281 to 0.281) | 0.000279 (0.000279 to 0.000279) | 274 (274 to 274) |
| C03 | 1 | 0.188 (0.188 to 0.188) | 1.05e-07 (1.05e-07 to 1.05e-07) | 925 (925 to 925) |
| C05 | 1 | 0.452 (0.452 to 0.452) | 0.0748 (0.0748 to 0.0748) | 79.4 (79.4 to 79.4) |
| C06 | 1 | 0.594 (0.594 to 0.594) | 0.552 (0.552 to 0.552) | 27.2 (27.2 to 27.2) |
| C07 | 1 | 0.35 (0.35 to 0.35) | 0.0576 (0.0576 to 0.0576) | 116 (116 to 116) |
| C09 | 1 | 0.208 (0.208 to 0.208) | 0.154 (0.154 to 0.154) | 78.4 (78.4 to 78.4) |
| C12 | 1 | 0.328 (0.328 to 0.328) | 0.000275 (0.000275 to 0.000275) | 269 (269 to 269) |
| C13 | 1 | 0.596 (0.596 to 0.596) | 0.357 (0.357 to 0.357) | 24.8 (24.8 to 24.8) |
| C14 | 30 | 0.5 (0.5 to 0.5) | 0.196 (0.196 to 0.196) | 68.9 (68.9 to 68.9) |

## Limits and failure modes

Most of the light goes to the zero order and to spurious interference orders; uniformity is essentially zero on symmetric lattices
(the 10x10 task) and improves only on low-symmetry geometries (C06 and C13 in the bake). It sends energy to ghost traps for
symmetric layouts (Di Leonardo et al. 2007). It is a baseline, not a method for arrays.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Bianchi and Di Leonardo 2010, https://arxiv.org/abs/0907.4027
