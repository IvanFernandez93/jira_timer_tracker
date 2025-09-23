# Jira Timer Tracker - Standalone Runner Script
# This script runs the application without installation
# Author: Ivan Fernandez
# Date: September 23, 2025

# Stop on first error
$ErrorActionPreference = "Stop"

# Display welcome message
Write-Host "===================================================" -ForegroundColor Green
Write-Host "   Jira Timer Tracker - Standalone Runner" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = (python --version 2>&1)
    Write-Host "✓ Found Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "✗ Python not found. Please install Python 3.9 or higher." -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check Python version meets minimum requirements
$versionPattern = "Python (\d+)\.(\d+)\.(\d+)"
if ($pythonVersion -match $versionPattern) {
    $majorVersion = [int]$Matches[1]
    $minorVersion = [int]$Matches[2]
    
    if (($majorVersion -lt 3) -or ($majorVersion -eq 3 -and $minorVersion -lt 9)) {
        Write-Host "✗ Python version must be 3.9 or higher. Found $majorVersion.$minorVersion" -ForegroundColor Red
        exit 1
    }
}

# Use a temporary virtual environment for running
$tempEnvDir = ".\.temp_venv"

# Check if we should create a new venv or use an existing one
$createNewEnv = $true

if (Test-Path $tempEnvDir) {
    $answer = Read-Host "Temporary environment already exists. Recreate? (y/n, default: n)"
    if ($answer -ne 'y') {
        $createNewEnv = $false
        Write-Host "Using existing temporary environment." -ForegroundColor Yellow
    } else {
        Write-Host "Recreating temporary environment..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force $tempEnvDir
    }
}

if ($createNewEnv) {
    # Create temporary virtual environment
    Write-Host "Creating temporary virtual environment..." -ForegroundColor Cyan
    python -m venv $tempEnvDir
    
    if (-not (Test-Path $tempEnvDir)) {
        Write-Host "✗ Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Temporary virtual environment created." -ForegroundColor Green

    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $tempEnvDir\Scripts\Activate.ps1

    # Check activation worked
    if (-not $env:VIRTUAL_ENV) {
        Write-Host "✗ Failed to activate virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment activated." -ForegroundColor Green

    # Install requirements
    Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Cyan
    pip install --upgrade pip
    pip install -r requirements.txt

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install required packages." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Dependencies installed successfully." -ForegroundColor Green
} else {
    # Just activate the existing environment
    Write-Host "Activating existing virtual environment..." -ForegroundColor Cyan
    & $tempEnvDir\Scripts\Activate.ps1
    
    # Check activation worked
    if (-not $env:VIRTUAL_ENV) {
        Write-Host "✗ Failed to activate virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment activated." -ForegroundColor Green
}

# Create necessary directories if they don't exist
$appDataPath = Join-Path $env:APPDATA "JiraTimeTracker"
if (-not (Test-Path $appDataPath)) {
    Write-Host "Creating application data directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $appDataPath | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $appDataPath "logs") | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $appDataPath "attachments") | Out-Null
    Write-Host "✓ Application data directories created." -ForegroundColor Green
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "   Starting Jira Timer Tracker..." -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

# Run the application
python main.py

# Deactivate the virtual environment when done
deactivate