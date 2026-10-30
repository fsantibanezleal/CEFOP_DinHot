# L03, onnxruntime-web (inference of the two learned models in the browser)

## What and why

onnxruntime-web 1.31.1 runs the ONNX graphs of the two model slots (cgh-net and warmstart-model) in the reader's browser, with the WebAssembly provider self-hosted and a single thread. A hand-written inference was rejected: the
shared runtime is tested and versioned. Training stays offline and local ([guide 03](../guides/03_gpu-lane.md)); only the released graph and its card are shipped.

## Install (exact, verified)

Pinned exactly at 1.31.1 in the frontend package manifest (`npm ci` in `frontend/`); the Python side uses the same major runtime to check that a released graph equals the training framework's output to 1e-5. The WebAssembly file is
the largest file of the site (the build is bounded at 30 MB).

## Usage

The graph input and output names, shapes and dtypes are fixed by the model-slot contract: cgh-net takes `target` float32 [1, 1, 128, 128] and returns `phase` float32 [1, 1, 128, 128]; warmstart-model takes `traps` float32 [1, 1024, 4]
and `mask` float32 [1, 1024] and returns `trap_phase` float32 [1, 1024] ([the data contracts](../architecture/08_data-contracts.md)). Only operators that the WebAssembly provider supports may appear in a released graph, and the
opset is stated in the model card.

## Applying it here

M17 and B3 ([M17](M17_unsupervised-cnn-hologram.md), [B3](B3_learned-warm-start.md)) infer through it; B3's predicted phases then feed the ported phase-fixed WGS. When no valid released model exists the baseline answers and the views say so.

## Caveats and licence

- GitHub Pages sends no cross-origin isolation headers, so `SharedArrayBuffer` and multi-threaded WebAssembly are unavailable: the number of threads is 1.
- Inference timings in the browser are not measured yet and are not quoted. The licence of the runtime was not re-read for this card (UNVERIFIED here); see [ATTRIBUTION](../../ATTRIBUTION.md).
