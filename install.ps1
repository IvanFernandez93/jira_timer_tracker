# PowerShell Installation Script for Jira Timer Tracker
# Author: Ivan Fernandez
# Date: September 23, 2025

# Stop on first error
$ErrorActionPreference = "Stop"

# Display welcome message
Write-Host "===================================================" -ForegroundColor Green
Write-Host "   Jira Timer Tracker - Installation Script" -ForegroundColor Green
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

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    
    if (-not (Test-Path ".\.venv")) {
        Write-Host "✗ Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "✓ Using existing virtual environment." -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Check activation worked
if (-not $env:VIRTUAL_ENV) {
    Write-Host "✗ Failed to activate virtual environment." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Virtual environment activated." -ForegroundColor Green

# Install requirements
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install --upgrade pip
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install required packages." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Dependencies installed successfully." -ForegroundColor Green

# Create necessary directories
$appDataPath = Join-Path $env:APPDATA "JiraTimeTracker"
if (-not (Test-Path $appDataPath)) {
    Write-Host "Creating application data directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $appDataPath | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $appDataPath "logs") | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $appDataPath "attachments") | Out-Null
    Write-Host "✓ Application data directories created." -ForegroundColor Green
} else {
    Write-Host "✓ Application data directories already exist." -ForegroundColor Green
}

# Create desktop shortcut
$WshShell = New-Object -comObject WScript.Shell
$shortcutPath = Join-Path $WshShell.SpecialFolders("Desktop") "Jira Timer Tracker.lnk"

if (-not (Test-Path $shortcutPath)) {
    Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PWD\run.ps1`""
    $Shortcut.WorkingDirectory = $PWD
    $Shortcut.IconLocation = "$PWD\resources\icons\app_icon.ico"
    $Shortcut.Save()
    Write-Host "✓ Desktop shortcut created." -ForegroundColor Green
} else {
    Write-Host "✓ Desktop shortcut already exists." -ForegroundColor Green
}

# Create Start Menu shortcut
$programsPath = Join-Path $WshShell.SpecialFolders("Programs") "Jira Timer Tracker"
$startMenuShortcutPath = Join-Path $programsPath "Jira Timer Tracker.lnk"

# Create program folder if it doesn't exist
if (-not (Test-Path $programsPath)) {
    Write-Host "Creating Start Menu folder..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $programsPath | Out-Null
}

if (-not (Test-Path $startMenuShortcutPath)) {
    Write-Host "Creating Start Menu shortcut..." -ForegroundColor Cyan
    $Shortcut = $WshShell.CreateShortcut($startMenuShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PWD\run.ps1`""
    $Shortcut.WorkingDirectory = $PWD
    $Shortcut.IconLocation = "$PWD\resources\icons\app_icon.ico"
    $Shortcut.Save()
    Write-Host "✓ Start Menu shortcut created." -ForegroundColor Green
} else {
    Write-Host "✓ Start Menu shortcut already exists." -ForegroundColor Green
}

# Create run script
$runScriptPath = Join-Path $PWD "run.ps1"
if (-not (Test-Path $runScriptPath)) {
    Write-Host "Creating launcher script..." -ForegroundColor Cyan
    @"
# Jira Timer Tracker Launcher
Set-Location "$PWD"
& .\.venv\Scripts\Activate.ps1
python main.py
"@ | Out-File -FilePath $runScriptPath -Encoding utf8
    Write-Host "✓ Launcher script created." -ForegroundColor Green
} else {
    Write-Host "✓ Launcher script already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To run Jira Timer Tracker:"
Write-Host "1. Double-click the desktop shortcut, or" -ForegroundColor Yellow
Write-Host "2. Run the following commands from this directory:" -ForegroundColor Yellow
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Thank you for installing Jira Timer Tracker!" -ForegroundColor Green

# Optional: Launch the application after installation
$launchNow = Read-Host "Would you like to launch Jira Timer Tracker now? (y/n)"
if ($launchNow -eq 'y') {
    & .\.venv\Scripts\python.exe .\main.py
}