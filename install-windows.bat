@echo off
REM ===================================================================
REM  PlanMyTrip - Windows installer / launcher
REM  Double-click this file. It sets up everything and starts the app.
REM  Only requirement: Python 3.11+  (https://www.python.org/downloads/)
REM  Uses a local SQLite database - no Postgres/Docker needed.
REM ===================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ============================================
echo   PlanMyTrip - setting up on Windows
echo  ============================================
echo.

REM --- 1. Check Python ---
where python >nul 2>&1
if errorlevel 1 (
  echo  [X] Python was not found on your PATH.
  echo      Install Python 3.11+ from https://www.python.org/downloads/
  echo      and tick "Add python.exe to PATH" during setup, then re-run this.
  echo.
  pause
  exit /b 1
)

REM --- 2. Create virtual environment (first run only) ---
if not exist ".venv" (
  echo  [*] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 ( echo  [X] Failed to create venv. & pause & exit /b 1 )
)

call ".venv\Scripts\activate.bat"

REM --- 3. Install dependencies ---
echo  [*] Installing dependencies (first run may take a minute)...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 ( echo  [X] Dependency install failed. & pause & exit /b 1 )

REM --- 4. Seed the local database ---
echo  [*] Preparing local database (SQLite)...
python -m app.seed
if errorlevel 1 ( echo  [X] Seeding failed. & pause & exit /b 1 )

REM --- 5. (optional) refresh live weather; safe if offline ---
echo  [*] Refreshing season data from live climate feed (skips if offline)...
python -m app.refresh

REM --- 6. Launch ---
echo.
echo  [OK] Starting PlanMyTrip at http://localhost:8000/docs
echo       (Close this window or press Ctrl+C to stop.)
echo.
start "" "http://localhost:8000/docs"
uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
