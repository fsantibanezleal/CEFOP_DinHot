# The staged precompute pipeline

`data-pipeline/pipeline/pipeline.py` orchestrates the **named stages** (frozen names/signatures, rework bodies):

| Stage | Module | Does |
|---|---|---|
| preprocess | `stages/preprocess.py` | read raw → apply **CONTRACT 1** (validate + outlier policy) |
| feature_extraction | `stages/feature_extraction.py` | validated params → feature rows |
| train | `stages/train.py` | fit the model → `models/` (OFFLINE; skippable; EXAMPLE = numpy lstsq surrogate) |
| infer | `stages/infer.py` | run the engine → trace (EXAMPLE = SIR) |
| evaluate | `stages/evaluate.py` | held-out, leakage-safe metrics (R²/RMSE) |
| export | `stages/export.py` | **CONTRACT 2**, compact artifact + manifest |

Run: `python data-pipeline/run.py [all|<case_id>] [--seed N]` (or `scripts/precompute.{sh,ps1}`). It writes
`data/derived/<case>/trace.json` + `data/derived/manifests/<case>.json` + `index.json`.

To instantiate a real product: keep the stage names, replace the bodies, `infer`/`train` call the
research-chosen SOTA engine (pinned in `data-pipeline/requirements.txt`, documented in
[../frameworks/](../frameworks/)). No hand-rolled toy substitute for an engine the research prescribed.
