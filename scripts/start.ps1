# Production-local launcher for Financial Assistant.
#
# Every step writes a timestamped line to app-scripts/launcher.log (append mode,
# rotated when it exceeds 1 MB). Any uncaught error is logged and shown to the
# user via a MessageBox that includes the log path.
#
# When invoked from RUN.bat: -PythonExe + -BackendDir point at the embedded
# interpreter and installed backend. When invoked from scripts/start.bat in the
# dev tree (no params): falls back to the venv's uvicorn.exe shim and ./backend.
#
# IMPORTANT: keep this file pure ASCII. package.ps1's parse-check reads it as
# ANSI; non-ASCII bytes (em-dash, curly quote) get mojibaked and the staged
# script becomes unparseable.

param(
    [string]$PythonExe = "",
    [string]$BackendDir = ""
)

$ErrorActionPreference = "Stop"

# --- Path setup -----------------------------------------------------------
$root        = Split-Path -Parent $PSScriptRoot
if (-not $BackendDir) { $BackendDir = Join-Path $root "backend" }

$logDir      = $PSScriptRoot
$launcherLog = Join-Path $logDir "launcher.log"
$uvOutLog    = Join-Path $logDir "uvicorn-stdout.log"
$uvErrLog    = Join-Path $logDir "uvicorn-stderr.log"

$uvExitCode = $null

# --- Logging --------------------------------------------------------------
$logSizeBudgetBytes = 1MB

function Rotate-Log($path) {
    if ((Test-Path $path) -and ((Get-Item $path).Length -gt $logSizeBudgetBytes)) {
        $rotated = "$path.1"
        if (Test-Path $rotated) { Remove-Item $rotated -Force -ErrorAction SilentlyContinue }
        Move-Item $path $rotated -Force -ErrorAction SilentlyContinue
    }
}

function Write-LogLine($level, $msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$level] $msg"
    try {
        $line | Out-File -FilePath $launcherLog -Append -Encoding utf8
    } catch {
        # Logging itself failed - last-ditch console write, no exit.
        Write-Host $line
    }
}

function LogI($msg) { Write-LogLine "INFO"  $msg }
function LogW($msg) { Write-LogLine "WARN"  $msg }
function LogE($msg) { Write-LogLine "ERROR" $msg }

function Show-MessageBox($title, $message, $icon) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $message, $title,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::$icon
    ) | Out-Null
}

function Fail($message) {
    LogE $message

    # Auto-bundle diagnostics so the user (or whoever is helping them) has
    # everything in one zip without having to know about COLLECT-LOGS.bat.
    # Wrapped in its own try/catch: if collection fails, still show the
    # MessageBox with the original failure reason.
    $zipNote = ""
    try {
        $collectScript = Join-Path $PSScriptRoot "collect-logs.ps1"
        if (Test-Path $collectScript) {
            $desktop = [Environment]::GetFolderPath("Desktop")
            $stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
            $autoZip = Join-Path $desktop "FA-diagnostics-$stamp.zip"
            LogI "Auto-collecting diagnostics to $autoZip"
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $collectScript -OutZip $autoZip 2>&1 |
                ForEach-Object { LogI "[collect-logs] $_" }
            if (Test-Path $autoZip) {
                $zipNote = "`n`nA diagnostics zip was created on your Desktop:`n$autoZip`n`nSend that file to whoever is helping you."
                LogI "Auto-collected diagnostics: $autoZip"
            } else {
                LogW "collect-logs.ps1 ran but the zip is missing at $autoZip"
                $zipNote = "`n`nA diagnostics zip could not be created automatically. Try running COLLECT-LOGS.bat from:`n$root"
            }
        } else {
            LogW "collect-logs.ps1 not found at $collectScript"
            $zipNote = "`n`nTo send logs, double-click COLLECT-LOGS.bat in:`n$root"
        }
    } catch {
        LogE "Auto-collect failed: $($_.Exception.Message)"
        $zipNote = "`n`nAuto-collect failed. Try running COLLECT-LOGS.bat from:`n$root"
    }

    $userMessage = "Financial Assistant could not start.`n`nReason:`n$message`n`nDiagnostics location:`n$logDir$zipNote"
    Show-MessageBox "Financial Assistant" $userMessage "Error"
    exit 1
}

