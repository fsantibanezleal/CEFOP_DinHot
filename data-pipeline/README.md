# data-pipeline/, the offline engine

The scripts of the product's science, invoked by path (`python data-pipeline/run.py`); the product declares no
package of its own. They run in `.venv-pipeline` (`scripts/setup.sh` or `scripts/setup.ps1`), on a workstation, never in CI.

## Layout

- `pipeline/pipeline.py`: the orchestrator and its CLI (`python data-pipeline/run.py [all|<case>] [--seed N]
  [--output <sandbox>]`)
- `pipeline/registry.py`: the cases, grouped by category, and the default case
- `pipeline/io/`: `contract.py` (contract 1), `formats.py` (readers and writers), `schema.py` (types)
- `pipeline/core/`: `rng.py` (seeded determinism), `trace.py` and `manifest.py` (contract 2), `gate.py` (the lane
  gate), `expect.py` (the expected ranges every result is checked against)
- `pipeline/model/`: the engine (the example is SIR)
- `pipeline/stages/`: preprocess, feature extraction, train, infer, evaluate, export
- `pipeline/cases/`: the cases, each with its bilingual title, category, expected band and expected ranges

See [../docs/architecture/05_precompute-pipeline.md](../docs/architecture/05_precompute-pipeline.md).
