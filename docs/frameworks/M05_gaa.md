# M05, Generalized adaptive additive GS (GAA)

| Item | Value |
|---|---|
| Family | GS |
| Lane | live |
| Targets, dimensions | traps, 2D and 3D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/baseline/m05_gaa.py`, `SPEC` line 22, `run` line 26; engine `_gs.py` |
| Anchor | Di Leonardo, Ianni and Ruocco 2007, Eqs. (15) and (16) |

## Purpose

GS with a feedback that raises the weak traps: the field of every trap is divided by a power of its own amplitude before it is
sent back, so a trap that is too dark gets more weight in the next hologram. It trades a little efficiency for a better
uniformity than GS.

## Equations

GAA maximises $(1-\alpha)\sum_m |V_m| + \alpha\sum_m \log|V_m|$; the stationarity condition, iterated, gives

$$\phi_j = \arg \sum_m e^{+i\Delta_j^m}\,\frac{V_m}{|V_m|}\Big[(1-\alpha) + \frac{\alpha}{|V_m|}\Big]$$

(with target weights, $V_m/|V_m|$ is scaled by $a_m = \sqrt{w_m}$ and $|V_m|$ becomes $|V_m|/a_m$). $\alpha = 0$ is GS. Source:
Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913 . UNVERIFIED: the bracket was reconstructed against Eq. (15)
because the Greek glyphs of Eq. (16) were lost in the text extraction, and the original adaptive-additive text of Soifer,
Kotlyar and Doskolovich was not opened. Published at 30 iterations on the 10 by 10 task: efficiency 0.93, uniformity 0.79.

## Implementation

Defaults (`run`, line 26): `alpha = 0.5`, `scale = "mean"`, `form = "point"`.

The bracket as printed depends on the absolute scale of $|V_m|$ (fractions of the input power, about 0.1 on the 10 by 10 task),
so $\alpha/|V_m|$ dominates and the iteration oscillates (uniformity 0.04 to 0.4, below GS, measured). `scale = "mean"` (default)
expresses $|V_m|$ in units of its mean over the traps, which reproduces the published trend; `scale = "absolute"` is the bracket
exactly as printed and stays selectable and tested. This is a deviation from the printed formula, stated in the module docstring.

## Acceptance criterion and test

Uniformity above GS at equal iterations on the 10 by 10 task:
`tests/methods/baseline/test_m05_gaa.py::test_uniformity_above_gs_at_equal_iterations`; `alpha = 0` equals GS
(`::test_alpha_zero_is_gs`).

## Measured values (DinHot measurement, acceptance run of 2026-10-28)

| Quantity | GAA (`scale = "mean"`) | GS | Conditions |
|---|---|---|---|
| Uniformity | 0.688 [0.638, 0.709] | 0.615 [0.550, 0.637] | 5 seeds, 30 iterations, 256 by 256 padded 2, 10 by 10 task |
| Efficiency | 0.811 | 0.816 | same |

GAA is above GS in every seed. With the bracket as printed (`scale = "absolute"`) uniformity is 0.250 [0.044, 0.439], below GS.
Published: 0.93 and 0.79; the efficiency level differs because the test beam is Gaussian.

## Limits

The scale convention is DinHot's reading of an unverified reconstruction. GAA remains below the weighted methods M06 and M07 in
uniformity.

## References

- Di Leonardo, Ianni and Ruocco 2007, Opt. Express 15, 1913, https://doi.org/10.1364/OE.15.001913
