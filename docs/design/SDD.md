# Software design document: DinHot

DinHot is a holography studio for optical trap arrays and shaped light fields that runs in the browser. A reader picks a case:
a trap geometry or a target potential, on a stated optical setup and a stated phase-only spatial light modulator (SLM). The
reader computes the phase hologram with any of 24 methods, from the classical baselines through the current state of the art to
methods beyond it. DinHot then shows where the light goes, how uniform and efficient the traps are, what the device and the
aberrations cost, what a camera feedback loop recovers, and what a trapped bead or atom does in the computed potential. It was born at CEFOP
(Universidad de Concepcion) as DinHotSys, a C++ desktop tool (2010), was rewritten in Python and FastAPI, and is rebuilt here on
the CAOS product template and shell (ADR-0075: this document is written before the development it governs).

## Problem and non-goals

Problem: a phase-only SLM placed in the pupil of a microscope objective can create hundreds to thousands of optical traps at
once, but only if the phase pattern it displays is computed well. The pattern decides how much light reaches the traps
(diffraction efficiency), how equal the traps are (uniformity), where stray light goes (zero order, ghost traps, replicas), how
the pattern survives a real device (phase quantization, pixel crosstalk, aberrations), and how fast it can be recomputed when
the traps move. The methods that solve this span fifty years, from the superposition of prisms and lenses to phase-fixed
weighted Gerchberg-Saxton, gradient optimization with a device model, optimal transport and learned holography. No public tool
runs them side by side on the same task, with the same seeds and metrics, together with the device and the physics of what is
trapped. DinHot does that, and adds six methods past the published state of the art.

Non-goals, each something a reader could reasonably assume:

- Driving hardware. DinHot computes and evaluates holograms in simulation; it does not talk to an SLM or a camera. Its
  camera-in-the-loop method runs on an emulated camera whose errors are stated parameters.
- A calibrated digital twin of one laboratory. Device and setup parameters come from published experiments, labelled as such;
  absolute numbers are those of the stated model, not of a measured instrument.
- Vectorial high-NA focusing as the default model. The engine is scalar (Fraunhofer and angular spectrum); the high-NA case
  carries a validity flag, and the vectorial lane is built only from equations read at the source.
- Display holography (near-eye and 3D displays). The methods overlap, the task does not: DinHot's targets are trap arrays and
  potentials for trapping.
- A server. The site is static; every computation runs in the browser or was baked offline and is replayed.

## Executive brief

The executive view of the Introduction is data, kept apart from this document: one file frames the problem space of
programmable light fields for trapping, centred on scaling neutral-atom tweezer arrays, for a decision maker, in English and
Spanish, with a linked source for every figure. It was researched before any development (the problem-context dossier of the
coordination records) and is rendered by the shell as the first view of the Introduction, where the product lands.

Data file: content/executive.json

## Research basis

Done before the plan and kept here so a reader can re-check it (ADR-0075). The persisted dossiers of the coordination records
(problem context, algorithms, physics and views, repository inventory, ADR walk, gap-closing research) hold every claim with
its source; this table lists what was decided and from what.

