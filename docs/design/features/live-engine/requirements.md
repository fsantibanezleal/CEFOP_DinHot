# Requirements: the live engine: the TypeScript port, its worker, cancellation and the WebGPU path

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The live lane of the site is a TypeScript port of the Python engine (`frontend/src/engine/holo/`) that runs in a dedicated Web Worker, so
the interface never blocks (ADR-0054). It ports exactly the methods whose Python `SPEC.lane` is `live` or `both` (15 of 24); any other method
is replayed from the bake and the engine says so with `NotLive`, never a silent fallback. The port is held to the Python engine by parity
tests over fixtures the Python engine writes (`tests/fixtures/engine/*.json`, catalog row `engine-reference`). An optional WebGPU backend runs
the FFT-form iterations on the graphics processor and falls back to the CPU path when it is absent, ineligible or fails, with the reason
recorded. The measured basis (Chromium 153, i9-14900HX: C02 0.49 to 0.80 s of the 1500 ms budget; WebGPU 5 times faster, agreement 3e-5 rad)
is in the SDD, section Lanes. The browser agreement test is `frontend/scripts/engine-browser.mjs`, local only.

| ID | Requirement | Gate |
|---|---|---|
| LE-001 | THE TypeScript random generator SHALL reproduce the committed stream of the Python generator (the unsigned 32-bit words bit for bit, the uniforms exactly, the normals to 1e-15). | `frontend/src/engine/holo/core.parity.test.ts::reproduces the committed rng-reference.json stream` |
| LE-002 | THE TypeScript FFT forward model SHALL be orthonormal and agree with the Python model on the committed fixtures, Parseval included. | `frontend/src/engine/holo/core.parity.test.ts::fft_focal_field (orthonormal, Parseval, pad 2 and 3)` |
| LE-003 | THE TypeScript device model SHALL quantize the phase to the same levels as the Python model, exactly, and to 1e-12 rad. | `frontend/src/engine/holo/device.parity.test.ts::quantize: levels exact, phase to 1e-12` |
| LE-004 | THE live engine SHALL port exactly the methods whose Python `SPEC.lane` is `live` or `both`, so that its method list equals the registry's. | `frontend/src/engine/holo/methods.parity.test.ts::lists exactly the methods whose Python lane is live or both` |
| LE-005 | IF a method is not ported (baked only, or unknown), THEN THE live engine SHALL raise `NotLive` naming it and saying it is replayed from the bake, never fall back to another method. | `frontend/src/engine/holo/methods.parity.test.ts::raises NotLive (never a silent fallback) for a baked-only or unknown method` |
| LE-006 | THE `NotLive` raised in the worker SHALL reach the caller of the engine client as a `NotLive`, not as a plain error. | `frontend/src/engine/holo/worker.test.ts::rejects a method that is not ported with NotLive, never a fallback` |
| LE-007 | WHEN a cancel message arrives, THE worker SHALL stop the run within one iteration. | `frontend/src/engine/holo/worker.test.ts::cancel stops the run within one iteration` |
| LE-008 | THE worker SHALL yield to the event loop after every iteration, so that a message is seen between iterations and the page stays responsive. | `frontend/src/engine/holo/worker.test.ts::yields to the event loop after every iteration (so a message can be seen between iterations)` |
| LE-009 | THE worker SHALL post at most 30 progress messages per second and a final result with the shapes of the contract. | `frontend/src/engine/holo/worker.test.ts::runs a case: progress at most 30 per second, a final result with the shapes of the contract` |
| LE-010 | WHEN the WebGPU backend is absent, ineligible or fails, THE worker SHALL run the CPU path and SHALL record the reason in `fallbackReason`; an explicit `cpu` backend SHALL record none. | `frontend/src/engine/holo/worker.test.ts::runs a case: progress at most 30 per second, a final result with the shapes of the contract` |
| LE-011 | THE fixtures the parity tests read SHALL be written by the Python engine, cover every live method and the core, be reproducible from it, and validate against the `engine-reference` schema. | `tests/contracts/test_documents.py::test_engine_reference_is_reproducible` |
