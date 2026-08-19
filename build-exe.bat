@echo off
REM ===================================================================
REM  Build PlanMyTrip.exe on Windows.
REM  Produces a single self-contained executable at dist\PlanMyTrip.exe
REM  Requirement: Python 3.11+  (https://www.python.org/downloads/)
REM
REM  This window ALWAYS stays open at the end (success or failure) so you
REM  can read what happened. If it still closes instantly, run it from an
REM  already-open terminal:  cmd  ->  cd to this folder  ->  build-exe.bat
REM ===================================================================
cd /d "%~dp0"

echo.
echo  ============================================
echo   Building PlanMyTrip.exe
echo  ============================================
echo.

REM --- Detect Python. Prefer the 'py' launcher: it avoids the Microsoft
REM     Store alias that silently breaks virtual-env creation. ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )

if not defined PY (
  echo  [X] Python 3.11+ was not found.
  echo.
  echo      Install it from https://www.python.org/downloads/
  echo      During setup, TICK the box "Add python.exe to PATH".
  echo      If "python" opens the Microsoft Store instead of running, that
  echo      store stub is the problem - install real Python from the link.
  goto :done
)

echo  [*] Using Python: %PY%
%PY% --version
echo.

if not exist ".venv" (
  echo  [*] Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)

echo  [*] Activating environment and installing dependencies...
echo      (First run downloads packages - can take a few minutes.)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :fail
python -m pip install pyinstaller==6.11.1 || goto :fail

echo.
echo  [*] Building the executable now.
echo      THIS TAKES 2-5 MINUTES. Please wait - it is not frozen.
echo.
python -m PyInstaller --clean --noconfirm PlanMyTrip.spec || goto :fail

echo.
echo  ============================================
echo   [OK] SUCCESS
echo  ============================================
echo   Your executable is here:
echo.
echo        %~dp0dist\PlanMyTrip.exe
echo.
echo   Double-click it to run PlanMyTrip (opens http://localhost:8000/).
goto :done

:fail
echo.
echo  ============================================
echo   [X] BUILD FAILED
echo  ============================================
echo   Scroll UP in this window to read the actual error.
echo   Common causes: no internet for the package download, or an
echo   antivirus blocking PyInstaller. Copy the error text if you need help.

:done
echo.
echo  --- This window will stay open. Press any key to close it. ---
pause >nul
