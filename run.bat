@echo off
title Accentually Console
cd /d "%~dp0"
echo Starting Accentually...
python quick_accent.py %*
if errorlevel 1 (
    echo.
    echo Accentually exited with an error. See the message above.
) else (
    echo.
    echo Accentually has exited. See the message above.
)
pause
