@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%~dp0launcher.py"
  exit /b
)
where pyw >nul 2>nul
if not errorlevel 1 (
  start "" pyw -3 "%~dp0launcher.py"
  exit /b
)
echo Python 3.11 oder neuer wird benoetigt. Danach START.cmd erneut oeffnen.
pause
