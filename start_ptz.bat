@echo off
title PTZ IP Server
cd /d "%~dp0"
echo Spoustim PTZ IP Server...
python "ptz_server.py"
if errorlevel 1 (
  echo.
  echo [!] python se nepodarilo spustit, zkousim py launcher...
  py "ptz_server.py"
)
echo.
echo Server skoncil. Okno muzes zavrit.
pause
