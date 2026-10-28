# Frameworks

One card per method of the ladder (24) and one per physics component (7). A card is the binding record of what the code does: the
equations with their source, the module and entrypoint with its defaults, the acceptance criterion and the test that holds it, the
values DinHot measured (with seeds, grid and date, labelled as DinHot's own), the limits, and the references with DOIs or URLs.
Nothing on a card is a published number unless it says "published" and names the source; every DinHot number comes from an acceptance
test run or a committed artifact. Where a method is still being built, the card states its contract and says that its measurements are
pending.

The engine is Python with numpy, in `data-pipeline/pipeline/model/holo/` (the core in `core/`, the methods in `methods/`). It is not a
package of its own (ADR-0057): the notebooks call its public functions. A TypeScript port runs the live methods in the browser and is
held to the Python engine by parity tests.

Test setup of the acceptance values unless a card says otherwise: 256 by 256 SLM pixels padded to a 512 by 512 FFT grid, wavelength 850 nm,
focal length 250 mm, pixel pitch 12.5 um, numerical aperture 0.5, Gaussian input beam of waist 1; the 10 by 10 task is a square grid of 100 traps
on FFT bins, 8 bins apart (`tests/methods/conftest.py`).

<p align="center"><img src="assets/method-ladder.svg" alt="The method ladder: classical baselines, Gerchberg-Saxton family, optimization, control, learned and beyond" width="760"></p>

## Physics components

| Card | Component | Module |
|---|---|---|
| [P01](frameworks/P01_forward-models-and-metrics.md) | Forward models, geometry, metrics | `core/forward.py`, `geometry.py`, `metrics.py`, `modes.py`, `traps.py` |
| [P02](frameworks/P02_device-model.md) | Device model (quantization, crosstalk, fill factor, flicker) | `core/device.py` |
| [P03](frameworks/P03_zernike.md) | Zernike aberrations, Noll order | `core/zernike.py` |
| [P04](frameworks/P04_trap-physics.md) | Trap physics (bead stiffness, atom dipole trap) | `core/trapphys.py` |
| [P05](frameworks/P05_particle-dynamics.md) | Particle dynamics and the spectral oracle | `core/dynamics.py` |
| [P06](frameworks/P06_emulated-camera.md) | Emulated camera | `core/camera.py` |
| [P07](frameworks/P07_portable-rng.md) | Portable random generator | `core/rng.py` |

## Methods

| Card | Method | Family | Lane | Anchor |
|---|---|---|---|---|
| [M01](frameworks/M01_superposition.md) | Superposition of prisms and lenses | analytic | live | Di Leonardo 2007 |
| [M02](frameworks/M02_random-superposition.md) | Random superposition | analytic | live | Di Leonardo 2007 |
| [M03](frameworks/M03_random-mask.md) | Random mask | analytic | live | Montes-Usategui 2006 |
| [M04](frameworks/M04_gerchberg-saxton.md) | Gerchberg-Saxton | GS | live | Gerchberg and Saxton 1972 |
| [M05](frameworks/M05_gaa.md) | Generalized adaptive additive | GS | live | Di Leonardo 2007 |
| [M06](frameworks/M06_gsw.md) | Weighted GS | GS | live | Di Leonardo 2007 |
| [M07](frameworks/M07_phase-fixed-wgs.md) | Phase-fixed weighted GS | GS | live | Kim 2019 |
| [M08](frameworks/M08_mraf.md) | Mixed-region amplitude freedom | full-field GS | live | Pasienski and DeMarco 2008 |
| [M09](frameworks/M09_direct-search.md) | Direct search | optimization | baked | Polin 2005 |
| [M10](frameworks/M10_conjugate-gradient.md) | Conjugate-gradient minimization | optimization | both | Harte 2014 |
| [M11](frameworks/M11_wirtinger-adam.md) | Wirtinger gradient descent with Adam | optimization | both | Chakravarthula 2019 |
| [M12](frameworks/M12_closed-loop-wgs.md) | Closed-loop WGS on an emulated camera | feedback | live | Nogrette 2014 |
| [M13](frameworks/M13_crosstalk-aware-cg.md) | Device-aware CG with pixel crosstalk | device-aware | baked | Schroff 2023 |
| [M14](frameworks/M14_zernike-correction.md) | Zernike correction and sensorless recovery | aberration | live | Nogrette 2014, Noll 1976 |
| [M15](frameworks/M15_vortex-traps.md) | Laguerre-Gaussian vortex traps | modes | live | Polin 2005 |
| [M16](frameworks/M16_rearrangement.md) | Hungarian assignment and linear phase interpolation | dynamic | live | Lee 2017 |
| [M17](frameworks/M17_unsupervised-cnn-hologram.md) | Unsupervised CNN hologram | learned | baked training, live inference | Eybposh 2020 |
| [M18](frameworks/M18_ot-initialized-mraf.md) | Optimal-transport initialized MRAF | optimization | baked | Swan 2024 |
| [M19](frameworks/M19_volumetric-3d-gs.md) | Volumetric 3D GS (multi-plane) | GS | both | Whyte and Courtial 2005 |
| [B1](frameworks/B1_device-aware-wgs.md) | Device-aware weighted GS | beyond | baked | gap: Schroff 2023 |
| [B2](frameworks/B2_flicker-bounded-sequence.md) | Flicker-bounded phase-continuous sequence | beyond | baked | gap: arXiv 2501.01391 |
| [B3](frameworks/B3_learned-warm-start.md) | Learned warm start for phase-fixed WGS | beyond, learned | live inference | gap: no source |
| [B4](frameworks/B4_aberration-robust-hologram.md) | Aberration-robust hologram | beyond | baked | gap: per-site or global correction only |
| [B5](frameworks/B5_pareto-front.md) | Efficiency-uniformity Pareto front | beyond | baked | gap: single trade-off points only |

The lane column is the `lane` of each method's `SPEC`. "Live" means the TypeScript engine computes it on the reader's input; "baked" means the Python engine bakes it and the
site replays it; "both" means a small size runs live and the full size is baked. Every method is also run by the benchmark protocol in Python
([model evaluation](architecture/06_model-evaluation.md)).

## Card format

Every card has the same sections, in this order: a header table (family, lane, targets, module and entrypoint with `SPEC` and `run` lines, anchor), Purpose, the equations with their
source (or The gap and Method for a beyond-the-state-of-the-art method), Implementation (defaults), Acceptance criterion and test, Measured values (with seeds and grid), Limits, References.
A method that is not yet built also has a Pending section at its end naming what is pending. An unverified reading of a source is written `UNVERIFIED` with what was tried.

## Status of the measured values

The measured values of the classical and optimization methods and of the beyond-the-state-of-the-art methods are those of the acceptance runs of 2026-10-28 on the development workstation, with the seeds
stated on each card (fewer than the 20 seeds of the benchmark protocol). The benchmark table over 20 seeds, the Pareto fronts and the learned-model metrics are shown by the Benchmark page
when the benchmark has run for the build; the cards never quote a number that the benchmark has not produced.
