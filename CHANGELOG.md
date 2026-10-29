# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.02.000], unreleased

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

### Fixed

- M06 and M07 project the start hologram's field with the initial weights (g0 = 1): from the same start they now equal slmsuite 0.5.0's
  WGS-Leonardo and WGS-Kim at feedback exponent 1 to four digits (`tests/methods/baseline/test_m06_against_slmsuite.py`,
  `test_m07_against_slmsuite.py`), in Python, TypeScript and WGSL; the beyond methods' GS family runs those rules instead of a copy, and the
  claims that rest on them were re-measured (BS-1, BS-2 over 8 and 6 seeds, BS-4, BS-5).
- The benchmark lists a cell whose method refuses the geometry as skipped with the method's reason, instead of stopping the run.
- A released model without onnxruntime refuses to run instead of answering with its baseline under the learned method's id.
- The cgh-net, warmstart-model and model-metrics contracts (1.0.1) state the released slot: three focal planes in, the volumetric GS (M19)
  as its baseline.

## [0.01.000], 2026-07-03

### Added
- Adopt the `X.XX.XXX` versioning scheme: a `VERSION` file as the single source of truth, this `CHANGELOG`, and the first git tag. Baseline documenting the current shipped state; later changes are versioned by nature (major/minor/patch).
