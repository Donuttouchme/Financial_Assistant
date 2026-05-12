@echo off
REM Financial Assistant launcher — invokes the PowerShell script with a hidden window.
REM Double-click target for the desktop shortcut.

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start.ps1"
