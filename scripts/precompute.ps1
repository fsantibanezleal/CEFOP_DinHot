# Run the offline pipeline in .venv-pipeline (pass-through args). E.g.:  ./scripts/precompute.ps1 <case-id> --seed 7
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$vp = Join-Path ".venv-pipeline" "Scripts\python.exe"
if (-not (Test-Path $vp)) { $vp = Join-Path ".venv-pipeline" "bin/python" }
& $vp data-pipeline/run.py @args