| decision | what the research found | source |
|---|---|---|
| The point-trap model, its three metrics (efficiency, uniformity, relative standard deviation) and the analytic and GS baselines M01 to M06 | Superposition, random superposition, random mask, GS, GAA and GSW compared on one 10x10 task: e/u 0.29/0.01, 0.69/0.01, 0.01/0.58, 0.94/0.60, 0.93/0.79, 0.93/0.99 | Di Leonardo, Ianni and Ruocco 2007, https://doi.org/10.1364/OE.15.001913 |
| Phase-fixed weighted GS (M07) is the state of the art for large point arrays | Fixing the focal-plane phase after the initial iterations keeps the weights effective; 1500 foci at 91.2 percent modulation efficiency, camera correction to 1.59 percent in three steps against 6.47 percent for conventional WGS | Kim et al. 2019, https://doi.org/10.1364/OL.44.003178 |
| MRAF (M08) for shaped potentials, trading efficiency for accuracy | Error 0.015 to 0.039 against 0.21 to 0.36 for GS, efficiency 0.18 to 0.45 | Pasienski and DeMarco 2008, https://doi.org/10.1364/OE.16.002176 |
| Direct search (M09) and the efficiency-uniformity cost with one weight | Cost C = -mean(I) + f sigma; under 5 percent variation on 119 traps | Polin et al. 2005, https://doi.org/10.1364/OPEX.13.005831 |
| Conjugate-gradient minimization (M10) with powered costs against vortices | Gradient of the intensity cost by two FFTs; 0.58 percent error on a square lattice | Harte et al. 2014, https://doi.org/10.1364/OE.22.026548 |
| Wirtinger gradient descent with Adam (M11) | Any differentiable forward model; the complex gradient by Wirtinger calculus | Chakravarthula et al. 2019, https://doi.org/10.1145/3355089.3356539 |
| Closed-loop feedback (M12) and its published curve | Trap-depth spread 19 percent rms to 1.4 percent in 20 iterations at gain 0.7 | Nogrette et al. 2014, https://arxiv.org/abs/1402.5329 |
| Device-aware CG with a pixel crosstalk kernel (M13), and the kernel parameters of the device model | Kernel exp(-(abs(kx)^q + abs(ky)^q)/sigma^q) with sigma 1.24 per pixel and q 1.80 on 3x3 sub-pixels; error below 2 percent | Schroff et al. 2023, https://doi.org/10.1038/s41598-023-30296-6 |
| Zernike modes indexed by Noll (M14) | The j to (n, m) ordering and normalization | Noll 1976, https://doi.org/10.1364/JOSA.66.000207 |
| Rearrangement by Hungarian assignment and linear phase interpolation (M16) | Cost sum of d^alpha with alpha above 1 avoids crossings; LPI keeps a moving trap above 70 percent of its intensity where WGS flickers | Lee, Kim and Ahn 2017, https://doi.org/10.1103/PhysRevA.95.053424 ; https://arxiv.org/abs/2501.01391 |
| Unsupervised CNN holograms (M17) | DeepCGH: at least ten times faster than GS and 9 to 43 percent more accurate on volume targets | Eybposh et al. 2020, https://doi.org/10.1364/OE.399624 |
| Optimal-transport initialization of MRAF (M18) | Error 0.17 to 0.96 percent with efficiency 53 to 85 percent on the MRAF targets; a separable dual form at 1024 squared | Swan et al. 2024, https://arxiv.org/abs/2408.17025 ; Torchylo et al. 2025, https://arxiv.org/abs/2512.19072 |
| Multi-plane GS (M19) | Plane-by-plane propagation with an amplitude constraint per plane | Whyte and Courtial 2005, https://doi.org/10.1088/1367-2630/7/1/117 |
| The executive why-now: arrays of thousands of sites, uniformity as the limit | 6,100 atoms in about 12,000 tweezers with an 11.4 percent depth spread after WGS | Manetsch et al. 2025, https://arxiv.org/abs/2403.12021 |
| Atom trap depth proportional to intensity, radial and axial frequencies | U = (3 pi c^2 / 2 omega0^3)(Gamma/Delta) I; omega_r = sqrt(4 U / m w0^2) | Grimm, Weidemuller and Ovchinnikov 2000, https://arxiv.org/abs/physics/9902072 |
| Bead dynamics and the stiffness calibration the Dynamics views check | Overdamped Langevin, corner frequency kappa / (2 pi gamma), Lorentzian spectrum | Tolic-Norrelykke et al. 2006, https://arxiv.org/abs/physics/0603037 |
| Requirements in EARS form, each with its gate | The five EARS patterns | Mavin et al. 2009, https://doi.org/10.1109/RE.2009.9 |

