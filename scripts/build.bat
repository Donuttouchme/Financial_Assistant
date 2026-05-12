@echo off
REM Builds the frontend bundle so the spouse-launcher can serve it.
REM Run after `git pull` whenever the developer wants to ship new frontend changes.

pushd "%~dp0\..\frontend"
call npm install
call npm run build
popd
echo Done. Run start.bat or the desktop shortcut to launch.
pause
