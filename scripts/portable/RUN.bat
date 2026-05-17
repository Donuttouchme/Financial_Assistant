@echo off
REM Financial Assistant launcher (portable build).
REM Sets FA_DB_PATH to %APPDATA%\FinancialAssistant\ so the database survives reinstalls.
REM Records invocation + PowerShell exit code in app-scripts\launcher.log.
REM Captures PowerShell's stderr to app-scripts\powershell-error.log so a broken
REM start.ps1 that can't reach its own logger still leaves a trace.

setlocal

set "INSTALL_DIR=%~dp0"
set "FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db"
set "PYTHON_EXE=%INSTALL_DIR%python\python.exe"
set "LOG_DIR=%INSTALL_DIR%app-scripts"
set "LAUNCHER_LOG=%LOG_DIR%\launcher.log"
set "PS_ERR_LOG=%LOG_DIR%\powershell-error.log"

REM Ensure dirs exist.
if not exist "%APPDATA%\FinancialAssistant" mkdir "%APPDATA%\FinancialAssistant"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Record invocation. Locale-dependent date/time format is acceptable here;
REM start.ps1 writes ISO-format timestamps for the detailed log lines.
echo [%date% %time%] RUN.bat invoked. INSTALL_DIR=%INSTALL_DIR% >> "%LAUNCHER_LOG%"

REM Run start.ps1. Redirect PS-level stderr to powershell-error.log so launcher
REM failures that prevent start.ps1 from reaching its own logger still leave a
REM trace (execution policy block, syntax error, missing file, etc.).
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\start.ps1" -PythonExe "%PYTHON_EXE%" -BackendDir "%INSTALL_DIR%backend" 2>> "%PS_ERR_LOG%"
set "PS_EXIT=%errorlevel%"

echo [%date% %time%] RUN.bat done. PowerShell exit code: %PS_EXIT% >> "%LAUNCHER_LOG%"
exit /b %PS_EXIT%
