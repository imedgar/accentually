@echo off
echo ======================================================
echo  QuickAccent - Disable Start with Windows
echo ======================================================

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "QuickAccent" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] QuickAccent removed from Windows startup.
) else (
    echo.
    echo [INFO] QuickAccent was not found in Windows startup.
)
echo.
pause
