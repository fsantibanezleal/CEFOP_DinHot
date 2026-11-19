# B1, Device-aware conjugate-gradient refinement (beyond the published state of the art; named device-aware weighted GS until 0.02.003)

| Item | Value |
|---|---|
| Family | beyond, device-aware |
| Lane | baked (`SPEC.lane`) |
| Targets, dimensions | traps, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/beyond/b1_device_wgs.py`, `SPEC` line 45, `run` line 52 |
| Gap | none left: the crosstalk model inside a conjugate-gradient refinement, with a spot array made by it, is Schroff et al. 2023 (their Fig. 5c); the method is a transposition of it to trap arrays |

## Purpose

Put the SLM's pixel crosstalk and quantizer inside a conjugate-gradient refinement that starts from weighted GS, for trap arrays, so the traps are equal on the device and not only
in the ideal model. Result of the 0.02.004 measurement: a negative result against Schroff et al. 2023. The gain belongs to the device model in the loop, which they already use; the
method's own elements (the efficiency-level loss, the weight update and the best-iterate safeguard) add nothing measurable over their normalized-error loss.

## The gap

Schroff et al. 2023 put the crosstalk model (3 by 3 upsampling, a fitted kernel) into a conjugate-gradient minimization of a normalized intensity error, with automatic differentiation and
camera feedback, and generate light potentials with it, among them a Gaussian spot array (their Fig. 5c), at about 10 minutes per feedback protocol and with no WGS comparison,
https://doi.org/10.1038/s41598-023-30296-6 . The idea of a crosstalk model inside a conjugate-gradient refinement of a trap array is therefore theirs. Persson, Engstrom and Goksor 2012
modify a hologram algorithm for crosstalk (known here through its abstract only), https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334 ; Kim et al. 2019 and Ebadi et al. 2021 use no
device model in the solver and rely on camera feedback. The method is a transposition of the approach of Schroff et al. to point-trap arrays with three elements of its own: the
efficiency-level loss, the weight update and the best-iterate safeguard.

## Method

Start from weighted GS. The weights of Di Leonardo et al. 2007, Eq. (18), $w_m \leftarrow w_m\langle r\rangle/r_m$ with $r_m = |V_m|/a_m$ the trap amplitude relative to its design
amplitude, measured on the device's focal field, are an option (`weights=True`), off by default since 0.02.004: the ablation of the paper gives a spread 7 times lower on the acceptance task (0.030 against 0.205 percent) and 3 times lower on the full device (0.242 against 0.729 percent) without them. Replace the projection of the phase update by $K$ conjugate-gradient steps on the device-aware loss

$$L(\phi) = \frac{\sum_m\big(|V_m(\phi)|^2 - T_m\big)^2}{\sum_m T_m^2}, \qquad T_m = \eta\,\frac{(w_ma_m)^2}{\sum_k(w_ka_k)^2}, \qquad \eta = \sum_m|V_m|^2$$

where $V = \mathrm{Op}(\phi)$ runs through the straight-through quantizer, the crosstalk operator $K*U$ (3 by 3 upsampling, circular convolution with the Schroff kernel),
the FFT of the upsampled grid and the pixel-aperture envelope ([P02](P02_device-model.md)). The gradient is the closed form of the crosstalk adjoint, so the TypeScript
port needs no automatic differentiation. The target level is the current efficiency $\eta$, so the steps flatten the traps without trading efficiency away; with the
weights on they supply an integral feedback that the few steps per iteration lack. Fletcher-Reeves CG with a strong-Wolfe line search restarts at every outer iteration, because
the target is set again at each of them. The option `loss='normalized-error'` runs the normalized-error cost of Schroff et al. 2023, eq (3), through the same operator, start, optimizer and safeguard, so the closest published loss is a baseline of the method itself.

## Implementation

Defaults (`b1_device_wgs.py`, lines 47 to 49): `steps = 3` CG steps per outer iteration, `warm = 12` ideal-model GSW iterations from the SR superposition (Kim's $N$), 4
outer iterations. Reading the traps off the device's focal field uses the nearest FFT bin (traps on bins, $z = 0$, no vortex). `init` overrides the warm start.

## Acceptance criterion and test

On the crosstalk device, relative standard deviation at least two times below M07, efficiency at most 10 percent lower:
`tests/methods/beyond/test_b1_device_wgs.py::test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device`.

## Measured values (release 0.02.004, `manuscripts/device-aware-refinement/data/beyond_numbers.tex`, `tab_schroff.tex`, `tab_abl_b1_geo.tex`)

10 by 10 task on 256 by 256 padded 2, 850 nm, focal length 250 mm, pitch 12.5 um, 5 seeds, simulated:

| Quantity | Device-aware refinement | Comparison | Conditions |
|---|---|---|---|
| Relative standard deviation, median (percent), crosstalk device | 0.030 (0.016 to 0.032) | phase-fixed WGS (M07) 5.21 at 30 and at 100 iterations | the baseline is no better at 100 iterations than at 30 |
| Factor over M07, geometric mean (95 percent interval) | 201.3 (132.9 to 304.9) | | efficiency ratio 0.999, smallest 0.996 |
| Same refinement without the device model in the loop | 5.15 | | the gain disappears: it belongs to the device model |
| Normalized-error loss of Schroff et al. through the same warm start, device model and optimizer | 0.031 (0.021 to 0.049); factor 159.9 (107.0 to 239.1) | efficiency-level loss 0.030 | indistinguishable at 5 seeds; the safeguard did not act |
| Full device (4-bit phase, fill factor 0.85) | efficiency-level 0.242, factor 23.5 (18.6 to 29.6); Schroff loss 0.222, factor 26.1 (20.2 to 33.9) | M07 5.85 | the normalized-error loss has the lower median |
| Weight update on | 0.205 on the crosstalk device and 0.729 on the full device | off: 0.030 and 0.242 | the update makes the spread 7 and 3 times higher |
| Time per hologram, median | 34 s on the acceptance task, 99 to 399 s on the benchmark geometries at 10 outer iterations | M07 0.74 s at 30 iterations and 2.42 s at 100; 0.05 to 0.99 s on the benchmark geometries | one CPU, other jobs also running: orders of magnitude |

Benchmark geometries on the C08 device (flicker), 100 iterations, 2 seeds per cell for the refinement: factors over M07 of G1 1.90, G2 2.04, G3 4.82, G4 1.05, G6a 2.15 and G6b 2.08; both
thresholds are met on the ring, the random set and the two large sets, not on the square lattice or the quasi-periodic set. At an equal wall-clock time of 1 s the refinement reads as better on 3 of 6 geometries
(the square lattice, the ring and the random set), ties on 3 and M07 wins on none.

## Limits

- The unit of $k$ in the crosstalk kernel is DinHot's reading ([P02](P02_device-model.md)); the claim is relative to the model of the device, not to a measured instrument.
- Cost per CG step is about 3 by 3 times the pixels of the plain FFT; baked.
- B1 returns its best iterate that keeps 0.9 of its warm start's efficiency (2026-10-30); in the comparisons of the 0.02.004 paper the safeguard did not act, so it adds nothing measurable.
- Scope measured by the benchmark on the C08 device (design record, update of 2026-11-15): both thresholds are met on the ring, the random set and the two large sets, not on the square lattice or the quasi-periodic set.
- The normalized-error loss is DinHot's implementation of the loss of Schroff et al. on point traps with a closed-form gradient: it is not their code, their automatic differentiation or their camera feedback.
- Every figure is simulated; the effect on a camera-corrected experiment or on atom survival is not measured.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, https://doi.org/10.1038/s41598-023-30296-6
- Persson, Engstrom and Goksor 2012, Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334
- Kim et al. 2019, https://doi.org/10.1364/OL.44.003178 ; Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913
