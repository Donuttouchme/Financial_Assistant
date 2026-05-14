@echo off
REM Stops Financial Assistant (portable build).
setlocal
set "INSTALL_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\stop.ps1"
