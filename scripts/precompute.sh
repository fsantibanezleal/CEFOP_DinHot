#!/usr/bin/env bash
# Run the offline pipeline in .venv-pipeline (pass-through args). E.g.:  ./scripts/precompute.sh <case-id> --seed 7
set -euo pipefail
cd "$(dirname "$0")/.."
VP=".venv-pipeline/bin/python"; [ -x "$VP" ] || VP=".venv-pipeline/Scripts/python.exe"
"$VP" data-pipeline/run.py "$@"