# Stop a process and all descendants. Stop-Process leaks grandchildren on Windows
# so we shell out to taskkill instead. Locally drop EAP=Stop because PS 5.1 wraps
# native-command stderr as NativeCommandError and would re-throw "process not
# found" into our top-level catch when the PID is already dead (e.g., uvicorn
# exited naturally and finally{} still runs the cleanup).
function Stop-Tree($processId) {
    if ($processId) {
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & taskkill.exe /T /F /PID $processId 2>&1 | Out-Null
        } finally {
            $ErrorActionPreference = $prevEAP
        }
    }
}

# --- Main body wrapped in try/catch ---------------------------------------
try {
    Rotate-Log $launcherLog
    Rotate-Log $uvOutLog
    Rotate-Log $uvErrLog

    LogI "================================================================="
    LogI "Launcher started. PID=$PID"
    LogI "PSVersion=$($PSVersionTable.PSVersion)  OS=$([System.Environment]::OSVersion.VersionString)"
    LogI "User=$env:USERNAME  Computer=$env:COMPUTERNAME"
    LogI "InstallRoot=$root"
    LogI "BackendDir=$BackendDir (exists=$(Test-Path $BackendDir))"
    if ($PythonExe) {
        LogI "PythonExe=$PythonExe (exists=$(Test-Path $PythonExe))"
    } else {
        LogI "PythonExe=(unset; will use dev venv uvicorn.exe)"
    }
    LogI "FA_DB_PATH=$env:FA_DB_PATH"
    if ($env:FA_DB_PATH) {
        LogI "DB exists=$(Test-Path $env:FA_DB_PATH)"
    }

    Set-Location $root
    LogI "WorkingDir=$(Get-Location)"

    # --- Port pre-check ---------------------------------------------------
    LogI "Checking port 8000 availability..."
    $listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $holderPid = ($listeners | Select-Object -First 1).OwningProcess
        $holderName = (Get-Process -Id $holderPid -ErrorAction SilentlyContinue).ProcessName
        LogW "Port 8000 already held by PID=$holderPid (Process=$holderName)."

        # Is it our own backend? /api/health returns {status:ok} only in our app.
        $oursAlready = $false
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200 -and $r.Content -match '"status"\s*:\s*"ok"') {
                $oursAlready = $true
            }
        } catch {
            LogI "Health probe of existing listener failed: $($_.Exception.Message)"
        }

        if ($oursAlready) {
            LogI "Existing listener is our app. Opening a fresh browser tab."
            $launchToken = [DateTimeOffset]::Now.ToUnixTimeSeconds()
            Start-Process "http://localhost:8000/?v=$launchToken"
            LogI "Browser launched against existing instance. Exiting."
            exit 0
        }

        Fail "Port 8000 is already in use by another program (PID=$holderPid, Process=$holderName). Close it from Task Manager and try again."
    }
    LogI "Port 8000 is free."

    # --- Frontend build (no-op in installed builds; dist ships in installer) ---
    if (-not (Test-Path "frontend\dist\index.html")) {
        LogW "frontend\dist\index.html missing - running npm build..."
        Push-Location frontend
        try {
            & npm install --omit=dev *>&1 | ForEach-Object { LogI "[npm] $_" }
            if ($LASTEXITCODE -ne 0) { Fail "npm install failed (exit $LASTEXITCODE)" }
            & npm run build *>&1 | ForEach-Object { LogI "[npm] $_" }
            if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed (exit $LASTEXITCODE)" }
        } finally {
            Pop-Location
        }
        LogI "Frontend build complete."
    } else {
        LogI "Frontend dist present (skipping build)."
    }

    # --- Resolve uvicorn command -----------------------------------------
    if ($PythonExe) {
        if (-not (Test-Path $PythonExe)) {
            Fail "Embedded Python not found at $PythonExe. The portable install may be corrupt - try reinstalling."
        }
        $uvicornCmd = $PythonExe
        $uvicornArgs = @("-m", "uvicorn", "app.main:app", "--port", "8000")
    } else {
        $uvicornExe = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
        if (-not (Test-Path $uvicornExe)) {
            Fail "uvicorn not found at $uvicornExe. Create the dev venv: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
        }
        $uvicornCmd = $uvicornExe
        $uvicornArgs = @("app.main:app", "--port", "8000")
    }
    LogI "Uvicorn command: $uvicornCmd $($uvicornArgs -join ' ')"
    LogI "Uvicorn working dir: $BackendDir"
    LogI "Uvicorn stdout -> $uvOutLog"
    LogI "Uvicorn stderr -> $uvErrLog"

    # Mark start-of-run in the uvicorn logs (append mode keeps prior runs).
    $marker = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] === Launcher PID=$PID starting uvicorn ==="
    Add-Content -Path $uvOutLog -Value $marker -Encoding utf8
    Add-Content -Path $uvErrLog -Value $marker -Encoding utf8

    # --- Spawn uvicorn ---------------------------------------------------
    $uv = Start-Process -FilePath $uvicornCmd `
        -ArgumentList $uvicornArgs `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $uvOutLog `
        -RedirectStandardError $uvErrLog `
        -PassThru
    LogI "Uvicorn started. PID=$($uv.Id)"

    try {
        # --- Health poll -------------------------------------------------
        # Use 127.0.0.1 explicitly: `localhost` resolves to ::1 first on Windows,
        # but uvicorn binds only to 127.0.0.1, and PS 5.1's Invoke-WebRequest
        # doesn't do Happy Eyeballs - each `localhost` attempt burns its full
        # TimeoutSec on the IPv6 failure.
        $ready = $false
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        for ($i = 1; $i -le 20; $i++) {
            Start-Sleep -Milliseconds 500
            if ($uv.HasExited) {
                LogE "Uvicorn exited before becoming ready (exit code $($uv.ExitCode))."
                break
            }
            try {
                $r = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 1
                if ($r.StatusCode -eq 200) {
                    $sw.Stop()
                    LogI "Health probe succeeded on attempt $i (after $($sw.ElapsedMilliseconds) ms)."
                    $ready = $true
                    break
                }
            } catch {
                # Expected during startup window. Log every 5th attempt to keep noise down.
                if (($i % 5) -eq 0) {
                    LogI "Health probe attempt ${i}: still waiting ($($_.Exception.Message))."
                }
            }
        }

        if (-not $ready) {
            $tail = if (Test-Path $uvErrLog) {
                (Get-Content $uvErrLog -Tail 50 | Out-String).Trim()
            } else {
                "(no uvicorn output captured)"
            }
            LogE "Uvicorn did not become ready. Stderr tail (last 50 lines):"
            LogE $tail
            Stop-Tree $uv.Id
            Fail "Backend did not respond on http://127.0.0.1:8000 within 10 seconds. See app-scripts\uvicorn-stderr.log for details."
        }

        # --- Launch browser ----------------------------------------------
        # `localhost` is fine here - browsers handle dual-stack. The query string
        # is a cache-buster: even with no-cache headers, browsers restore from
        # bfcache on relaunch and skip the network entirely. A unique URL forces
        # a fresh load.
        $launchToken = [DateTimeOffset]::Now.ToUnixTimeSeconds()
        Start-Process "http://localhost:8000/?v=$launchToken"
        LogI "Browser launched against http://localhost:8000/?v=$launchToken"

        # Block until uvicorn exits.
        LogI "Waiting for uvicorn to exit..."
        Wait-Process -Id $uv.Id
        $uvExitCode = $uv.ExitCode
        LogI "Uvicorn exited (exit code $uvExitCode)."
    } finally {
        Stop-Tree $uv.Id
    }
} catch {
    $err = $_
    $stack = if ($err.ScriptStackTrace) { $err.ScriptStackTrace } else { "(no stack trace)" }
    LogE "Uncaught exception: $($err.Exception.Message)"
    LogE "Stack trace:"
    LogE $stack
    Fail "Unexpected error: $($err.Exception.Message)"
}

# Propagate uvicorn's exit code so RUN.bat can act on it (exit 75 = "please
# relaunch me", used by the backup-restore flow to re-enter the lifespan
# startup with a freshly staged DB).
if ($null -ne $uvExitCode) {
    exit $uvExitCode
}
