# Production-local launcher for Financial Assistant.
# Failure modes show a Windows MessageBox; full details go to scripts/start-error.log
# and scripts/uvicorn-stderr.log (uvicorn writes its INFO output to stderr).
# Assumes: frontend has been built into frontend/dist (the StaticFiles mount picks it up).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$logPath = Join-Path $PSScriptRoot "start-error.log"
$uvOutLog = Join-Path $PSScriptRoot "uvicorn-stdout.log"
$uvErrLog = Join-Path $PSScriptRoot "uvicorn-stderr.log"

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

# Kills a process and all descendants. Used on shutdown / failure so we don't
# leave an orphan uvicorn holding port 8000 — Stop-Process only kills the direct
# PID and leaks grandchildren on Windows.
function Stop-Tree($processId) {
    if ($processId) {
        & taskkill.exe /T /F /PID $processId 2>&1 | Out-Null
    }
}

# Pre-check: is port 8000 free? Filter to State=Listen — leftover client sockets
# from a previous run sit in FinWait2/TimeWait for ~30s and would otherwise make
# this look busy when no one is actually listening.
$portBusy = $null -ne (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
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

# Resolve the venv's uvicorn launcher directly. Bypasses Activate.ps1 (which
# can hit ExecutionPolicy issues inside background jobs) and gives us a real
# PID we can track + kill the tree of on failure.
$uvicornExe = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicornExe)) {
    Fail "uvicorn not found at $uvicornExe. The backend virtualenv may be missing. Run: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
}

# Truncate previous uvicorn logs so the tail-on-failure only reflects this run.
"" | Out-File -FilePath $uvOutLog -Encoding utf8
"" | Out-File -FilePath $uvErrLog -Encoding utf8

$uv = Start-Process -FilePath $uvicornExe `
    -ArgumentList "app.main:app","--port","8000" `
    -WorkingDirectory (Join-Path $root "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $uvOutLog `
    -RedirectStandardError $uvErrLog `
    -PassThru

try {
    # Wait up to 10s for /api/health. Use 127.0.0.1 explicitly — `localhost` resolves
    # to ::1 first on Windows, but uvicorn binds only to 127.0.0.1, and PS 5.1's
    # Invoke-WebRequest doesn't do Happy Eyeballs, so each `localhost` attempt
    # burns its full TimeoutSec on the IPv6 failure.
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        if ($uv.HasExited) { break }
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 1
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }

    if (-not $ready) {
        $tail = if (Test-Path $uvErrLog) { Get-Content $uvErrLog -Tail 30 | Out-String } else { "(no uvicorn output captured)" }
        Stop-Tree $uv.Id
        Fail "Backend did not respond on http://127.0.0.1:8000 within 10 seconds.`n`nLog tail:`n$tail"
    }

    # Open the browser with a per-launch cache-buster query.
    # Reason: even with no-cache headers, browsers restore the previous session's
    # tab from memory / bfcache and skip the network entirely on relaunch — so
    # the user sees the old UI until they manually reload. A unique query string
    # forces a fresh URL on every launch, which the browser can't satisfy from
    # cache. `localhost` is fine here — browsers handle dual-stack.
    $launchToken = [DateTimeOffset]::Now.ToUnixTimeSeconds()
    Start-Process "http://localhost:8000/?v=$launchToken"

    # Block until uvicorn exits.
    Wait-Process -Id $uv.Id
} finally {
    Stop-Tree $uv.Id
}
