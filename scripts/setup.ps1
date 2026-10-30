# The pipeline environment, isolated and pinned: .venv-pipeline with the precompute and dev requirements. The API
# environment (.venv, requirements-api.txt) is created only when app/ is active. With -Notebooks it builds the
# notebook environment instead, .venv-notebooks from notebooks/requirements.txt (scripts/run_notebooks.py runs in it).
# Idempotent; no global installs.
param([switch]$Notebooks)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }

function Get-VenvPy($dir) {
  $p = Join-Path $dir "Scripts\python.exe"
  if (-not (Test-Path $p)) { $p = Join-Path $dir "bin/python" }
  return $p
}

if ($Notebooks) {
  Write-Host "[setup] .venv-notebooks (the notebook environment)"
  if (-not (Test-Path ".venv-notebooks")) { & $py -m venv .venv-notebooks }
  $vn = Get-VenvPy ".venv-notebooks"
  & $vn -m pip install --upgrade pip -q
  & $vn -m pip install -q -r notebooks/requirements.txt
  Write-Host "[setup] .venv-notebooks ready. Next: python scripts/run_notebooks.py --check"
  exit 0
}

Write-Host "[setup] .venv-pipeline (the offline lane)"
if (-not (Test-Path ".venv-pipeline")) { & $py -m venv .venv-pipeline }
$vp = Get-VenvPy ".venv-pipeline"
& $vp -m pip install --upgrade pip -q
& $vp -m pip install -q -r requirements-precompute.txt -r requirements-dev.txt
Write-Host "[setup] .venv-pipeline ready"

$apiActive = (Test-Path app/main.py) -and (Test-Path requirements-api.txt) -and `
  ((Get-Content requirements-api.txt | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' }).Count -gt 0)
if ($apiActive) {
  Write-Host "[setup] .venv (the API, app/ is active)"
  if (-not (Test-Path ".venv")) { & $py -m venv .venv }
  $vr = Get-VenvPy ".venv"
  & $vr -m pip install --upgrade pip -q
  & $vr -m pip install -q -r requirements-api.txt
  Write-Host "[setup] .venv ready"
}

Write-Host "[setup] done. Next: ./scripts/precompute.ps1 (the canonical bake), then cd frontend; npm ci; npm run dev"
