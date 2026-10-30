# M05: Generalized adaptive additive GS (GAA)

| Item | Value |
|---|---|
| Ladder row | M05, tier classical (SDD, Method ladder) |
| Family, lane | GS, live |
| Targets, dimensions | traps, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m05_gaa.py` (`SPEC` line 22, `run` line 26) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` (`rule_gaa`, line 75) |
| Gate | `tests/methods/baseline/test_m05_gaa.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m05`, line 109) and `frontend/src/engine/holo/methods/gs.ts` (`ruleGaa`, line 82) |
| Card | [M05](../../frameworks/M05_gaa.md) |

## Tier and role

The established adaptive variant of Gerchberg-Saxton: a feedback that raises the weak traps, by dividing the field of every trap
by a power of its own amplitude before it is sent back. It is a baseline because it is the first published remedy of GS's poor
uniformity (it trades a little efficiency for uniformity) and the rung between GS (M04) and the weighted GS (M06). Source: Di
Leonardo, Ianni and Ruocco 2007, Eqs. (15) and (16) (https://doi.org/10.1364/OE.15.001913). The original adaptive-additive
algorithm of Soifer, Kotlyar and Doskolovich was not opened (UNVERIFIED).

## Problem it answers

A better uniformity than GS at nearly the same efficiency, with one parameter $\alpha$ and no extra state.

## Inputs and outputs

Inputs as M04 for trap targets (`form`, `init`, `budget`, `rng`) plus `alpha` in $[0, 1]$ and `scale` (`mean` or `absolute`); a shaped
target is refused naming `traps`. Output: `Result` with `phi`, one `history` entry per iteration, `fields` and
`meta` (`alpha`, `scale`, `form`, `iterations`). `alpha` outside $[0, 1]$ or an unknown `scale` raise a `ValueError`.

## The method

GAA maximizes $(1-\alpha)\sum_m |V_m| + \alpha\sum_m \log|V_m|$; the stationarity condition, iterated, gives (Di Leonardo et al. 2007,
Eqs. (15), (16))

$$\phi_j = \arg \sum_m e^{+i\Delta_j^m}\,\frac{V_m}{|V_m|}\Big[(1-\alpha) + \frac{\alpha}{|V_m|}\Big].$$

With target weights $V_m/|V_m|$ is scaled by $a_m = \sqrt{w_m}$ and $|V_m|$ becomes $r_m = |V_m|/a_m$. $\alpha = 0$ is GS (test
`::test_alpha_zero_is_gs`). The code (`rule_gaa`, `_gs.py` lines 75 to 85) is $c_m = a_m\,V_m/|V_m|\,\big[(1-\alpha) + \alpha/\tilde r_m\big]$ with
$\tilde r_m = r_m/\langle r\rangle$ for `scale='mean'` and $\tilde r_m = r_m$ for `scale='absolute'`.

Deviation from the printed formula, stated in the module docstring: the bracket as printed depends on the absolute scale of
$|V_m|$ (fractions of the input power, about 0.1 on the 10x10 task), so $\alpha/|V_m|$ dominates and the iteration oscillates
(uniformity 0.04 to 0.4, below GS, measured). Expressing $|V_m|$ in units of its mean over the traps (`scale='mean'`) reproduces the
published trend. UNVERIFIED: the bracket was reconstructed in the gap study against Eq. (15) because the Greek glyphs of Eq. (16) were
lost in the text extraction.

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `alpha` | 0.5 | `m05_gaa.py` line 26 | the value of Di Leonardo et al. 2007 (efficiency 0.93, uniformity 0.79 at 30 iterations) |
| `scale` | `mean` | `m05_gaa.py` line 27 | DinHot's reading: it makes the iteration scale free (measured: `absolute` gives uniformity 0.250, below GS) |
| `form` | `auto` | `m05_gaa.py` line 27 | the FFT form on bins, else the point form (I1 report F1) |

The port's default form is `point` (`frontend/src/engine/holo/methods/baseline.ts` line 115), identical on bins. The benchmark
tuning grid for M05 is `alpha` in (0.25, 0.5, 0.75, 1.0) (`FALLBACK_TUNING`, `data-pipeline/pipeline/benchmark/protocol.py` line 54).

## Complexity and lane

Cost $K \times M \times N$ (point form), the same as GS. Lane `live`; parity worst difference 7.1e-14 (T1 report D2).

## Acceptance criterion and gate

Ladder row: uniformity above GS at equal iterations on the 10x10 task. Gate
`tests/methods/baseline/test_m05_gaa.py::test_uniformity_above_gs_at_equal_iterations`: 5 seeds, 30 iterations each for M04 and
M05 on the 256 by 256 padded-2 grid; per seed $u_{GAA} > u_{GS}$, the median of $u$ at least 0.05 above GS, and the efficiency above
0.95 of GS's. Companion tests: `alpha = 0` is GS, the defaults are 0.5 and deterministic, and the printed absolute bracket runs and
differs.

## Evaluation that confirms or refutes it

Confirmed by uniformity above GS in every seed at equal iterations and efficiency within 5 percent of GS. Refuted if any seed has
GAA below GS (which is what the bracket as printed does). The test fixes the reading of the formula: with `scale='absolute'` the
acceptance would fail.

## Measured result

Acceptance run of 2026-10-28 (E2 report D2 and D5): 10x10 task 8 bins apart, 256 by 256 padded 2, test setup (850 nm, focal length 250
mm, pitch 12.5 um, Gaussian beam), 30 iterations, 5 seeds, median with the range:

| Quantity | GAA (`scale='mean'`) | GS (M04) |
|---|---|---|
| Uniformity | 0.688 [0.638, 0.709] | 0.615 [0.550, 0.637] |
| Efficiency | 0.811 | 0.816 |

GAA is above GS in every seed. With the bracket as printed (`scale='absolute'`): uniformity 0.250 [0.044, 0.439], below GS.
Published at 30 iterations: efficiency 0.93, uniformity 0.79 (a flat beam; the efficiency level here is lower because the test beam is
Gaussian).

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.807 (0.784 to 0.819) | 0.873 (0.776 to 0.932) | 8.6 (3.86 to 16.6) |
| C02 | 30 | 0.814 (0.812 to 0.818) | 0.716 (0.695 to 0.742) | 12.9 (11.9 to 14.5) |
| C07 | 30 | 0.802 (0.799 to 0.804) | 0.725 (0.661 to 0.772) | 14.1 (12.8 to 16.6) |
| C12 | 30 | 0.813 (0.805 to 0.818) | 0.696 (0.637 to 0.738) | 12.6 (11.8 to 13.8) |

## Limits and failure modes

The scale convention is DinHot's reading of an unverified reconstruction. GAA stays below the weighted methods M06 and M07 in
uniformity (in the bake, uniformity 0.64 to 0.93 against 0.95 to 1.0 for M06 on C01, C02 and C12). It has no integral memory of earlier
corrections, unlike the weights of M06.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
