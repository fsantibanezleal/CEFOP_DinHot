# The live lane

The live lane re-runs a case in the reader's browser with the reader's values: the method, the device and the traps (the editor adds, drags and deletes them). It is a TypeScript port of the Python engine, written to match
step for step: the same scheme, the same order of operations, the same conventions for centring and scaling.

Status: the TypeScript engine is in development on its own branch and is not on this one, so the paths below are named in prose, not as links. Everything in this page that states a measured number states where it was
measured.

## Shape of the engine

- Location: the frontend's engine folder (`frontend/src/engine`, in a `holo` subfolder), mirroring the Python `core/` and the live methods; each module cites its Python counterpart and the source of its equations.
- FFT: `fft.js` 4.0.4 (Float64, radix-4), pinned exactly. The 2D transform is rows then columns with the same centring and orthonormal scaling as the Python engine. Measured in Node 24: 34.9 ms for a 1024 by 1024 complex 2D
  transform and about 24 ms for a weighted GS iteration at the live grid (256 pixels padded to 512).
- Runs in a Web Worker so the interface never blocks. The worker takes `run` and `cancel` messages, returns progress (per-iteration metrics, at most 30 per second) and a final result with transferable buffers; a new run
  cancels the previous one.
- Optional WebGPU backend for the FFT-form iterations, detected at run time, with the CPU path as the fallback; its agreement with the CPU path is asserted by a browser test run locally and in the gate run, never in Node CI.
  Pages sends no cross-origin isolation headers, so workers are single-threaded and `SharedArrayBuffer` is not used; onnxruntime-web is self-hosted with one thread.
- Live budget: the lane gate gives each case 1500 ms per run and 256 KiB per trace. At the live grid a 30-iteration run of the weighted GS fits.
- Live methods: those whose `SPEC.lane` is `live` or `both` ([method interface](09_method-interface-and-registry.md)); the baked methods (M09, M13, M18, B1, B2, B4, B5 and the training of M17 and B3) are replayed and labelled as
  such. A method that is not ported raises a typed error that the workbench shows as "replayed from the bake", never a silent fallback to another method.

## Browser measurements behind the design

Measured in Chromium 156 driven by Playwright on the development workstation (Intel Core i9-14900HX, 32 logical processors) in the research for this product; one machine, ranges not a single number:

| Quantity | CPU (fft.js, Float64) | WebGPU (Stockham radix-2, float32, Intel UHD adapter) |
|---|---|---|
| 2D FFT 512 by 512 | 7.9 ms (headless shell), 19.7 ms (new headless) | 2.3 ms |
| One weighted GS iteration at 512 by 512 | 27.9 to 58.8 ms | 4.6 ms |
| Agreement with the CPU result | | max error 1.7e-5 to 2.9e-5 of the maximum value (float32) |

The factor of about 2 between the two headless modes on the CPU is a measured variance that was not explained; planning uses the slower. WebGPU was available only in the new headless mode and exposed the integrated GPU, not
the NVIDIA one; mobile, Safari and Firefox timings were not measured.

## What holds it to the Python engine

The Python engine writes reference fixtures (seeded inputs and outputs at small grids and one at the live grid; the engine-reference row of [the contract catalog](../contracts/catalog.md)); the engine's unit tests read them with a
tolerance stated per quantity (for example 1e-9 relative for fields, exact for the random generator and for quantized 8-bit phases). The random generator is held to `tests/fixtures/rng-reference.json`. A change to either engine
that is not made to the other fails the web's tests. The WebGPU path is held to the CPU path in a browser, with a stated tolerance, and is disabled when it disagrees.

## What runs where

- The live engine computes only what the reader changes: a case's method with other values, the device switched, the traps edited. Everything baked stays baked.
- Every view shows its lane: live (computed in the browser) or replay (read from an artifact), and a view that still shows an earlier selection is overlaid as recomputing.
