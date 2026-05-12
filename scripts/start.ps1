# Production-local launcher for Financial Assistant.
# Failure modes show a Windows MessageBox; full details go to scripts/start-error.log.
# Assumes: frontend has been built into frontend/dist (the StaticFiles mount picks it up).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$logPath = Join-Path $PSScriptRoot "start-error.log"

function Fail($message) {
    "[$([DateTime]::Now)] $message" | Out-File -FilePath $logPath -Append -Encoding utf8
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Financial Assistant could not start:`n`n$message`n`nSee $logPath for details.",
        "Financial Assistant",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 1
}

# Pre-check: is port 8000 free?
$portBusy = $null -ne (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue)
if ($portBusy) {
    Fail "Port 8000 is already in use. The app may already be running, or another program is holding the port. Close it from Task Manager and try again."
}

# Build the frontend if dist is missing — cheap to skip when fresh.
if (-not (Test-Path "frontend\dist\index.html")) {
    "[$([DateTime]::Now)] frontend/dist missing - building..." | Out-File -FilePath $logPath -Append -Encoding utf8
    Push-Location frontend
    try {
        & npm install --omit=dev *>&1 | Out-File -FilePath $logPath -Append -Encoding utf8
        & npm run build *>&1 | Out-File -FilePath $logPath -Append -Encoding utf8
        if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed." }
    } finally {
        Pop-Location
    }
}

# Background uvicorn as a child Job.
Push-Location backend
try {
    $job = Start-Job -ScriptBlock {
        param($cwd)
        Set-Location $cwd
        & ".\.venv\Scripts\Activate.ps1"
        & uvicorn app.main:app --port 8000 *>&1
    } -ArgumentList (Get-Location).Path

    # Wait up to 10s for /api/health to respond.
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $r = Invoke-WebRequest "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 1
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }

    if (-not $ready) {
        $output = (Receive-Job $job 2>&1 | Out-String)
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -ErrorAction SilentlyContinue
        Fail "Backend did not respond on http://localhost:8000 within 10 seconds.`n`nLog tail:`n$output"
    }

    # Open the browser.
    Start-Process "http://localhost:8000"

    # Block until the user closes this (hidden) PowerShell window, which kills the job.
    try {
        Wait-Job $job | Out-Null
    } finally {
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -ErrorAction SilentlyContinue
    }
} finally {
    Pop-Location
}
