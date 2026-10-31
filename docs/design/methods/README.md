# Method design records

One design record for every row of the method ladder of the [software design document](../SDD.md): the ten classical methods, the nine state-of-the-art methods and the five methods beyond them. The ladder gives one
acceptance criterion and one gate per row; the record gives the full design that a reviewer checks the code and the results against (ADR-0075, ADR-0069). The frameworks cards in [frameworks](../../frameworks.md)
describe the same methods for a reader of the site; the records differ in what they promise: every default is the code's, with its file and line and the source or the measurement that set it, and every measured number
names its report or committed artifact and its conditions.

Every record has the same sections: tier and role (for a classical method, the established method and why it is a baseline; for a state-of-the-art method, the current solution replicated and its source; for a beyond
method, the hypothesis and the gap), the problem it answers, inputs and outputs, the method with its equations and their sources, defaults, complexity and lane, the acceptance criterion and gate (as the ladder row, and how
the test measures it), the evaluation that confirms or refutes it, the measured result, the limits and failure modes, and the references. A beyond record states its outcome in the header table and keeps a negative one
(BS-3 refuted, BS-4 negative for pointing errors).

## Conditions common to the records

- The acceptance tests run the real methods on the live grid of the engine: 256 by 256 SLM pixels padded 2 (FFT grid 512 by 512), wavelength 850 nm, focal length 250 mm, numerical aperture 0.5, immersion index 1.0, pixel
  pitch 12.5 um and a Gaussian beam of waist fraction 1 (`tests/methods/conftest.py`), unless a record says another grid (the shaped targets of the optimization methods use a 64-pixel or 128-pixel SLM padded 2; M17 uses 128
  pixels padded 1). The 10x10 task is a square grid of traps on FFT bins, 8 bins apart.
- Seeds, iteration budgets and the machine are stated per measurement. The measured values quoted from the unit reports (E2, E3, M1, T1, I1) are the values of their acceptance runs of 2026-10-28.
- The tables headed "Committed canonical bake" are computed from `data-pipeline/pipeline/cases/measured_ranges.json` (the mean over three seeds of the canonical bake, with the range) and the iteration count of
  `data/derived/manifests/`. Each case has its own optics and device, so these values are not the acceptance-test conditions and must not be compared with them without reading the case.
- Metrics follow `core/metrics.py`: efficiency $e = \sum_m I_m$, uniformity $u = 1 - (\max I - \min I)/(\max I + \min I)$ and relative standard deviation $\sigma = 100\,\mathrm{std}(I)/\mathrm{mean}(I)$ in percent, with
  $I_m = |V_m|^2$ divided by the target weight where the weights differ.
- The numbering is the ladder's: `M<n>` and `BS-<n>`; the engine id of a beyond method is `B<n>` (BS-6, the emulated camera, was withdrawn as a beyond claim and is part of M12's record).
- Unverified items are written UNVERIFIED with what was tried; a field the sources cannot fill is written as not established.

## Classical

| Record | Method | One line |
|---|---|---|
| [M01](M01-superposition.md) | Superposition of prisms and lenses | the plain sum of the single-trap holograms; the zero point of the ladder (efficiency 0.28, uniformity 0.0003) |
| [M02](M02-random-superposition.md) | Random superposition | one random phase per trap; the start of most iterative methods (efficiency 0.75, uniformity 0.25) |
| [M03](M03-random-mask.md) | Random mask | disjoint random pixel subdomains per trap; equal traps at an efficiency about 1/M |
| [M04](M04-gerchberg-saxton.md) | Gerchberg-Saxton | the point-trap and FFT forms of the iteration; the baseline of the weighted and shaped methods |
| [M05](M05-gaa.md) | Generalized adaptive additive | GS with a feedback on weak traps; uniformity above GS, with the scale convention stated |
| [M06](M06-gsw.md) | Weighted GS | integral feedback on the weights; efficiency and uniformity above 0.9 in 10 to 13 iterations |
| [M09](M09-direct-search.md) | Direct search | pixel-wise search on the Polin cost; uniformity above 0.999 at a lower efficiency |
| [M14](M14-zernike-correction.md) | Zernike correction and sensorless recovery | an additive wavefront removed by a merit-function modal search on the camera |
| [M15](M15-vortex-traps.md) | Laguerre-Gaussian vortex traps | orbital angular momentum as one more delay term in the weighted GS; winding checked on a ring |
| [M19](M19-volumetric-3d-gs.md) | Multi-plane GS (volumetric 3D GS) | Whyte and Courtial's Ewald-sphere 3D Gerchberg-Saxton for point traps at several depths |

## State of the art

| Record | Method | One line |
|---|---|---|
| [M07](M07-phase-fixed-wgs.md) | Phase-fixed weighted GS | Kim et al. 2019; the code default `n_fix` is 12 and the acceptance criterion is measured with 60 |
| [M08](M08-mraf.md) | Mixed-region amplitude freedom | Pasienski and DeMarco 2008; accuracy for shaped potentials bought with efficiency |
| [M10](M10-conjugate-gradient.md) | Conjugate-gradient minimization | Harte et al. 2014; closed-form gradient checked against finite differences, strong-Wolfe line search |
| [M11](M11-wirtinger-adam.md) | Wirtinger gradient descent with Adam | Chakravarthula et al. 2019; the learning rate 1.0 tuned on the trap loss |
| [M12](M12-closed-loop-wgs.md) | Closed-loop weighted GS on an emulated camera | Nogrette et al. 2014 and Kim et al. 2019 updates on `core/camera.py` |
| [M13](M13-crosstalk-aware-cg.md) | Device-aware CG with pixel crosstalk | Schroff et al. 2023; the crosstalk kernel inside the gradient |
| [M16](M16-rearrangement.md) | Hungarian assignment and linear phase interpolation | Lee, Kim and Ahn 2017 and the LPI sequence; zero crossings, transient ratio above 0.7 |
| [M17](M17-unsupervised-cnn-hologram.md) | Unsupervised CNN hologram (DeepCGH form, three planes) | Eybposh et al. 2020 at DinHot's size; released, 1.14 times M19 at equal wall-clock |
| [M18](M18-ot-initialized-mraf.md) | Optimal-transport initialized MRAF | Swan et al. 2024 and Torchylo et al. 2025; about 10 times lower error than a random start |

## Beyond the state of the art

| Record | Method | One line |
|---|---|---|
| [B1](B1-device-aware-wgs.md) | Device-aware weighted GS (B1) | hypothesis confirmed: spread 49 times below M07 on the crosstalk device at 0.997 of its efficiency |
| [B2](B2-flicker-bounded-sequence.md) | Flicker-bounded phase-continuous sequence (B2) | hypothesis confirmed in DinHot's transient model: 0.92 against 0.54 to 0.72 for LPI |
| [B3](B3-learned-warm-start.md) | Learned warm start for phase-fixed WGS (B3) | hypothesis refuted: 1.75 times against 2, and a control without the network gains as much |
| [B4](B4-aberration-robust-hologram.md) | Aberration-robust hologram (B4) | confirmed for residual aberrations (a median of 1.435 times over three seeds); pointing errors not obtained (1.04 times) |
| [B5](B5-pareto-front.md) | Efficiency-uniformity Pareto front (B5) | hypothesis confirmed by a small margin: hypervolume 0.8190 against 0.8018 (re-measured 2026-10-29) |