No controlled published comparison of WGS, phase-fixed WGS, CG, MRAF and a learned method on the same point-trap array was
found; the benchmark protocol below is DinHot's own and its numbers are measured, never quoted.

UNVERIFIED: the vectorial Debye equations (Leutenegger et al. 2006, https://doi.org/10.1364/OE.14.011277), the band-limited
angular spectrum limit (https://doi.org/10.1364/OE.17.019662), the crosstalk-aware GS update of Persson et al. 2012, the random
mask rule of Montes-Usategui et al. 2006 and the numeric effects of quantization and flicker were not read in the first round;
the gap-closing research unit reads them before the methods and pages that use them are built, and this line is rewritten with
what it found.

## Sizing and contracts

The design rests on the sizing kept with the coordination records (repositories, components, modules with their owner units,
every boundary, machine limits, parallel units with disjoint write scopes) and on the contract catalog kept here,
[`docs/contracts/catalog.md`](../contracts/catalog.md). Every boundary is a catalog row with one schema file, an example, a test
on each side, its missing-data behavior and a provider.

- Ingestion (params-record, contract 1, `data-pipeline/pipeline/io/contract.py`): a case is an optical setup (wavelength,
  focal length, numerical aperture, immersion index, input beam), a device (pixels, pitch, bit depth, crosstalk kernel, fill
  factor, flicker), a target (a list of traps with id, position in micrometres, relative weight and topological charge, or a
  shaped potential), an aberration (Noll coefficients in waves), the method set and budgets, a seed, the grid, and for the
  dynamic cases the particle and the rearrangement. A missing, non-numeric, NaN or out-of-range value is rejected with its
  reason; a trap outside the unaliased field of view is rejected with the field's bounds (case C11 exists to prove it).
- Artifacts (case-index, case-manifest, trace, contract 2): the index of the twelve cases with bilingual titles and
  categories; one manifest per case (parameters, seed, engine version, lane verdict, metrics per method, expected ranges,
  bilingual band); one trace per case (per method: the metric series against iteration, the final per-trap intensities and
  metrics; for the case's reference method: the quantized phase mask and the focal intensity map in dB at the live grid, the
  axial cuts; for the dynamic cases: the particle trace and the rearrangement frames), each trace within the lane gate's
  256 KiB.
- The benchmark (benchmark-results): the protocol's table, method by geometry by budget, medians and inter-quartile ranges
  over 20 seeds, and the Pareto fronts.
- The model slots (cgh-net, warmstart-model): two ONNX models with their held-out metrics; the baselines behind the same
  contracts are GS for cgh-net and the random-phase start for warmstart-model.
- Readiness: what is real in this build, row by row.
- The dormant API: GET only, 503 with the declared state.

## Technology and versions

Every pinned dependency of `requirements-precompute.txt` (through `data-pipeline/requirements.txt`),
`requirements-dev.txt` and `frontend/package.json`, with the version actually installed; `scripts/check_tech_matrix.py`
fails when a pin and this table disagree. A package.json range is recorded at the version `frontend/package-lock.json`
resolves it to. The runtimes are Python 3.12 (CI; the device's venv may be newer) and Node 24 (CI).

| component | package | version | use | alternative considered |
|---|---|---|---|---|
| engine | numpy | 2.4.6 | the canonical hologram engine (`numpy.fft`, linear algebra); the same pin in `notebooks/requirements.txt` | scipy.fft, rejected: a second heavy dependency for the same transforms |
| notebooks | matplotlib | 3.11.2 | the figures of the notebooks (`notebooks/requirements.txt`); https://pypi.org/pypi/matplotlib/json read on 2026-10-19, released 2026-09-11 | none: the figures of the notebooks need a plotting library, and the web's uplot runs in the browser only |
| notebooks | scipy | 1.18.1 | the pinned reference implementation of the level 3 example notebook (`scipy.integrate.solve_ivp`, RK45 and DOP853; `notebooks/requirements.txt`); https://pypi.org/pypi/scipy/json read on 2026-10-26, released 2026-08-21 | none: it is the state-of-the-art solver the level 3 notebook compares the engine with; the engine itself stays numpy only |
| notebooks | nbclient | 0.11.0 | executes a notebook top to bottom in a fresh kernel (`scripts/run_notebooks.py`); https://pypi.org/pypi/nbclient/json read on 2026-10-19, released 2026-06-05 | nbconvert --execute, rejected: a heavier install for the same execution |
| notebooks | nbformat | 5.11.1 | reads and writes the notebook format (`scripts/run_notebooks.py`); https://pypi.org/pypi/nbformat/json read on 2026-10-19, released 2026-08-17 | none: the format's own library |
| notebooks | ipykernel | 7.4.0 | the Python kernel the notebooks run in; https://pypi.org/pypi/ipykernel/json read on 2026-10-19, released 2026-09-29 | none: nbclient needs a kernel |
| tests | pytest | 9.1.1 | the pipeline, contract, guard and adversarial tests | unittest, rejected: no parametrisation or fixtures |
| lint | ruff | 0.15.18 | lint of data-pipeline, tests, scripts and app | flake8 plus isort, rejected: two tools for one |
| contracts | jsonschema | 4.26.0 | validates every document against its schema file | fastjsonschema, rejected: no support for the draft the schemas declare |
| contracts | openapi-spec-validator | 0.9.0 | validates `docs/contracts/api.openapi.json` | none: the only maintained validator for the OpenAPI 3.1 document |
| API | fastapi | 0.143.0 | the dormant `app/`, run by the API contract tests | flask, rejected: no response models to compare with the OpenAPI document |
| API | httpx | 0.28.1 | the test client of the dormant `app/` | requests, rejected: FastAPI's test client needs httpx |
| shell | @fasl-work/caos-app-shell | 0.19.5 | the shared app shell (pinned exactly, ADR-0078) | a hand-rolled shell, forbidden by ADR-0078 |
| web | react | 19.3.0 | the UI | none: the shell requires it |
| web | react-dom | 19.3.0 | the UI renderer | none: the shell requires it |
| web | react-router | 8.4.0 | the routes | none: the shell requires it |
| web | zustand | 5.0.15 | the workbench selection store | redux, rejected: one store of a few keys |
| web | katex | 0.19.1 | typeset equations on the pages | MathJax, rejected: heavier and slower to render |
| web | lucide-react | 1.52.0 | icons | the shell's own set where it has one |
| web | uplot | 1.6.32 | the interactive curves (`UPlotChart`) | a static SVG, rejected: no hover or zoom |
| live engine | fft.js | 4.0.4 | the Float64 radix-4 FFT of the TypeScript engine; measured 34.9 ms for a 1024 squared complex 2D transform in Node 24 | kissfft-wasm and webfft, not adopted: no measured gain recorded yet, and a WASM build adds a binary to the site |
| learned models | onnxruntime-web | 1.31.1 | inference of cgh-net and warmstart-model in the browser, WASM self-hosted, one thread | a hand-written inference, rejected: the shared runtime is tested and versioned |
| 3D view | three | 0.186.1 | the 3D focal-volume view of the multi-plane cases | regl, rejected: no scene graph or camera controls for an isosurface view |
| build | @types/three | 0.186.0 | types of three | none |
| build | vite | 8.3.5 | bundler and dev server | webpack, rejected: slower and needs more configuration |
| build | @vitejs/plugin-react | 6.1.1 | the React transform for vite | none |
| build | typescript | 5.9.3 | type check of the web and the generated contract types | none |
| build | openapi-typescript | 7.13.0 | generates `contract.gen.ts` from the OpenAPI document | hand-written types, rejected: they drift (the build checks them) |
| build | @types/node | 24.19.1 | types of the build scripts | none |
| build | @types/react | 19.3.0 | types of React | none |
| build | @types/react-dom | 19.3.0 | types of React DOM | none |
| tests | vitest | 5.0.3 | the web unit tests | jest, rejected: needs a transform for the vite config |
| gate | playwright | 1.63.0 | the measured UI gate (`npm run gate`), local only | cypress, rejected: heavier install |

## Resources

What each stage needs on the development workstation (Windows 11, Intel Core i9-14900HX, 48 GB RAM, RTX 4070 Laptop 8 GB).
These are bounds set from the dossiers' measured FFT timings and the method costs; the bake and the training replace each bound
with its measurement in [`measured-resources.md`](measured-resources.md) before the release.

| stage | memory | disk | time | where it runs |
|---|---|---|---|---|
| bake (`data-pipeline/run.py`, twelve cases, every valid method per case) | at most 4 GB peak (1024 squared complex grids, a few at once) | at most 3 MB of artifacts in `data/derived/` (each trace at most 256 KiB) | at most 20 min | workstation, never CI |
| benchmark (the protocol, 7 geometries, 24 methods, 20 seeds, three budgets) | at most 4 GB peak | at most 2 MB of results | at most 6 h, resumable by cell | workstation, never CI |
| training (cgh-net and warmstart-model, PyTorch on the GPU) | at most 7 GB GPU memory, 8 GB host | at most 10 MB of ONNX models and metrics; datasets in the data root, never in the repository | at most 3 h | workstation GPU, never CI |
| tests (pytest, the whole suite) | at most 2 GB peak | temporary copies under the temp root | at most 10 min | workstation; the plants (`tests/adversarial`) also in CI |
| install (`npm ci`) | at most 400 MB peak | at most 400 MB in `node_modules` | at most 3 min | workstation and CI web job |
| build (`npm run build`) | at most 600 MB peak | at most 30 MB in `frontend/dist` (the onnxruntime WASM is the largest file) | at most 60 s | workstation and CI web job |
| web unit tests (`npm test`, engine parity included) | at most 1 GB peak | none | at most 60 s | workstation and CI web job |
| deploy payload (GitHub Pages) | none | at most 30 MB uploaded | one Pages deploy, under 3 min | CI after main |

## Lanes

- Offline: `data-pipeline/run.py` bakes every case with every method valid for it, checks each against its expected ranges,
  runs the benchmark protocol and the units gate. Training runs locally only. Never in CI, never in the browser.
- Replay: the committed artifacts (manifests, traces, benchmark results, model metrics and the ONNX models), copied into the
  site by `frontend/scripts/copy-data.mjs` and fetched with the version in the address.
- Live: `frontend/src/engine/holo/`, a TypeScript port of the forward models, the device model and the live methods, running
  in a Web Worker so the interface never blocks. The FFT is fft.js (Float64). An optional WebGPU backend runs the FFT-form
  iterations on the GPU when the browser offers it, and falls back to the CPU path otherwise. The basis is measured: the lane gate
  gives each case a run budget of 1500 ms and a trace budget of 256 KiB. At the live grid (256 squared padded to 512 squared) a
  weighted GS iteration measured about 24 ms in Node 24, so a 30-iteration run fits the budget. The baked methods (M09, M13,
  M18, B4, B5, the training of M17 and B3) are replayed and labelled as such.

## Method ladder

Every method is one complete vertical (ADR-0069): Python engine, its acceptance test, its run in the benchmark protocol, its
card in `docs/frameworks/`, its Methodology topic and, when live, its TypeScript port with a parity test. The acceptance
criteria are measured on DinHot's own grids; the anchors are the published results they are set against.

| id | method | acceptance criterion | gate |
|---|---|---|---|
| M01 | Superposition of prisms and lenses | on the 10x10 task, efficiency and uniformity within the seed spread of 0.29 and 0.01 | `tests/methods/test_m01_superposition.py` |
| M02 | Random superposition | on the 10x10 task, within the seed spread of 0.69 and 0.01 | `tests/methods/test_m02_random_superposition.py` |
| M03 | Random mask | on the 10x10 task, efficiency about 1/M and uniformity within the spread of 0.58 | `tests/methods/test_m03_random_mask.py` |
| M04 | Gerchberg-Saxton, point-trap and FFT forms | the two forms agree on a 2D grid; 30 iterations on the 10x10 task reach efficiency at least 0.9 with uniformity near 0.6 | `tests/methods/test_m04_gs.py` |
| M05 | Generalized adaptive additive | uniformity above GS at equal iterations on the 10x10 task | `tests/methods/test_m05_gaa.py` |
| M06 | Weighted GS | efficiency and uniformity at least 0.9 within 10 iterations on the 10x10 task; the 3x3x3 lattice above 0.9 and 0.98 | `tests/methods/test_m06_gsw.py` |
| M07 | Phase-fixed weighted GS | fewer iterations than M06 to a relative standard deviation of 0.5 percent on a 50x30 array | `tests/methods/test_m07_phase_fixed_wgs.py` |
| M08 | MRAF | on ring, disc and line targets, signal-region error at least five times below GS at the cost of efficiency | `tests/methods/test_m08_mraf.py` |
| M09 | Direct search | uniformity at least 0.98 on the 10x10 task; under 5 percent rms variation on a quasi-periodic set | `tests/methods/test_m09_direct_search.py` |
| M10 | Conjugate-gradient minimization | the analytic gradient matches finite differences; a square lattice below 1 percent error | `tests/methods/test_m10_cg.py` |
| M11 | Wirtinger gradient descent with Adam | lower trap-intensity error than M04 at equal iterations on the 10x10 task | `tests/methods/test_m11_wirtinger_adam.py` |
| M12 | Closed-loop WGS on an emulated camera | from a 19 percent rms open-loop spread, at most 2.1 percent in 20 iterations at gain 0.7 | `tests/methods/test_m12_closed_loop.py` |
| M13 | Device-aware CG with pixel crosstalk | on the crosstalk device, lower error than M10 without the model on a large disc | `tests/methods/test_m13_crosstalk_cg.py` |
| M14 | Zernike correction and sensorless modal recovery | recovers an injected set of Noll modes 4 to 11 within 5 percent of their amplitude | `tests/methods/test_m14_zernike.py` |
| M15 | Laguerre-Gaussian vortex traps | the ring phase winds by 2 pi l with an error under 0.1 rad | `tests/methods/test_m15_vortex.py` |
| M16 | Hungarian assignment and linear phase interpolation | no crossing moves for alpha 1.5 on a 7x7 to 3x3 sort; a moving trap above 70 percent of its mean intensity | `tests/methods/test_m16_rearrangement.py` |
| M17 | Unsupervised CNN hologram | on held-out targets, accuracy above GS at the same wall-clock budget | `tests/methods/test_m17_cgh_net.py` |
| M18 | Optimal-transport initialized MRAF | lower error than MRAF from a random start on the shaped targets | `tests/methods/test_m18_ot_mraf.py` |
| M19 | Multi-plane GS | on a three-plane target, every plane within the plane intensity band | `tests/methods/test_m19_multiplane.py` |
| B1 | Device-aware weighted GS | on the crosstalk device, relative standard deviation at least two times below M07, efficiency at most 10 percent lower | `tests/methods/test_b1_device_wgs.py` |
| B2 | Flicker-bounded phase-continuous sequence | minimum transient intensity of a moving trap at least 0.9 of its mean, against LPI | `tests/methods/test_b2_flicker_bounded.py` |
| B3 | Learned warm start for phase-fixed WGS | median iterations to 1 percent at least two times below a random start, held-out geometries, model at most 1 MB | `tests/methods/test_b3_warm_start.py` |
| B4 | Aberration- and pointing-robust hologram | the 95th percentile of the relative standard deviation over a perturbation ensemble at least two times below M07 | `tests/methods/test_b4_robust.py` |
| B5 | Efficiency-uniformity Pareto front | hypervolume at least that of the M04, M05, M09 and M06 points on the 10x10 task | `tests/methods/test_b5_pareto.py` |

Physics components, each tested in `tests/engine/`: the FFT and point-trap forward models (agreement at the trap positions), the
angular spectrum for defocused planes, the device model (quantization, crosstalk, fill-factor envelope, zero order, flicker),
the Zernike basis (orthogonality over the disc), the trap physics and the particle dynamics (the simulated bead's spectrum
recovers the input corner frequency).

## Cases

Twelve cases in four categories. Arrays: C01 small square grid (3x3), C02 10x10 grid with camera feedback, C03 large array
(32x32 and the disordered 819 set), C12 calibration (the 10x10 task of the analytic and GS baselines). Shaped and 3D: C04 ring and
disc potentials with the crosstalk model on and off, C05 three-plane array with vortices, C06 vortex ring with a line trap.
Device and optics: C07 high numerical aperture, C08 device-limited (crosstalk, 4-bit phase, fill factor, flicker), C09 aberrated
with and without correction. Dynamics and controls: C10 rearrangement sequence, C11 a trap outside the field of view (refused,
never computed). Each case states numeric expected ranges for its metrics (`data-pipeline/pipeline/core/expect.py` fails the bake
outside them) and a bilingual band. Variants: the method the reader picks among those valid for the case, and the device (ideal
or the case's own), computed live where the method is live. The trap editor (add, drag, delete) changes the case's target live.

## Oracles

- Parseval and the forward-model agreement: total power is conserved by the propagation, and the FFT and point-trap forms give
  the same trap fields at the trap positions.
- The published reference results of the calibration case: the analytic and GS rows of the 10x10 task, reproduced within the
  seed spread.
- The physics limits: a random mask reaches an efficiency about the inverse of the trap count; an ideal uniform array cannot
  exceed the efficiency bound of a phase-only hologram; a vortex winds its phase by 2 pi l.
- The particle oracle: the simulated bead's power spectrum fits a Lorentzian whose corner frequency is the stiffness of the
  computed trap divided by 2 pi gamma; its position histogram follows the Boltzmann law of the computed potential.
- Parity: the Python engine is the reference for the live engine, to a stated tolerance per quantity.
None of these is a model judging a model.

## Beyond the state of the art

Each component is DinHot's own, grounded in a sourced gap, measured by the benchmark protocol against the strongest baseline,
and covered by a level 4 notebook in each language.

- BS-1 (B1) device-aware weighted GS: the WGS weights kept, the phase update replaced by gradient steps through the crosstalk
  kernel and the quantizer. Gap: the crosstalk model has been used only with conjugate gradient on shaped potentials (Schroff et
  al. 2023, https://doi.org/10.1038/s41598-023-30296-6).
- BS-2 (B2) flicker-bounded phase-continuous sequences: each intermediate hologram optimized with the trap phases locked to a
  smooth trajectory. Gap: linear phase interpolation does not optimize its intermediate frames (https://arxiv.org/abs/2501.01391).
- BS-3 (B3) learned warm start: a permutation-invariant network over trap coordinates predicts the initial trap phases of
  phase-fixed WGS. Gap: no source initializes WGS with a network (algorithms dossier D5.1).
- BS-4 (B4) robust hologram: the expected cost over residual aberrations and pointing errors. Gap: corrections are global or per
  site, never robust (https://arxiv.org/abs/2512.15967).
- BS-5 (B5) the efficiency-uniformity Pareto front by continuation. Gap: methods report single trade-off points (Di Leonardo et
  al. 2007, https://doi.org/10.1364/OE.15.001913).
- BS-6 (M12) an open camera-in-the-loop emulator that reproduces the published feedback curves in the browser. Gap: feedback is
  published on hardware only (Nogrette et al. 2014, https://arxiv.org/abs/1402.5329).

## Deploy driver

GitHub Pages at dinhot.fasl-work.com: a public repository, a static site, every artifact committed, no secret and no server
(ADR-0055 A55.1: no VPS trigger applies; the compute is an FFT loop the browser runs within the lane budget). Pages sends no
COOP and COEP headers, so the workers are single-threaded and SharedArrayBuffer is not used. The previous VPS service is
retired after the Pages site passes its live checks. The target is written in `deploy/TARGET` and checked by
`scripts/check_deploy_place.py`.

## Risks and kill criteria

- Risk: the two engines drift (FFT rounding, phase wrapping). Kill: the parity tests fail.
- Risk: a method claims a result it does not reach on DinHot's grids. Kill: its acceptance test fails; the pages state only
  measured numbers from the committed benchmark results.
- Risk: the live engine blocks the interface. Kill: the gate's idle and reactivity checks (G8, G9) and the lane gate's budget.
- Risk: the WebGPU backend disagrees with the CPU path. Kill: the browser agreement test; the backend is disabled when it fails.
- Risk: a learned model is judged by its own training data. Kill: held-out geometries only, written apart before training.
- Risk: a baked artifact exceeds the trace budget. Kill: the lane gate in the bake.
- Risk: an instantiated product keeps pieces of the example. Kill: `scripts/check_template_residue.py`.
- Risk: the site looks right and is not. Kill: `npm run gate` before any deploy, with the captures read.

## ADR fit

| ADR | Rule | Carried by |
|---|---|---|
| ADR-0011, ADR-0012 | English default and Spanish; light and dark | the shell |
| ADR-0016, ADR-0017 | the shell frame, six routes, the documentation areas; the executive view first | the shell's pages and `ExecutiveView`, `content/executive.json` |
| ADR-0054 | committed artifacts are the evidence; the live lane re-runs the engine | `data/derived/`, `frontend/src/engine/holo/`, the parity tests |
| ADR-0055 | Pages by default | `deploy/TARGET` |
| ADR-0056 | the `docs/` wiki | `docs/` |
| ADR-0057 | the product archetype; no package of its own | this repository; `product.json` `method_packages` is empty |
| ADR-0058 | the architecture modal, five bilingual diagrams | `frontend/src/architecture/` |
| ADR-0068 | versions X.XX.XXX | `VERSION`, `scripts/check_version_coherence.py` |
| ADR-0069 | one complete vertical per method with its acceptance criterion; training offline | the method ladder above, `tests/methods/` |
| ADR-0070 | Focus mode for the App: the workbench opens the open group of a case in the full viewport; `?focus=1`, Escape or the exit button returns to the same case, group and sub-view | `frontend/src/workbench/Workbench.tsx` (`focus`), `npm run gate` with `--require-focus` (G18) |
| ADR-0071 | the page is the viewport; one tab row; drawing at least half the viewport | the shell's `CaseWorkbench`; the gate |
| ADR-0074 | CI runs cheap checks only; no training in CI | `.github/workflows/ci.yml`, `scripts/check_ci_budget.py` |
| ADR-0075 | every requirement names its gate | `docs/design/features/`, `scripts/check_sdd.py` |
| ADR-0078 | rules live in the base | shell 0.19.5 pinned exactly and template 0.12.000 |
| ADR-0080 | contract-first parallel delivery | `docs/contracts/`, `tests/contracts/`, `scripts/check_contracts.py`, `scripts/check_readiness.py` |
| extension (no ADR) | a WebGPU backend for the live FFT iterations, optional, with the CPU path as the fallback and a browser agreement test | `frontend/src/engine/holo/gpu/`; proposed to the base as a rule for in-browser accelerated compute |
| extension (no ADR) | a perceptually uniform cyclic colormap for phase, which the visualization rubric does not name | `frontend/src/workbench/colormaps.ts`, its source and licence in `ATTRIBUTION.md` |
