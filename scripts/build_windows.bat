@echo off
REM Build PeerCode.exe (onefile, windowed) and the setup installer.
setlocal
cd /d "%~dp0.."

echo [1/3] Building web UI...
pushd webapp
call npm run build || goto :fail
popd

echo [2/3] Building PeerCode.exe...
pyinstaller --noconfirm --onefile --windowed --name PeerCode ^
  --icon "assets\PeerCode.ico" ^
  --add-data "web;web" ^
  --add-data "backend;backend" ^
  --hidden-import aiohttp ^
  --hidden-import websockets ^
  --hidden-import watchdog.observers ^
  --hidden-import watchdog.events ^
  --collect-all webview ^
  --collect-all clr_loader ^
  --collect-all pythonnet ^
  app.py || goto :fail

echo [3/3] Building installer...
where iscc >nul 2>nul
if %errorlevel%==0 (
  iscc installer\PeerCode.iss
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer\PeerCode.iss
) else (
  echo Inno Setup not found - skipping installer. Install from https://jrsoftware.org/isinfo.php
)
echo Done. See dist\PeerCode.exe and dist\installer\PeerCode-Setup.exe
exit /b 0

:fail
echo Build failed.
exit /b 1
