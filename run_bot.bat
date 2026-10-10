@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo ERROR: Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist .env (
  echo ERROR: .env file missing. Copy .env.example to .env and fill in the required values.
  pause
  exit /b 1
)
.venv\Scripts\python.exe preflight.py
if errorlevel 1 (
  pause
  exit /b 1
)
.venv\Scripts\python.exe bot.py
pause
