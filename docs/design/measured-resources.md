# Measured resources of DinHot

The committed evidence behind the numbers that [`SDD.md`](SDD.md) states in the Resources, the Lanes and the Deploy driver. Each section
says who measured it, on what, and where the measurement can be repeated. The measuring machine is the development workstation (Windows 11,
Intel Core i9-14900HX, 48 GB RAM, RTX 4070 Laptop 8 GB, Python 3.13, Node 24); the browser is Chromium 153.0.8010.12 driven by Playwright
1.63. Sizes are bytes of file content. A figure that was measured by a unit of the build and is not repeated here is marked with the unit that
holds its report in the coordination records; nothing below is quoted from a paper.

## Stored size of the committed artifacts

Measured on 2026-10-28 on the tree of the release branch.

```
$ find data/derived -type f | xargs du -cb | tail -1
2046947	total
$ find data/derived -type f | wc -l
33
$ ls -l models/cgh-net.onnx
4671540
```

`data/derived/` holds 2,046,947 bytes (1.95 MiB) in 33 files: the thirteen cases (twelve baked, one refused), the index, the manifests
(245,687 bytes together), the traces, the benchmark results (39,636 bytes), the model metrics and the readiness. The twelve traces together hold
1,701,463 bytes (1,661.6 KiB); the largest is C03, the 32x32 lattice, with 258,681 bytes, under the lane gate's 262,144 bytes (256 KiB), and the
next is C13 with 217,494 bytes. The released graph `models/cgh-net.onnx` holds 4,671,540 bytes (4.46 MiB), under the 5 MB per file the base-integrity
guard allows. The SDD's bound of 3 MB of artifacts and 256 KiB per trace holds.

## The bake: time and memory

Measured by unit I1 (`changes/i1.md`, now in this record) with `python data-pipeline/run.py all --allow-missing-methods --workers 12` on the
workstation (12 workers, 13 GB of RAM free):

| measurement | value |
|---|---|
| canonical bake, 11 cases in parallel, C11 refused, idle machine | 515 s (8 min 36 s) |
| the same bake while the machine ran other jobs | 761 s |
| the slowest cases | C05 514 s, C08 354 s, C02 347 s |
| the sequential bake of the first sandbox run | 5,084 s |
| peak working set of one case process | 322 MB; the 11 processes together under 3.6 GB |
| measurement of the expected ranges, 3 seeds, 33 case bakes | 1,813 s |
| case C13 alone: ranges run (3 seeds, 3 workers) / canonical bake (1 worker) | 504 s / about 450 s |

The Resources row of the SDD says about 9 minutes and 4 GB on 12 cores for the thirteen cases. One case per process is the unit of
parallelism; the methods of a case run in sequence.

## The live engine: median time of one run

Measured by unit T1 (`changes/t1.md`, now in this record): 30 iterations of M07 on the 256 x 256 padded-2 grid, a warm run, in the dedicated
Web Worker, CPU path, the whole run including the scoring from the final phase, in Chromium 153.

| case | traps | form | time |
|---|---|---|---|
| C02, the default case | 100, off bin | point-trap | 0.49 to 0.80 s depending on the browser mode and the machine load; inside the 1500 ms budget |
| C03, the large array | 1,024, off bin | point-trap | 2.4 to 4.3 s; outside the budget (Node on the same machine: 0.55 s; the factor between the worker and Node is a measured variance of this laptop) |
| C03 as measured by unit I1 in another run | 1,024, off bin | point-trap | 1.0 to 3.5 s in Chromium, against 0.49 to 0.80 s for the on-bin C02 |

The FFT of the engine (fft.js, Float64, radix 4) measured 34.9 ms for a 1024 squared complex transform in Node 24, and a weighted GS iteration
at the live grid (256 squared padded to 512 squared) about 24 ms in Node 24. The cases C01, C02 and C03 sit on integer-bin lattices so that the
FFT form applies and the live lane keeps its 1500 ms budget.

WebGPU (Intel gen-12lp adapter, Chromium new headless mode only): 30 iterations of M07 on the same cases with the traps moved onto FFT bins take
0.31 to 0.32 s against 1.5 to 1.6 s on the CPU in that mode, 5 times faster. Agreement with the CPU path: 3e-5 rad after one iteration, 5e-7 in
efficiency and 9e-5 relative in the trap intensities after thirty. The GPU path holds two `nFft^2` complex float32 buffers (4 MB at 512 squared) and
a few trap-sized buffers, released when the run ends or is cancelled; the point-trap plan caches at most `M n <= 2e6` factors (32 MB). These
numbers are repeated by `frontend/scripts/engine-browser.mjs` (real Worker and WebGPU in Chromium, local, never in Node CI).

## Training the learned model

The training record `data/derived/models/cgh-net-training.json` (unit M1) holds the configuration and the sizes of `cgh-net`: 16,000 steps of
batch 32, learning rate 0.001, 14 channels, at most 2.2 hours, 4,671,540 bytes of ONNX at opset 17. The graph agrees with the training
framework on the reconstructed focal intensity to a relative 8.4e-6 (the card states 1e-5). On 162 held-out volumes the median accuracy against GS is
1.140 (quartiles 1.102 and 1.160), and one solve takes a median 7,486 ms in the comparison that gave it (`data/derived/models/metrics.json`).
The slot `warmstart-model` was trained and rejected: `data/derived/models/warmstart-model-rejected.json` records the measured negative.

## The site: build and deploy payload

The deploy payload is the build of `frontend/` plus the committed artifacts copied by `frontend/scripts/copy-data.mjs`; the largest single file
is the onnxruntime WASM binary. The SDD bound is 30 MB uploaded to GitHub Pages. This record is updated with the measured size of
`frontend/dist` by the release check (`npm run build`), whose output is not committed.
