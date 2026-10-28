@echo off
echo ======================================================
echo  Accentually - Enable Start with Windows
echo ======================================================
cd /d "%~dp0"

set "VBS_PATH=%~dp0run_background.vbs"
set "CMD_STR=wscript.exe \"%VBS_PATH%\""

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "QuickAccent" /t REG_SZ /d "%CMD_STR%" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Accentually has been added to Windows startup!
    echo It will now run silently in the background whenever you log in.
) else (
    echo.
    echo [ERROR] Failed to add startup registry entry.
)
echo.
pause
