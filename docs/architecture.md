# Architecture

- [01, overview](architecture/01_overview.md): what DinHot is and is not, the lanes, the physics chain, the flow, what holds it
- [02, determinism and the trace](architecture/02_determinism-and-trace.md): the portable generator, byte-identical artifacts, the compact trace
- [03, the gates](architecture/03_the-gate.md): the lane gate, the expected ranges, the units gate, the web gate
- [04, the live lane](architecture/04_live-lane.md): the TypeScript engine, the Web Worker, the WebGPU backend, the parity tests
- [05, the staged pipeline](architecture/05_precompute-pipeline.md): the stages, the bake, the commands
- [06, model evaluation](architecture/06_model-evaluation.md): the scorer, the benchmark protocol, the oracles, the learned models
- [07, deploy](architecture/07_deploy.md): GitHub Pages, the checks before and after, CI
- [08, the data contracts](architecture/08_data-contracts.md): contract 1, contract 2, the model slots, missing data as a state
- [09, the method interface and registry](architecture/09_method-interface-and-registry.md): the module contract every method follows

The binding decisions are ADR-0054 (committed artifacts are the evidence, the live lane re-runs the engine), ADR-0057 (the archetype), ADR-0058 (the architecture modal), ADR-0069 (one complete vertical per method), ADR-0071 (the UI floor),
ADR-0074 (the CI budget), ADR-0075 (the SDD), ADR-0078 (rules live in the base) and ADR-0080 (contract-first parallel delivery), in the CAOS conventions.
