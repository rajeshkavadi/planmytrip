@echo off
REM ===================================================================
REM  Build PlanMyTrip.exe on Windows (double-click this file).
REM  Produces a single self-contained executable at dist\PlanMyTrip.exe
REM  Requirement: Python 3.11+  (https://www.python.org/downloads/)
REM ===================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ============================================
echo   Building PlanMyTrip.exe
echo  ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo  [X] Python not found. Install 3.11+ from https://www.python.org/downloads/
  echo      and tick "Add python.exe to PATH", then re-run this.
  pause & exit /b 1
)

if not exist ".venv" (
  echo  [*] Creating virtual environment...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo  [*] Installing app + build dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
pip install pyinstaller==6.11.1
if errorlevel 1 ( echo  [X] Dependency install failed. & pause & exit /b 1 )

echo  [*] Building the executable (this takes a couple of minutes)...
pyinstaller --clean --noconfirm PlanMyTrip.spec
if errorlevel 1 ( echo  [X] Build failed. See the log above. & pause & exit /b 1 )

echo.
echo  [OK] Done. Your executable is at:
echo         dist\PlanMyTrip.exe
echo.
echo  Double-click it to run PlanMyTrip. It opens http://localhost:8000/
echo.
pause
