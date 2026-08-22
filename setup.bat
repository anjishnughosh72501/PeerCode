@echo off
setlocal EnableDelayedExpansion
rem ============================================================
rem  PeerCode one-command setup for Windows
rem  Installs every dependency and launches the app from source.
rem  Works on a fresh clone - no prebuilt artifacts required.
rem ============================================================
cd /d "%~dp0"

echo [PeerCode] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Be sure to tick "Add Python to PATH" during installation.
    pause & exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" || (
    echo ERROR: Python 3.9 or newer is required.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python -c "import sys; print('%d.%d' ^%% (sys.version_info[0], sys.version_info[1]))"') do set PYVER=%%i
echo Found Python !PYVER!

echo [PeerCode] Creating virtual environment...
if not exist .venv (
    python -m venv .venv || (echo ERROR: failed to create venv & pause & exit /b 1)
)
call .venv\Scripts\activate.bat

echo [PeerCode] Installing backend dependencies...
python -m pip install --upgrade pip >nul
pip install -r backend\requirements.txt || (echo ERROR: dependency installation failed & pause & exit /b 1)

rem Optional: native desktop window (falls back to your browser without it)
pip install pywebview >nul 2>nul || echo [PeerCode] pywebview unavailable - the UI will open in your browser instead.

echo [PeerCode] Building web UI...
where npm >nul 2>nul
if not errorlevel 1 (
    pushd webapp
    call npm install --no-audit --no-fund || (popd & echo ERROR: npm install failed & pause & exit /b 1)
    call npm run build || (popd & echo ERROR: web build failed & pause & exit /b 1)
    popd
) else (
    echo Node.js not found - using the prebuilt web bundle in web\.
)

echo.
echo ============================================
echo   PeerCode is ready! Starting it now...
echo   The UI opens at http://127.0.0.1:7432/
echo ============================================
echo.
python app.py
endlocal
