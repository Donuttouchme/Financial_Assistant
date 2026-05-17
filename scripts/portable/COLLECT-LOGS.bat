@echo off
REM Bundles diagnostic info into a single zip on the Desktop. Send this file
REM to whoever is helping you troubleshoot Financial Assistant.
REM
REM Output: %USERPROFILE%\Desktop\FA-diagnostics-<timestamp>.zip
REM Contents: all .log files, environment snapshot, port-8000 holder, install
REM           directory listing, embedded Python version, and the DB schema
REM           (NO transaction rows or any other personal data).

setlocal
set "INSTALL_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%app-scripts\collect-logs.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Failed to collect diagnostics. See message above.
    pause
    exit /b 1
)
pause
