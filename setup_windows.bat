@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo AuraX Music Bot - Windows setup
 echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher not found. Install Python 3.11 from https://www.python.org/downloads/windows/ and enable Add Python to PATH.
  pause
  exit /b 1
)
py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 is required. Install Python 3.11, then rerun this file.
  pause
  exit /b 1
)
if not exist .venv py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist .env copy .env.example .env >nul
echo.
echo Setup complete. Edit .env with your credentials, then run run_bot.bat.
echo FFmpeg must also be installed and available on PATH for music playback.
pause
exit /b 0
:failed
echo ERROR: Package installation failed. Check internet, Python version, and the error above.
pause
exit /b 1
