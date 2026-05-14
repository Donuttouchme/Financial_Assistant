# Financial Assistant v{VERSION}

Local-first personal finance tracker. Empty DB on first run; data stored in `%APPDATA%\FinancialAssistant\financial.db` (preserved across upgrades and uninstall).

## Install

1. Download `Financial-Assistant-Setup-v{VERSION}.exe` below.
2. Double-click. If Windows shows "Windows protected your PC", click **More info** → **Run anyway** (the installer is unsigned — one-time message).
3. Accept the installer defaults. A browser window will open automatically.

## Stop / quit

* The app auto-stops after 1 hour of inactivity.
* To stop manually: Start menu → **Stop Financial Assistant**.

## Update

Download the newer installer and run it. Your data in `%APPDATA%\FinancialAssistant\` is preserved.

## What's new

* (list changes here per release)

## Known issues

* SmartScreen warning on first install (unsigned). Working as expected — click "Run anyway".

## Bug reports

If something goes wrong, attach these files from the install dir:
* `app-scripts\uvicorn-stderr.log`
* `app-scripts\start-error.log`
* `app-scripts\stop.log`
