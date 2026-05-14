@echo off
REM Financial Assistant launcher (portable build).
REM Sets FA_DB_PATH to %APPDATA%\FinancialAssistant\ so the database survives reinstalls.

setlocal

set "INSTALL_DIR=%~dp0"
set "FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db"
set "PYTHON_EXE=%INSTALL_DIR%python\python.exe"

REM Ensure the data directory exists.
if not exist "%APPDATA%\FinancialAssistant" mkdir "%APPDATA%\FinancialAssistant"

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\start.ps1" -PythonExe "%PYTHON_EXE%" -BackendDir "%INSTALL_DIR%backend"
