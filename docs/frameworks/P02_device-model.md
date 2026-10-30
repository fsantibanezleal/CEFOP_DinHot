# P02, Device model (the SLM as it is)

Physics component. A real phase-only SLM quantizes the phase, couples neighbouring pixels, covers only part of each pixel
and fluctuates in time. The device model turns an ideal hologram into the phase the device really shows and into the focal
field it really produces.

| Item | Value |
|---|---|
| Module | `data-pipeline/pipeline/model/holo/core/device.py` |
| Tests | `tests/engine/test_device.py` |
| Used by | M13, B1, B4 (as a scorer), the bake of C04 and C08, the benchmark device cells |

## Purpose

Methods that ignore the device lose uniformity when the hologram is displayed on it. This module is the single definition of
the device, shared by the offline scorer and by the device-aware methods.

## Equations

A missing device (`device=None`) is the ideal one: phase displayed exactly, point-sampled pixels, no crosstalk. `Device()` with
its defaults is different on purpose: square pixels of fill factor 1, so the pixel-aperture envelope is present;
quantization, crosstalk, flicker and the LUT nonlinearity are off (`device.py`, line 38).

**Displayed phase** (`displayed_phase`, line 77), in this order: wrap to $[0, 2\pi)$, quantize to $2^b$ levels, nonlinear
response $2\pi\,(\phi_q / 2\pi)^{\gamma}$, additive Gaussian flicker noise of rms `flicker_rad` per pixel, wrap.

**Pixel crosstalk.** Each SLM pixel is $u \times u$ computational pixels (default $u = 3$) and the phase is convolved with

$$K = \mathcal{F}^{-1}\Big\{\exp\!\Big[-\frac{|k_x|^q + |k_y|^q}{\sigma^q}\Big]\Big\}, \qquad \sigma = 1.24,\ q = 1.80$$

(`crosstalk_kernel`, line 99; `crosstalk`, line 119). The fitted values $\sigma = 1.24$ per pixel and $q = 1.80$, on 3 by 3
sub-pixels with an error below 2 percent, are those of Schroff et al. 2023, Methods, "Pixel crosstalk modelling", Eq. (4),
https://doi.org/10.1038/s41598-023-30296-6 . The convolution is circular (FFT based), so the phase wraps at the border of the
SLM. The adjoint (`crosstalk_adjoint`, line 128) is the convolution with the reversed kernel followed by the sum over each
$u \times u$ block; it lets gradient methods differentiate through the device in closed form, with no automatic
differentiation.

**Pixel aperture.** A square pixel of width $a = \sqrt{\text{fill}}\;p$ multiplies the focal field by
$\operatorname{sinc}(a x / \lambda f)\operatorname{sinc}(a y / \lambda f)$, so the intensity falls to about
$\operatorname{sinc}^2(\sqrt{\text{fill}}/2) \approx 0.4$ at the edge of the unaliased window (`pixel_envelope`, line 150).
This is DERIVED in DinHot's research record, not read from a source; the test compares it with a brute-force DFT of a
pixel-sampled hologram. The envelope has unit value at the centre: the power lost to dead area is not applied.

**Device focal field** (`device_focal_field`, line 181). Without crosstalk: the FFT of the displayed phase times the pixel
aperture field envelope. With crosstalk: the hologram is upsampled and blurred, transformed on the finer grid, cropped to the
same window, and the sample-and-hold (Dirichlet) factor is exchanged for the pixel aperture, so the two paths agree exactly
when the kernel is a delta.

**Quantization efficiency.** For a stepped grating with $N$ levels over $2\pi$ the first-order efficiency is
$\eta_1 = \operatorname{sinc}^2(1/N)$: 40.5 percent for $N = 2$, 68.4 percent for $N = 3$, above 91 percent for $N = 6$
(a published result, Moreno et al., postprint, https://tecnopto.umh.es/files/2014/05/Stepped-gratings-with-high-modulation-depth-LCoS-POSTPRINT.pdf ;
journal reference UNVERIFIED). The values for $N = 4, 8, 16$ (0.811, 0.950, 0.987) are computed from that formula, not printed in
the source. For a general hologram the effect also appears as noise in the replica orders, which the engine tests against a
brute-force quantized DFT.

