param([switch]$Install, [switch]$Gpu, [switch]$Notebooks, [switch]$Release, [string]$FromStage,
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$Extra)
$ErrorActionPreference = 'Stop'
$python = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
  if ($Install -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    $ErrorActionPreference = 'Continue'
    & winget install --id Python.Python.3.12 --exact
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host 'Python installed. Open a new terminal and rerun 00_install-prereqs.'
    exit 0
  }
  Write-Error 'Python is missing. Run 00_install-prereqs.ps1 -Install or install Python>=3.12.'
  exit 1
}
$arguments = @((Join-Path $PSScriptRoot 'local/workflow.py'), 'generate')
if ($Install) { $arguments += '--install' }
if ($Gpu) { $arguments += '--gpu' }
if ($Notebooks) { $arguments += '--notebooks' }
if ($Release) { $arguments += '--release' }
if ($FromStage) { $arguments += @('--from-stage', $FromStage) }
$arguments += $Extra
# Native warnings on stderr do not change a successful exit status in Windows PowerShell 5.1.
$ErrorActionPreference = 'Continue'
& $python @arguments
exit $LASTEXITCODE
