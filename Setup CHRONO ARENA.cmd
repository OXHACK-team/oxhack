@echo off
cd /d "%~dp0"
echo CHRONO ARENA - first-time setup
echo Python 3.11 64-bit and an internet connection are needed for dependencies.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo Setup could not finish. Read the error above, then try again.
    pause
    exit /b 1
)
echo.
echo Ready. Open Launch CHRONO ARENA.cmd or Launch Demo.cmd.
pause
