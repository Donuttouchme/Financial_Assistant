@echo off
REM Financial Assistant launcher (portable build).
REM Sets FA_DB_PATH to %APPDATA%\FinancialAssistant\ so the database survives reinstalls.

setlocal

set "INSTALL_DIR=%~dp0"
set "FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db"

REM Ensure the data directory exists.
if not exist "%APPDATA%\FinancialAssistant" mkdir "%APPDATA%\FinancialAssistant"

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\start.ps1"
