@echo off
REM Jira Timer Tracker - Standalone Runner (Batch version)
REM This script runs the application without installation

echo =================================================
echo    Jira Timer Tracker - Standalone Runner
echo =================================================
echo.

REM Check if Python is installed
python --version > NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X Python not found. Please install Python 3.9 or higher.
    echo   Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✓ Python found

REM Use a temporary virtual environment for running
set TEMP_ENV=.\.temp_venv

REM Check if temp env exists
if exist %TEMP_ENV% (
    echo Temporary environment already exists. Using it.
) else (
    echo Creating temporary virtual environment...
    python -m venv %TEMP_ENV%
    
    if not exist %TEMP_ENV% (
        echo X Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo ✓ Temporary virtual environment created.
)

REM Activate virtual environment
call %TEMP_ENV%\Scripts\activate.bat

REM Check if requirements are installed
if not exist %TEMP_ENV%\Lib\site-packages\PyQt6 (
    echo Installing dependencies (this may take a few minutes)...
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if %ERRORLEVEL% NEQ 0 (
        echo X Failed to install required packages.
        pause
        exit /b 1
    )
    echo ✓ Dependencies installed successfully.
)

REM Create necessary directories
set APP_DATA=%APPDATA%\JiraTimeTracker
if not exist "%APP_DATA%" (
    echo Creating application data directory...
    mkdir "%APP_DATA%"
    mkdir "%APP_DATA%\logs"
    mkdir "%APP_DATA%\attachments"
    echo ✓ Application data directories created.
)

echo.
echo =================================================
echo    Starting Jira Timer Tracker...
echo =================================================
echo.

REM Run the application
python main.py

REM Deactivate the virtual environment when done
call deactivate

pause