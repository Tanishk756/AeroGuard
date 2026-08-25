$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot '.venv'
$pythonExe = (Get-Command python -ErrorAction Stop).Source

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating project-local virtual environment at $venvPath"
    & $pythonExe -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists at $venvPath"
}

Write-Host "Virtual environment ready."
Write-Host "Use: .\scripts\activate-venv.ps1"
Write-Host "Then install backend dependencies with: .\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt"
