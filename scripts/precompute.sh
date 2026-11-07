#!/usr/bin/env bash
set -euo pipefail
entry_dir="$(cd "$(dirname "$0")" && pwd)"
python_command="${PYTHON:-python3}"
if ! command -v "$python_command" >/dev/null 2>&1; then
  if [ "${1:-}" = "--install" ] && command -v brew >/dev/null 2>&1; then
    brew install python@3.12
    echo "Python installed. Open a new terminal and rerun 00_install-prereqs."
    exit 0
  fi
  echo "Python is missing; install Python>=3.12 and rerun 00_install-prereqs." >&2
  exit 1
fi
exec "$python_command" "$entry_dir/local/workflow.py" generate "$@"
