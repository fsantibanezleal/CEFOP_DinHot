# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.02.003], 2026-11-08

### Changed

- Adopted CAOS_PRODUCT_TEMPLATE 0.15.006 and the shared app shell 0.25.0. The shell's gate now measures DinHot's long
  documentation pages, because the walk's budget scales with the document. The story's callout cards show their state. The
  fourteen methods in the rail are one select, using the shell's variant select layout, which was added for DinHot. The site's
  further files (the benchmark, the model metrics, the released models) are served through the base's product hook.
- The App opens on the optical train, from the laser to the traps, drawn from the case's setup, and shows the SLM in section, one
  pixel row with its commanded and displayed phase; both carry anchored callouts. A trap selected on the focal plane, in the per-trap
  bars or on the optical train is selected everywhere. The method at work redraws the focal plane at the iteration the reader scrubs.
- A guided story of five steps (`/story/setup`, `/story/device`, `/story/method`, `/story/compare`, `/story/hold`) states one measured
  finding per step, computed from the release's artifacts; the comparison step is on the modelled device.
- Every method is named by its name in the app, the notebooks, the manuscripts and the README; the engine ids stay in code and data.
- The notebook runtimes live in the device's venvs root (`<venvs root>/dinhot/`), as the base requires.
- Re-baked at 0.02.003: case C01 traps a bead in water (medium index 1.33), so its stiffness and corner frequency are 1.98 pN/um and
  34.5 Hz; the other twelve cases reproduce; the benchmark was run again (its cells run the seeds a 600 s wall-clock bound admits);
  the model metrics are measured again at this version by the generation itself.
- Publications: the technical report v0.02.003 (10.5281/zenodo.24049958) and the device-aware weighted GS and flicker-bounded
  sequences paper v0.04 (10.5281/zenodo.24049969), and three new papers: the efficiency-uniformity front (10.5281/zenodo.24022463),
  the aberration-robust hologram (10.5281/zenodo.24022465) and the learned warm start (10.5281/zenodo.24022471), each generated
  from this bake and reviewed by a reader other than its writer.

### Fixed

- The review findings of the technical report, the four method papers and the notebooks of topics 01 to 08, and the citations checked
  against the full texts where they were open.
- The full gate's findings on the release build: labels that overlapped or were cut in the optical train, the SLM section, the
  phasor figure and the lanes figure; the story's callouts, which overlapped at some sizes and were missing on the phone; the
  method step, which kept changing while idle.
- Two readings of the views by a reviewer other than their builders:
  - **The story:** its exits open the App on the step's view and method. Its callouts sit above their subjects on every screen size.
    The hold step pins its cards to the bead and to the fitted corner frequency.
  - **The App's views:**
    - A trap selected anywhere is marked in the focal image and in the per-trap bars. The focal image has micrometre axes and three callouts.
    - The dynamics view shows the bead in its trap with its position against time and its spectrum.
    - The Pareto view tells its series apart, draws the seed ranges, and recommends a method with its reason.
  - **Text:** cases and benchmark geometries are named by their names, never their ids, and micrometres are written µm.

## [0.02.002], 2026-10-31

### Changed

- Re-baked at 0.02.002, and the technical report v0.02.002 (10.5281/zenodo.23850386) and the manuscript v0.03 (10.5281/zenodo.23850389) generated from that
  bake. The report now states that the benchmark's cell medians depend on the seeds a wall-clock bound admits, so the count of
  geometries where the stored Pareto front meets the published hypervolume at 100 iterations moves between runs (margins at most 0.007).

## [0.02.001], 2026-10-31

### Changed

- Adopted CAOS_PRODUCT_TEMPLATE 0.14.000: each method is named by its name wherever a reader sees it. The app, the notebooks, the
  README and both manuscripts present 19 published methods and 5 proposed methods; the Methodology page groups them by family, and
  the Benchmark page compares published and proposed methods, each proposed method against the strongest published method of its cell.
- The level 3 and 4 notebooks use the sections Comparison and Evidence.
- The technical report v0.02.001 (10.5281/zenodo.23837873) is organized by method family, and the manuscript on device-aware weighted
  GS and flicker-bounded sequences is at v0.02 (10.5281/zenodo.23837877), both on the numbers of 0.02.000.
