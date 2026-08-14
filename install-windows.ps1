<#
  PlanMyTrip - Windows installer / launcher (PowerShell)
  Right-click > "Run with PowerShell", or from a terminal:
      powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
  Requires Python 3.11+. Uses a local SQLite database - no Postgres/Docker.
#>
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  PlanMyTrip - setting up on Windows"        -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# 1. Check Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "[X] Python not found. Install 3.11+ from https://www.python.org/downloads/" -ForegroundColor Red
  Write-Host "    Tick 'Add python.exe to PATH' during setup, then re-run this script."
  Read-Host "Press Enter to exit"; exit 1
}

# 2. Virtual environment (first run only)
if (-not (Test-Path ".venv")) {
  Write-Host "[*] Creating virtual environment..."
  python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"

# 3. Dependencies
Write-Host "[*] Installing dependencies (first run may take a minute)..."
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt

# 4. Seed local SQLite database
Write-Host "[*] Preparing local database (SQLite)..."
python -m app.seed

# 5. Optional live weather refresh (safe if offline)
Write-Host "[*] Refreshing season data from live climate feed (skips if offline)..."
python -m app.refresh

# 6. Launch
Write-Host "`n[OK] Starting PlanMyTrip at http://localhost:8000/  (API docs at /docs)" -ForegroundColor Green
Write-Host "     (Press Ctrl+C to stop.)`n"
Start-Process "http://localhost:8000/"
uvicorn app.main:app --host 127.0.0.1 --port 8000