## Implementation

- Entrypoints: `device.Device`, `quantize`, `displayed_phase`, `crosstalk`, `crosstalk_adjoint`, `pixel_envelope`,
  `device_focal_field`.
- Defaults of `Device` (line 38): `bit_depth = None`, `crosstalk = None`, `upsample = 3`, `fill_factor = 1.0`,
  `flicker_rad = 0.0`, `lut_gamma = 1.0`. The case devices: C04 has 8 bits and the crosstalk kernel; C08 has 4 bits, the
  kernel, fill factor 0.85, flicker 0.05 rad (`data-pipeline/pipeline/cases/library.py`, lines 41 to 44).

## Acceptance criterion and test

Gates, all in `tests/engine/test_device.py`: the crosstalk adjoint passes the inner-product identity
$\langle \text{crosstalk}(\phi), g\rangle = \langle \phi, \text{adjoint}(g)\rangle$ to 1e-12 for three devices
(`test_crosstalk_adjoint_inner_product_identity`); the kernel matches its definition (`test_kernel_matches_definition_eq4`);
the blur is the circular convolution with the kernel (`test_crosstalk_is_circular_convolution_with_kernel`); the pixel envelope
matches a brute-force DFT for fill factors 1.0 and 0.64 below 2e-3 (`test_pixel_envelope_against_brute_force_dft`); with a
delta kernel the crosstalk path equals the ideal path to 1e-9
(`test_device_field_crosstalk_path_reduces_to_ideal_without_blur`); efficiency falls monotonically with fewer bits and a binary
grating's first order is $4/\pi^2$ within 10 percent (`test_quantization_costs_efficiency_monotonically`).

## Measured values (DinHot measurements, engine test run of 2026-10-28)

| Quantity | Measured | Conditions |
|---|---|---|
| Adjoint identity | 1e-12 | three devices |
| Pixel envelope against brute-force DFT | below 2e-3 | fill factors 1.0 and 0.64 |
| Crosstalk path with a delta kernel | 1e-9 relative to the ideal path | |

## Limits

- UNVERIFIED: the unit of $k$ in the kernel. The source gives $\sigma = 1.24\ \mathrm{px}^{-1}$ without saying cycles or radians
  per SLM pixel. The implementation takes cycles per SLM pixel (`_transfer`, line 94). If the source means radians, the
  transfer function changes by one factor $2\pi$.
- UNVERIFIED: no primary source with measured effects of quantization, LUT gamma and flicker on a modern nematic SLM was read.
  Flicker is a computed parameter (the one measured device read is a 2008 twisted-nematic LCoS with about 120 degrees of
  fluctuation at one gray level: Lizana et al., https://opg.optica.org/oe/fulltext.cfm?uri=oe-16-21-16711 ); the C08 value of
  0.05 rad is a stated parameter, not a calibrated one.
- The fill factor squared law (87 percent gives 76 percent measured, https://arxiv.org/abs/1512.06241 ) is not applied as a
  power loss.

## References

- Schroff, La Rooij, Haller and Kuhr 2023, Sci. Rep. 13, 3252, https://doi.org/10.1038/s41598-023-30296-6
- Lizana et al. 2008, Opt. Express 16, 16711, https://opg.optica.org/oe/fulltext.cfm?uri=oe-16-21-16711
- Fill factor, "Optical techniques for Rydberg physics in lattice geometries", https://arxiv.org/abs/1512.06241
- Moreno et al., stepped gratings, https://tecnopto.umh.es/files/2014/05/Stepped-gratings-with-high-modulation-depth-LCoS-POSTPRINT.pdf
