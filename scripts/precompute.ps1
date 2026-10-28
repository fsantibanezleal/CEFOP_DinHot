# Run the offline pipeline in .venv-pipeline. With no arguments: the canonical bake of the twelve cases, then the benchmark
# protocol (resumable), then the readiness document. With arguments they pass through to data-pipeline/run.py, e.g.
#   ./scripts/precompute.ps1 C02_grid_feedback --output "$env:CAOS_TEMP_ROOT/bake"      one case into a sandbox
#   ./scripts/precompute.ps1 benchmark --seeds 20 --workers 12 --resume   the benchmark alone
# Never in CI (ADR-0074).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$vp = Join-Path ".venv-pipeline" "Scripts\python.exe"
if (-not (Test-Path $vp)) { $vp = Join-Path ".venv-pipeline" "bin/python" }
if ($args.Count -gt 0) {
  & $vp data-pipeline/run.py @args
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
  & $vp data-pipeline/run.py all
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $vp data-pipeline/run.py benchmark --resume
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
