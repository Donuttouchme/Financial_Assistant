# Production-local launcher for Financial Assistant.
# Assumes: frontend has been built into frontend/dist (the StaticFiles mount will pick it up).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Build the frontend if dist is missing — cheap to skip when fresh.
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "frontend/dist missing — building..."
    Push-Location frontend
    npm install --omit=dev | Out-Null
    npm run build
    Pop-Location
}

# Background uvicorn as a child Job.
Push-Location backend
& ".\.venv\Scripts\Activate.ps1"
$job = Start-Job -ScriptBlock {
    param($cwd)
    Set-Location $cwd
    & ".\.venv\Scripts\Activate.ps1"
    & uvicorn app.main:app --port 8000
} -ArgumentList (Get-Location).Path

# Wait up to 10s for the server.
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $r = Invoke-WebRequest "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
}

if (-not $ready) {
    Write-Host "Backend did not come up — see job output:" -ForegroundColor Red
    Receive-Job $job
    Stop-Job $job
    Remove-Job $job
    Read-Host "Press Enter to exit"
    exit 1
}

# Open the browser.
Start-Process "http://localhost:8000"

Write-Host "Financial Assistant is running on http://localhost:8000"
Write-Host "Close this window to stop the server."

# Stream the server log into this window until the user closes it.
try {
    Wait-Job $job | Out-Null
} finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
}
