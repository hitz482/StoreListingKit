# One-command local setup on Windows (PowerShell): .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest -q
Write-Host "Done. Start the app with: .\.venv\Scripts\python -m storelistingkit"
