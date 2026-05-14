# Stops Financial Assistant by killing whatever process tree is listening on port 8000.
# Companion to start.bat so the user doesn't need Task Manager to quit.
# Writes scripts/stop.log every run so failures can be diagnosed after the fact.

$ErrorActionPreference = "Continue"
$logPath = Join-Path $PSScriptRoot "stop.log"

function Log($msg) {
    "[$([DateTime]::Now)] $msg" | Out-File -FilePath $logPath -Append -Encoding utf8
}

function Show($message, $icon = "Information") {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $message,
        "Financial Assistant",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::$icon
    ) | Out-Null
}

Log "=== stop.ps1 invoked ==="

$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $listeners) {
    Log "No listener on port 8000."
    Show "Financial Assistant is not running."
    exit 0
}

$killed = @()
foreach ($listener in $listeners) {
    $procId = $listener.OwningProcess
    Log "Listener PID $procId - running taskkill /T /F."
    $out = & taskkill.exe /T /F /PID $procId 2>&1
    $code = $LASTEXITCODE
    Log "taskkill PID=$procId exit=$code output=$out"
    $killed += "PID $procId (exit $code)"
}

Start-Sleep -Milliseconds 700
$killedSummary = $killed -join ", "
$still = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($still) {
    $stillPid = ($still | Select-Object -First 1).OwningProcess
    Log "FAILURE: port 8000 still held after kill attempt (now PID $stillPid)."
    Show "Could not stop the listener on port 8000.`n`nKilled: $killedSummary`nStill held by: PID $stillPid`n`nSee $logPath for details." "Error"
    exit 1
}

Log "SUCCESS: port 8000 free."
Show "Financial Assistant stopped.`n`nKilled: $killedSummary."
