# Stops Financial Assistant by killing whatever process tree is listening on port 8000.
# Companion to start.bat so the user doesn't need Task Manager to quit.

$ErrorActionPreference = "Continue"

function Show($message, $icon = "Information") {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $message,
        "Financial Assistant",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::$icon
    ) | Out-Null
}

$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Show "Financial Assistant is not running."
    exit 0
}

foreach ($listener in $listeners) {
    & taskkill.exe /T /F /PID $listener.OwningProcess 2>&1 | Out-Null
}

Start-Sleep -Milliseconds 500
if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Show "Could not stop the listener on port 8000. Open Task Manager and end 'python.exe'." "Error"
    exit 1
}
Show "Financial Assistant stopped."
