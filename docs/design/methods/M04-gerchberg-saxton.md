# M04: Gerchberg-Saxton, point-trap and FFT forms

| Item | Value |
|---|---|
| Ladder row | M04, tier classical (SDD, Method ladder) |
| Family, lane | GS, live |
| Targets, dimensions | traps and shaped fields, 2D and 3D |
| Module | `data-pipeline/pipeline/model/holo/methods/baseline/m04_gs.py` (`SPEC` line 19, `run` line 22) on the engine `data-pipeline/pipeline/model/holo/methods/baseline/_gs.py` (`rule_gs` line 71, `run_traps` line 110, `run_field` line 169) |
| Gate | `tests/methods/baseline/test_m04_gs.py` |
| Live port | `frontend/src/engine/holo/methods/baseline.ts` (`m04`, line 98) and `frontend/src/engine/holo/methods/gs.ts` |
| Card | [M04](../../frameworks/M04_gerchberg-saxton.md) |

## Tier and role

The established iterative method of holographic optical tweezers: alternate between the SLM plane and the trap plane, impose the
known amplitudes in each, keep the phase that comes back. It is a baseline for three reasons: it is the workhorse that the
weighted variants (M05 to M07) modify, it is the reference of the learned and optimization methods (M11 is compared with it at equal
iterations), and with a zero noise region it is the baseline that M08 (MRAF) improves for shaped targets. Source: Di Leonardo,
Ianni and Ruocco 2007, Table 1 (https://doi.org/10.1364/OE.15.001913); Gerchberg and Saxton 1972 is the original and its text was
not opened (UNVERIFIED).

## Problem it answers

Efficient (above 0.9 with a flat beam) but not uniform holograms for arrays of traps, and, in its field form, a first hologram for a
shaped target.

## Inputs and outputs

- Inputs: `setup`, `target` of kind `traps` or `field` (an `amplitude` and a boolean signal `mask` on the `n_fft` by `n_fft`
  focal grid), `budget` (an iteration cap, optionally a wall-clock cap), `rng`, optional `init` (a finite starting phase of shape
  `n_pix` by `n_pix`), `form` (`point`, `fft` or `auto`), `start_waves`. `device` is ignored (ideal).
- Output: `Result` with `phi` (radians), `history` (one entry per iteration with `iteration`, `efficiency`, `uniformity`,
  `rel_std`, `time_s`; for a shaped target also `error`), `fields` (trap fields $V_m$, or the focal field of a shaped target) and
  `meta` (`method`, `form`, `iterations`).
- The FFT form needs every trap on an FFT bin (to `ON_BIN_TOL` bins), $z = 0$ and no vortex, and raises a `ValueError` otherwise
  (`_gs.check_on_bins`, line 54); a shaped target needs `form='fft'`.

## The method

With the trap fields $V_m = \frac1N\sum_j A_j e^{i(\phi_j - \Delta_j^m)}$, target amplitudes $a_m = \sqrt{w_m}$ and $\Delta_j^m$ the
delay of M01, one iteration is

$$\phi_j^{k} = \arg \sum_m a_m\,\frac{V_m^{k-1}}{|V_m^{k-1}|}\;e^{+i\Delta_j^m}$$

(Di Leonardo et al. 2007, Table 1; the phasor $V/|V|$ is 1 where $V = 0$, `_common.phasor`, line 121). The start is the SR hologram of
M02 (`start_phase`, `_common.py` line 48) unless `init` is given. In the code the rule is `rule_gs` (`_gs.py` line 71,
`c_m = a_m phasor(V_m)`), the loop `run_traps` back-projects the coefficients and keeps the phase.

Two forms of the same map. The point form is the direct sum of `core/forward.py`. The FFT form places the constraint on the bins of
the zero-padded transform: $\phi \leftarrow \arg\,\mathcal F^{-1}\big[\sum_m c_m\,\delta(\mathbf u - \mathbf u_m)\big]$
(`fft_backproject`, `_common.py` line 64). They are the same linear map up to a scale for traps on bins, so they agree to rounding.
`form='auto'` takes the FFT form when every trap is on a bin with $z = 0$ and charge 0 and the point form otherwise
(`resolve_form`, `_gs.py` line 46), and records the choice in `meta['form']`.

Shaped targets (the baseline of M08): `run_field` (line 357) iterates the same projection with the mixed-region rule of Pasienski and
DeMarco 2008, Eq. (1), at mixing $m = 1$, i.e. a zero noise region,
$G = \{T|_{SR} + 0\cdot|E|\,|_{NR}\}\,e^{i\arg E}$, then $\phi = \arg\mathcal F^{-1}G$ with the SLM amplitude reset to the beam
(`_gs.py` lines 196 and 197). The target $T$ is rescaled to the input power, $\sum T^2 = N_{pix}$ in the signal region (line 185).

## Defaults

| Parameter | Default | Where | Source of the value |
|---|---|---|---|
| `form` | `None`: `fft` for a shaped target, `auto` for traps | `m04_gs.py` lines 24 and 25; `AUTO` in `_gs.py` line 29 | engineering choice; the forms agree on bins (test) |
| `start_waves` | `20.0` (`_gs.START_WAVES`, `_gs.py` line 166) | `m04_gs.py` line 23 | DinHot's choice for the shaped start: a Fresnel-lens phase of 20 waves at the aperture edge, because a random start leaves speckle (see M08); the original text states no start (UNVERIFIED) |
| `ON_BIN_TOL` | 2e-3 bins | `_gs.py` line 30 | case coordinates are rounded to 1e-4 um (code comment) |
| start for traps | SR hologram (M02) | `_common.py` line 48 | Di Leonardo et al. 2007 |

The port's default form for traps is `point` (`frontend/src/engine/holo/methods/baseline.ts` line 100), where the Python default is `auto`; the two are identical on bins, the port does not choose the FFT form on its own for M04.

## Complexity and lane

Cost $K \times M \times N$ for the point form (Di Leonardo et al. 2007, Table 1) and $O(P\log P)$ per iteration for the FFT form with
$P = n_{fft}^2$. Lane `live`. Parity: worst observed difference of M04 against the Python fixtures 7.1e-14 (T1 report D2), tolerance
1e-9 rad. The SDD (section Lanes) records a weighted-GS iteration at the live grid (256 by 256 padded 2) of about 24 ms in Node 24.

## Acceptance criterion and gate

Ladder row: the two forms agree to 1e-9 rad; 30 iterations on the 10x10 task with a flat beam reach efficiency at least 0.9 and
uniformity near 0.6. Gate `tests/methods/baseline/test_m04_gs.py`:

- `::test_two_forms_agree_on_a_2d_on_bin_grid`: 8 iterations, seed 5, forms `point` and `fft`; the test asserts a wrapped phase
  difference below 1e-6 rad and the history differences below 1e-9 (the ladder text says 1e-9 rad; the measurement, 6e-13 rad, meets
  both);
- `::test_acceptance_10x10_30_iterations_flat_beam`: seeds of the test, 30 iterations, a flat beam; $e \ge 0.9$ and $0.4 < u < 0.8$;
- `::test_acceptance_10x10_30_iterations_gaussian_beam`: with the Gaussian beam of the core default, $e \ge 0.9$ of the metric ceiling
  $(\overline{A})^2$ (0.869 at the test setup), the same uniformity band.

## Evaluation that confirms or refutes it

Confirmed if the engine reproduces the published GS row (efficiency 0.94, uniformity 0.60, relative standard deviation 17 percent at
30 iterations) and if the two forms are one map. It is refuted if the forms differ beyond rounding or if the flat-beam efficiency
falls under 0.9. The beam matters: the efficiency of a Gaussian beam is capped by $(\overline{A})^2$, so the bar of 0.9 holds only for a
flat beam (E2 report, summary item 2), which is why the ladder row names the flat beam.

## Measured result

Acceptance run of 2026-10-28 (E2 report D2 and D5), 10x10 task 8 bins apart, 256 by 256 padded 2, test setup (850 nm, focal length
250 mm, pitch 12.5 um), 30 iterations, 3 seeds, median with the range:

| Beam | Efficiency | Uniformity |
|---|---|---|
| Flat | 0.939 [0.933, 0.939] | 0.604 [0.557, 0.626] |
| Gaussian (waist fraction 1) | 0.815, which is 0.937 of the ceiling 0.869 | within 0.4 to 0.8 (the test bound) |

The forms agree to 6e-13 rad (8 iterations). Published: 0.94 and 0.60. Further, E3's in-test copy of the same rule gives a relative
standard deviation of 17.79, 17.98 and 18.82 percent over seeds 1 to 3 at 30 iterations (E3 report D5, the baseline of M11).

Committed canonical bake (`data-pipeline/pipeline/cases/measured_ranges.json`, mean over 3 seeds with the range; each case has its
own optics, listed in `data/derived/manifests/`; the C04 row is the shaped disc scored on the case's crosstalk device):

| Case | Iterations | Efficiency | Uniformity | Relative standard deviation (percent) |
|---|---|---|---|---|
| C01 | 30 | 0.796 (0.779 to 0.819) | 0.748 (0.672 to 0.879) | 17.2 (7.34 to 23.7) |
| C02 | 30 | 0.817 (0.812 to 0.819) | 0.568 (0.488 to 0.625) | 17.3 (16 to 19.5) |
| C03 | 30 | 0.818 (0.817 to 0.819) | 0.492 (0.455 to 0.52) | 17.8 (17.1 to 18.7) |
| C05 | 30 | 0.908 (0.895 to 0.918) | 0.611 (0.575 to 0.643) | 19.3 (16.8 to 22.4) |
| C06 | 30 | 0.707 (0.703 to 0.71) | 0.86 (0.856 to 0.861) | 8.23 (7.33 to 9.29) |
| C07 | 30 | 0.811 (0.807 to 0.814) | 0.648 (0.585 to 0.746) | 18.2 (13.4 to 22.5) |
| C08 | 30 | 0.698 (0.692 to 0.703) | 0.464 (0.373 to 0.539) | 24.3 (21.6 to 28) |
| C09 | 30 | 0.457 (0.455 to 0.458) | 0.734 (0.727 to 0.739) | 15.3 (15 to 15.7) |
| C12 | 30 | 0.817 (0.812 to 0.821) | 0.575 (0.506 to 0.64) | 18.5 (16.4 to 20) |
| C13 | 30 | 0.742 (0.74 to 0.743) | 0.645 (0.64 to 0.652) | 11 (10.6 to 11.2) |
| C14 | 30 | 0.797 (0.795 to 0.799) | 0.656 (0.608 to 0.701) | 16.9 (15.3 to 18.4) |

| Case | Iterations | Signal-region power fraction | Signal rms error (percent) |
|---|---|---|---|
| C04 | 30 | 0.926 (0.926 to 0.926) | 44.9 (44.9 to 44.9) |

## Limits and failure modes

- Uniformity stalls near 0.6: GS does not control the trap intensities; the weighted variants M05 to M07 do.
- The efficiency of a Gaussian beam is capped by $(\overline{A})^2$.
- Stagnation in local minima and ghost traps; a shaped target leaves speckle in the signal region (the reason for M08).
- The FFT form refuses off-bin traps, 3D traps and vortices.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
- Gerchberg and Saxton 1972 (original text not opened, UNVERIFIED)
- Pasienski and DeMarco 2008, Opt. Express 16, 2176, https://doi.org/10.1364/OE.16.002176 (the field form)
