@echo off
echo ======================================================
echo  Accentually - Disable Start with Windows
echo ======================================================

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "Accentually" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Accentually removed from Windows startup.
) else (
    echo.
    echo [INFO] Accentually was not found in Windows startup.
)
echo.
pause
