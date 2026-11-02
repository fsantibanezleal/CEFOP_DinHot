#!/usr/bin/env bash
# Run the offline pipeline in .venv-pipeline. With no arguments: the canonical bake of the fourteen cases, then the benchmark
# protocol (resumable), then the readiness document. With arguments they pass through to data-pipeline/run.py, for example
#   ./scripts/precompute.sh C02_grid_feedback --output "$CAOS_TEMP_ROOT/bake"      one case into a sandbox
#   ./scripts/precompute.sh benchmark --seeds 20 --workers 12 --resume   the benchmark alone
# Never in CI (ADR-0074).
set -euo pipefail
cd "$(dirname "$0")/.."
VP=".venv-pipeline/bin/python"; [ -x "$VP" ] || VP=".venv-pipeline/Scripts/python.exe"
if [ "$#" -gt 0 ]; then
  "$VP" data-pipeline/run.py "$@"
else
  "$VP" data-pipeline/run.py all
  "$VP" data-pipeline/run.py benchmark --resume
fi
