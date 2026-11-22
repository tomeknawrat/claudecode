@echo off
title PTZ IP Server
cd /d "%~dp0"

REM --- Najdi funkcni Python (nejdriv "python", jinak "py" launcher) ---
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 set "PY=py"
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo [!] Python nenalezen. Nainstaluj Python 3 z https://www.python.org/ a spust znovu.
  pause
  exit /b 1
)

REM --- Doinstaluj chybejici knihovny (jen pokud chybi) ---
REM websockets = nutny; pystray + pillow = volitelne (ikonka v systemove liste).
REM Kdyz jsou vsechny, instalace se preskoci a start je rychly.
%PY% -c "import websockets, pystray, PIL" >nul 2>&1
if errorlevel 1 (
  echo Instaluji chybejici knihovny ^(websockets, pystray, pillow^)...
  %PY% -m pip install --disable-pip-version-check websockets pystray pillow
  echo.
)

echo Spoustim PTZ IP Server...
%PY% "ptz_server.py"

echo.
echo Server skoncil. Okno muzes zavrit.
pause
