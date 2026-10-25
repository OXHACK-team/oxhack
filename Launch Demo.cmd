@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First-time setup is needed in this folder.
    echo Double-click "Setup CHRONO ARENA.cmd", then launch again.
    echo Python 3.11 64-bit is required.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py --demo --windowed %*
if errorlevel 1 pause
