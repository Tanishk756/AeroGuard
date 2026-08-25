$repoRoot = Split-Path -Parent $PSScriptRoot
$venvActivate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'

if (-not (Test-Path $venvActivate)) {
    throw "Virtual environment not found at $venvActivate. Run .\scripts\setup-venv.ps1 first."
}

& $venvActivate
Write-Host "AeroGuard virtual environment activated."
Write-Host "Use .\.venv\Scripts\python.exe for backend commands."