- Re-baked at 0.02.001: the cases reproduce; the benchmark's cells run more seeds within the same wall-clock bound, so its medians move.

## [0.02.000], 2026-10-30

### Changed

- Re-instantiated from CAOS_PRODUCT_TEMPLATE 0.12.000 (now 0.13.001) into this repository, history kept: the pipeline, the two
  contracts, the lanes, the workbench on the shared shell, the six routes, the guards and the measured gate. The
  FastAPI and WebSocket application, its vanilla JavaScript frontend and the legacy DinHotSys C++ sources and
  binaries leave the tree; they stay in the git history (tag v0.01.000).

### Added

- The App: the workbench of DinHot (five groups and the Context write-up, a trap editor, the live and replay lanes with their labels, Focus mode,
  the two learned model slots in the browser with their baselines) and the removal of the template's example engine.
- The live engine: a TypeScript port of the forward models, the device model and fifteen methods in a Web Worker, held to the Python engine by
  parity tests, with an optional WebGPU backend that falls back to the CPU path and records why.
- Case C13, the disordered array of 819 traps, and case C14, a three-plane volume at the geometry of the released cgh-net, so the bake holds
  fourteen cases (thirteen baked, C11 refused by contract 1); the cases bake in parallel; the expected ranges are measured on three seeds and
  each case card states them, written by `scripts/write_case_ranges.py`.
- The learned slots: `cgh-net` (M17) released with its ONNX graph and card, `warmstart-model` (B3) tested and refuted, each with its baseline.
- The specification of eleven features with a gate per requirement and an adversarial check per requirement (`docs/design/features/`), and the
  planted-defect tests that run each gate with its defect (`tests/adversarial/plant_run.py`); the measured resources
  (`docs/design/measured-resources.md`).
- The three method tiers: classical, state of the art and five proposals beyond it (BS-1 to BS-5; BS-3 refuted, BS-4 negative on pointing).
- Sixty didactic notebooks, thirty per language, by topic from simple to complex, reviewed against the notebook bar and re-executed.
- The Benchmark page: the protocol, one tab per geometry with its device, parameter set and budget, the three-tier comparison, the Pareto
  fronts, the five beyond claims with their verdicts, the learned models, the device and budget curves and an in-browser timing, read from
  the committed results at run time.
- The technical report and the manuscript of BS-1 and BS-2 are generated from the committed artifacts and from scripts that measure what a
  table states: the acceptance table by `manuscripts/holographic-trap-studio/data/acceptance.py`, BS-1, BS-2 and BS-2's scope on long moves
  and on C10 by `manuscripts/device-aware-flicker-bounded/data/measure.py`.

### Fixed

- M06 and M07 project the start hologram's field with the initial weights (g0 = 1): from the same start they now equal slmsuite 0.5.0's
  WGS-Leonardo and WGS-Kim at feedback exponent 1 to four digits (`tests/methods/baseline/test_m06_against_slmsuite.py`,
  `test_m07_against_slmsuite.py`), in Python, TypeScript and WGSL; the beyond methods' GS family runs those rules instead of a copy, and the
  claims that rest on them were re-measured (BS-1, BS-2 over 8 and 6 seeds, BS-4, BS-5).
- The benchmark lists a cell whose method refuses the geometry as skipped with the method's reason, instead of stopping the run, and
  stores B5's Pareto front from the indices of its non-dominated points (the release run stopped on it).
- BS-4's robustness to pointing errors re-measured on the corrected engine: 1.04 times (1.02 before), still a reported negative.
- B1 (BS-1) returns its best iterate that keeps 0.9 of its warm start's efficiency: its weight update could wind up on a device
  it cannot follow (the benchmark's square lattice on the C08 device, where one seed fell to 0.03 efficiency); its acceptance
  figures are unchanged, C08 and the benchmark's B1 cells were re-measured.
- A released model without onnxruntime refuses to run instead of answering with its baseline under the learned method's id.
- The cgh-net, warmstart-model and model-metrics contracts (1.0.1) state the released slot: three focal planes in, the volumetric GS (M19)
  as its baseline.

## [0.01.000], 2026-07-03

### Added
- Adopt the `X.XX.XXX` versioning scheme: a `VERSION` file as the single source of truth, this `CHANGELOG`, and the first git tag. Baseline documenting the current shipped state; later changes are versioned by nature (major/minor/patch).
