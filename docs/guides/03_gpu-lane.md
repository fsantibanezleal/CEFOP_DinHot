# Guide: the GPU lane

DinHot has two different uses of a GPU and neither is required to run the product.

## Offline: training the two learned models

Training of the unsupervised CNN hologram (M17) and the learned warm start (B3) runs on the workstation GPU (design bounds: at most 7 GB of GPU memory and 8 GB of host memory, at most 3 hours, at most 10 MB of ONNX models and
metrics committed). It is local and offline: never in CI, never in the browser (ADR-0069, ADR-0074).

1. The CUDA build and the training stack are pinned in `requirements-gpu.txt`, which extends the pipeline requirements; the index URL of the CUDA build and the verified driver and runtime matrix are recorded in that file by the learned-methods work (the file is a placeholder until then).
2. Install them in a GPU environment of their own, never into the pipeline environment: `python -m venv <venv root>/<name>`, then `pip install -r requirements-gpu.txt` in it.
3. Datasets and checkpoints live in the data root and the training root (a faster local drive for active training), never in the repository; when training ends the results move to the data root and the fast copy is deleted. Only
   the released ONNX files, their cards and the metrics document are committed.
4. Evaluation is on held-out geometries written before training; a model that does not meet its acceptance criterion is not released ([model evaluation](../architecture/06_model-evaluation.md)).

The committed artifacts are produced offline regardless of lane, so the site deploys as a static replay with the released models or, while none is released, with the baselines (GS for the CNN slot, the random start for the warm-start slot).

## In the browser: the WebGPU backend of the live engine

The live engine has an optional WebGPU backend for the FFT-form iterations, detected at run time, with the CPU path as the fallback ([the live lane](../architecture/04_live-lane.md)). It is not a pipeline GPU lane: the pipeline never needs it,
and a browser without WebGPU, or with a disagreeing result, uses the CPU path.
