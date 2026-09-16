@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Install Python 3.12 or newer from python.org, then run this file again.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
 echo Installation failed. Check your internet connection and Python version.
 pause
 exit /b 1
)
.venv\Scripts\python.exe start-local.py
pause
