<#
PowerShell helper to create a virtual environment, install development requirements
and run pytest for this project on Windows.
#>
param(
    [switch]$Recreate
)

set-StrictMode -Version Latest

$venvDir = "$PSScriptRoot\.venv"

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }

if ($Recreate -and (Test-Path $venvDir)){
    Write-Info "Removing existing venv..."
    Remove-Item -Recurse -Force $venvDir
}

if (!(Test-Path $venvDir)){
    Write-Info "Creating virtual environment in $venvDir"
    python -m venv $venvDir
}


# Use the venv's python directly to avoid relying on shell activation
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
if (!(Test-Path $venvPython)){
    Write-Error "Virtualenv python not found at $venvPython"
    exit 2
}

Write-Info "Upgrading pip in venv"
& "$venvPython" -m pip install --upgrade pip

Write-Info "Installing development requirements into venv"
Write-Info "Installing runtime requirements into venv"
& "$venvPython" -m pip install -r "$PSScriptRoot\requirements.txt"
if ($LASTEXITCODE -ne 0){
    Write-Error "Failed to install runtime requirements from requirements.txt"
    exit 4
}

Write-Info "Installing development requirements into venv"
& "$venvPython" -m pip install -r "$PSScriptRoot\requirements-dev.txt"

Write-Info "Running pytest (via venv python)"
# Ensure a Qt binding is available for pytest-qt (PyQt6 preferred)
Write-Info "Ensuring PyQt6 is installed for pytest-qt"
& "$venvPython" -m pip install PyQt6
if ($LASTEXITCODE -ne 0){
    Write-Error "Failed to install PyQt6 automatically. You may need to install it manually: & $venvPython -m pip install PyQt6"
    exit 3
}

& "$venvPython" -m pytest -q

if ($LASTEXITCODE -ne 0){
    Write-Error "pytest reported failures (exit code $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Info "All tests passed"
