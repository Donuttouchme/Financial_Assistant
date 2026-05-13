@echo off
REM Financial Assistant stop script - kills the listener on port 8000.
REM Double-click target for a "Quit Financial Assistant" desktop shortcut.

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0stop.ps1"
