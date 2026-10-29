# The staged precompute pipeline

`data-pipeline/pipeline/pipeline.py` orchestrates the named stages (their names and signatures are frozen by the base; the bodies are DinHot's). Every stage is deterministic, typed, seeded and independently testable.

| Stage | Module | Does |
|---|---|---|
| preprocess | `data-pipeline/pipeline/stages/preprocess.py` | read the source document of cases (`data/examples/cases.json`, else the registry's twelve default records) and apply **contract 1**: schema plus the rules a schema cannot state; a rejected record carries its reason, a suspicious one is flagged |
| feature_extraction | `data-pipeline/pipeline/stages/feature_extraction.py` | the derived geometry of a validated record (trap count, extent in micrometres, smallest spacing in focal bins, the fraction of the unaliased half field the farthest trap uses) |
| train | `data-pipeline/pipeline/stages/train.py` | the offline training of the two learned models (cgh-net, warmstart-model): local GPU, never CI. The body on this branch is still the template's placeholder, which the pipeline does not call; the learned-methods work replaces it |
| infer | `data-pipeline/pipeline/stages/infer.py` | run every method valid for a case through the registry, with the same seed and budget for all, and score each independently with `core/score.py`; also the camera, particle and rearrangement drivers (`feedback.py`, `dynamics.py`, `rearrangement.py`) |
| evaluate | `data-pipeline/pipeline/stages/evaluate.py` | the held-out metrics of the model slots; same state as train |
| export | `data-pipeline/pipeline/stages/export.py` | **contract 2**: the compact trace and the case manifest, with the lane and gate verdicts, the flags, the verdict per method and the model slots behind the metrics |
| benchmark | `data-pipeline/pipeline/stages/benchmark.py` | the benchmark protocol over the method registry ([model evaluation](06_model-evaluation.md)); owner of the benchmark-results row |

The per-case bake (`data-pipeline/pipeline/bake.py`) runs, in order: contract-1 record, methods through the registry, expected ranges, lane measurement, maps and drivers, trace within the byte gate, units gate, manifest. It
never raises for a method or a gate problem, so one bad case does not hide the others: failures are collected and a `BakeFailed` names case, method or driver and metric at the end.

## Run

```
python data-pipeline/run.py                           # all cases, then the readiness document
python data-pipeline/run.py C02_grid_feedback         # one case
python data-pipeline/run.py all --only C01_square_grid,C12_calibration --output <sandbox>
python data-pipeline/run.py all --resume              # skip cases whose manifest has the same inputs and version
python data-pipeline/run.py benchmark [--seeds 20] [--workers 12] [--reduced] [--only G1,G2] [--methods M04,M06]
python data-pipeline/run.py readiness                 # recompute data/derived/readiness.json from the catalog
python data-pipeline/run.py cases                     # write data/examples/cases.json from the registry
python data-pipeline/run.py units                     # the units gate over the shipped artifacts
```

The canonical bake is an explicit release operation, never in CI (ADR-0074). Tests and smoke runs pass `--output` so that they cannot mutate the committed evidence; `--allow-missing-methods` bakes the methods present into a
sandbox and is never canonical. The scripts `scripts/precompute.sh` and `scripts/precompute.ps1` wrap the commands. Outputs: `data/derived/` (index, manifests, one trace per case, the benchmark results, the model metrics, the
readiness document).

## Resources

The bake runs on the workstation, never in CI: at most 4 GB peak, at most 3 MB of artifacts, at most 20 minutes for the fourteen cases; the benchmark at most 6 hours, resumable by cell. These are bounds from the design; the
measured values replace them in [`design/measured-resources.md`](../design/measured-resources.md) before a release.

## Where a method plugs in

A method is a module with `SPEC` and `run`; adding one to the ladder needs no change to the pipeline ([method interface](09_method-interface-and-registry.md)). The engine lives in
`data-pipeline/pipeline/model/holo/`, documented card by card in [frameworks](../frameworks.md). It is not a package of its own (ADR-0057). No hand-rolled substitute stands in for a method the research prescribed.
