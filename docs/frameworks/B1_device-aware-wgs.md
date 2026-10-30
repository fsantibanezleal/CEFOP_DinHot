# B1, Device-aware weighted GS (beyond the published state of the art)

| Item | Value |
|---|---|
| Family | beyond, device-aware |
| Lane | baked (`SPEC.lane`) |
| Targets, dimensions | traps, 2D |
| Module and entrypoint | `data-pipeline/pipeline/model/holo/methods/beyond/b1_device_wgs.py`, `SPEC` line 45, `run` line 52 |
| Gap | the crosstalk model has been used only with conjugate gradient on shaped potentials |

## Purpose

Put the SLM's pixel crosstalk and quantizer inside the weighted GS loop for trap arrays, so the traps are equal on the device and not only
in the ideal model.

## The gap

Schroff et al. 2023 put the crosstalk model into conjugate gradient on shaped potentials (10 minutes per hologram, no WGS comparison),
https://doi.org/10.1038/s41598-023-30296-6 ; Persson, Engstrom and Goksor 2012 convolve the phase inside a weighted GS but replace
amplitudes only, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334 ; Kim et al. 2019 and Ebadi et al. 2021 use no device model in the solver
and rely on camera feedback.

## Method

Keep the weights of Di Leonardo et al. 2007, Eq. (18), $w_m \leftarrow w_m\langle r\rangle/r_m$ with $r_m = |V_m|/a_m$ the trap amplitude relative to its design
amplitude, measured on the device's focal field. Replace the projection of the phase update by $K$ conjugate-gradient steps on the device-aware loss

$$L(\phi) = \frac{\sum_m\big(|V_m(\phi)|^2 - T_m\big)^2}{\sum_m T_m^2}, \qquad T_m = \eta\,\frac{(w_ma_m)^2}{\sum_k(w_ka_k)^2}, \qquad \eta = \sum_m|V_m|^2$$

where $V = \mathrm{Op}(\phi)$ runs through the straight-through quantizer, the crosstalk operator $K*U$ (3 by 3 upsampling, circular convolution with the Schroff kernel),
the FFT of the upsampled grid and the pixel-aperture envelope ([P02](P02_device-model.md)). The gradient is the closed form of the crosstalk adjoint, so the TypeScript
port needs no automatic differentiation. The target level is the current efficiency $\eta$, so the steps flatten the traps without trading efficiency away; the
weights supply the integral feedback that the few steps per iteration lack. Fletcher-Reeves CG with a strong-Wolfe line search restarts at every outer iteration, because
the target changes with the weights.

## Implementation

Defaults (`b1_device_wgs.py`, lines 47 to 49): `steps = 3` CG steps per outer iteration, `warm = 12` ideal-model GSW iterations from the SR superposition (Kim's $N$), 4
outer iterations. Reading the traps off the device's focal field uses the nearest FFT bin (traps on bins, $z = 0$, no vortex). `init` overrides the warm start.

## Acceptance criterion and test

On the crosstalk device, relative standard deviation at least two times below M07, efficiency at most 10 percent lower:
`tests/methods/beyond/test_b1_device_wgs.py::test_acceptance_two_times_lower_rel_std_than_phase_fixed_wgs_on_the_crosstalk_device`.

## Measured values (seed 1 of the claim's measurement, 2026-10-30)

| Quantity | B1 | M07 on the ideal model, scored on the device | Conditions |
|---|---|---|---|
| Relative standard deviation (percent) | 0.298 | 4.745 (30 iterations) and 4.746 (100 iterations) | 1 seed, 10 by 10 task on 256 by 256 padded 2 |
| Efficiency | 0.7452 | 0.7471 | same |
| Ratio | 15.9 times lower spread on this seed, 0.997 of the efficiency; a median of 25.8 times (15.9 to 33.3) over five seeds; B1's benchmark cells on the C08 device hold 2 seeds (M07's 20) | | |

More iterations do not help the baseline (spread 4.745 with 30 iterations and 4.746 with 100, seed 1). The criterion is exceeded by a wide margin; the benchmark
repeats the comparison on its geometries on the C08 device, where B1's cells hold 2 seeds (M07's 20).

## Limits

- UNVERIFIED: the unit of $k$ in the crosstalk kernel ([P02](P02_device-model.md)); the claim is relative to the model of the device, not to a measured instrument.
- Cost per CG step is about 3 by 3 times the pixels of the plain FFT; baked.
- B1 returns its best iterate that keeps 0.9 of its warm start's efficiency (2026-10-30): its weight update can wind up on a device the
  few gradient steps cannot fit, and without the safeguard one seed in two did on the benchmark's square lattice on the C08 device.
- Scope measured by the benchmark on the C08 device (design record, update of 2026-10-30): the claim holds on the ring and the random set,
  B1 lowers the spread by less than two times on the large set, and keeps its start on the square and quasi-periodic lattices.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, https://doi.org/10.1038/s41598-023-30296-6
- Persson, Engstrom and Goksor 2012, Opt. Express 20, 22334, https://opg.optica.org/oe/fulltext.cfm?uri=oe-20-20-22334
- Kim et al. 2019, https://doi.org/10.1364/OL.44.003178 ; Di Leonardo et al. 2007, https://doi.org/10.1364/OE.15.001913
