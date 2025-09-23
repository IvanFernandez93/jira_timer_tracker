````markdown
# Jira Time Tracker (desktop)

Quick start
-----------

### Option 1: Full Installation

1. Install requirements:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

2. Run the app:

```powershell
python main.py
```

### Option 2: Using the Installation Script

Run the installation script which will set up a virtual environment, install dependencies, and create shortcuts:

```powershell
.\install.ps1
```

### Option 3: Standalone Execution (No Installation)

For running the app without installation, use one of the standalone scripts:

- PowerShell version:
```powershell
.\run_standalone.ps1
```

- Batch version (for Command Prompt):
```batch
run_standalone.bat
```

These scripts will create a temporary virtual environment, install required dependencies, and run the application directly.

3. Run tests:

```powershell
python -m pytest -q
```

Running tests locally (Windows)
------------------------------

Use the provided PowerShell helper `run_tests.ps1` to create a virtual environment, install development dependencies and run tests:

```powershell
# create venv and run tests (first time)
./run_tests.ps1

# or run steps manually:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pytest -q
```

Note: Tests use `pytest-qt` which requires a Qt runtime (PyQt6). If you see errors about missing Qt packages, install PyQt6 before running tests:

```powershell
python -m pip install PyQt6
```

Configuration notes
-------------------
- Settings are stored in the local SQLite DB in table `AppSettings` (key/value).
- Important keys you can set:
  - `JIRA_URL`: Jira base URL used to connect.
  - `jira/max_retries`, `jira/base_retry_delay`, `jira/max_delay` for retry policy.
  - `jira/non_retryable_statuses` as CSV for HTTP codes to treat as non-retryable.
  - `log_level`, `log_max_bytes`, `log_backup_count` for logging.

Developer notes
---------------
- Tests rely on `pytest` (see `requirements-dev.txt`).
- `services/jira_service.py` exposes `_with_retries` and accepts an injectable `sleep_func` to allow fast unit tests.

If you want, I can prepare a PR summary or package these changes into a release note.
