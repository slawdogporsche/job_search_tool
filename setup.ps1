# Windows PowerShell. Creates .venv, installs deps, initializes git.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .git)) {
  git init -q; git add -A; git commit -qm "Initial commit: job search tool"
}
Write-Host "`nDone. Activate with:  .\.venv\Scripts\Activate.ps1"
