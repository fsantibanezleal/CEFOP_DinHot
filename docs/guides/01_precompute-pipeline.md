# Guide: run the precompute pipeline

The offline lane bakes the fourteen cases with every method valid for each, runs the benchmark protocol and writes the readiness document. It runs on the workstation, never in CI (ADR-0074).

## Set up

```bash
./scripts/setup.sh            # or scripts/setup.ps1: builds .venv-pipeline and installs the pinned requirements
```

The environment is isolated and pinned (`requirements-precompute.txt` and `requirements-dev.txt`); nothing is installed globally. The notebooks have their own environment (`./scripts/setup.sh --notebooks`).

## Bake

```bash
./scripts/precompute.sh                                   # the canonical bake of the fourteen cases, then the benchmark (resumable)
./scripts/precompute.sh C02_grid_feedback --output <sandbox>   # one case into a sandbox
./scripts/precompute.sh benchmark --seeds 20 --workers 12 --resume   # the benchmark alone
./scripts/precompute.sh readiness                          # recompute the readiness document from the catalog
./scripts/smoke.sh                                         # contract 2 check: index, manifests and artifacts consistent
```

On Windows use the `.ps1` twins. The canonical bake writes `data/derived/` and is a release operation: tests and smoke runs pass `--output` to a folder in the temp root so that they cannot change the committed evidence. A bake
that finds a result outside its case's expected range, a trace over 256 KiB, a mislabelled lane or an observable in the wrong units fails, naming the case, the method and the metric
([the gates](../architecture/03_the-gate.md)). `--allow-missing-methods` bakes the methods that exist into a sandbox and is never canonical.

## Test

```bash
.venv-pipeline/bin/python -m pytest          # Scripts/python.exe on Windows
```

The engine tests are in `tests/engine/` (forward models, device, Zernike, trap physics, dynamics, camera, random generator, registry), the method acceptance tests in `tests/methods/` (one file per method, grouped by
`baseline`, `control`, `optim` and `beyond`), the producer tests in `tests/bake/`, `tests/contracts/` and `tests/test_*.py`, the planted defects in `tests/adversarial/`. The whole suite runs in at most 10 minutes on the
workstation; the plants also run in CI.

## What a run produces

`data/derived/` holds the case index, one manifest and one trace per baked case, the benchmark results, the model metrics and the readiness document. The run is deterministic in `(params, seed)`: the same seed gives
byte-identical artifacts ([determinism and the trace](../architecture/02_determinism-and-trace.md)). The stages and their roles are in
[the staged pipeline](../architecture/05_precompute-pipeline.md).
