# Changelog

All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is
tagged.

## [0.02.000], unreleased

### Changed

- Re-instantiated from CAOS_PRODUCT_TEMPLATE 0.12.000 into this repository, history kept: the pipeline, the two
  contracts, the lanes, the workbench on the shared shell, the six routes, the guards and the measured gate. The
  FastAPI and WebSocket application, its vanilla JavaScript frontend and the legacy DinHotSys C++ sources and
  binaries leave the tree; they stay in the git history (tag v0.01.000).

### Added

- The App: the workbench of DinHot (five groups and the Context write-up, a trap editor, the live and replay lanes with their labels, Focus mode,
  the two learned model slots in the browser with their baselines) and the removal of the template's example engine.
- The live engine: a TypeScript port of the forward models, the device model and fifteen methods in a Web Worker, held to the Python engine by
  parity tests, with an optional WebGPU backend that falls back to the CPU path and records why.
- Case C13, the disordered array of 819 traps, so the bake holds thirteen cases (twelve baked, C11 refused by contract 1); the cases bake in
  parallel; the expected ranges are measured on three seeds.
- The learned slots: `cgh-net` (M17) released with its ONNX graph and card, `warmstart-model` (B3) tested and refuted, each with its baseline.
- The specification of eleven features with a gate per requirement and an adversarial check per requirement (`docs/design/features/`), and the
  planted-defect tests that run each gate with its defect (`tests/adversarial/plant_run.py`); the measured resources
  (`docs/design/measured-resources.md`).
- The three method tiers: classical, state of the art and five proposals beyond it (BS-1 to BS-5; BS-3 refuted, BS-4 negative on pointing).

## [0.01.000], 2026-07-03

### Added
- Adopt the `X.XX.XXX` versioning scheme: a `VERSION` file as the single source of truth, this `CHANGELOG`, and the first git tag. Baseline documenting the current shipped state; later changes are versioned by nature (major/minor/patch).
