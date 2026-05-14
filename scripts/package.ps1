# Builds the portable distribution.
# Output: dist/Financial-Assistant-Setup-v<version>.exe
#
# Usage: .\scripts\package.ps1 -Version "1.0"
#
# Requires:
#   - Node.js (already installed for frontend dev)
#   - Inno Setup 6 (ISCC.exe at $env:LOCALAPPDATA\Programs\Inno Setup 6\)
#   - Internet (downloads Python 3.14 embed on first run)

param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$staging = Join-Path $root "dist\portable-staging"
$out = Join-Path $root "dist"

Write-Host "=== Financial Assistant portable build v$Version ==="
Write-Host "root:    $root"
Write-Host "staging: $staging"
Write-Host ""

# 1) Clean staging
if (Test-Path $staging) {
    Write-Host "[1/N] Cleaning staging..."
    Remove-Item -Recurse -Force $staging
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null

# 2) Frontend build
Write-Host "[2/N] Building frontend..."
Push-Location (Join-Path $root "frontend")
try {
    # Run npm commands without 2>&1 redirection - PowerShell 5.1 wraps native
    # stderr lines as NativeCommandError when ErrorActionPreference=Stop.
    # Let warnings print to console; rely on $LASTEXITCODE for failure detection.
    $ErrorActionPreference = "Continue"
    & npm install
    $npmInstallExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($npmInstallExit -ne 0) { throw "npm install failed (exit $npmInstallExit)" }

    $ErrorActionPreference = "Continue"
    & npm run build
    $npmBuildExit = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($npmBuildExit -ne 0) { throw "npm run build failed (exit $npmBuildExit)" }
} finally {
    Pop-Location
    $ErrorActionPreference = "Stop"
}

# 3) Stage frontend dist
Write-Host "[3/N] Staging frontend/dist..."
New-Item -ItemType Directory -Force -Path (Join-Path $staging "frontend") | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "frontend\dist") (Join-Path $staging "frontend\dist")

# 4) Stage backend code (no venv, no DB, no caches)
Write-Host "[4/N] Staging backend code..."
$backendStage = Join-Path $staging "backend"
New-Item -ItemType Directory -Force -Path $backendStage | Out-Null
# Copy everything under backend/, then prune.
Copy-Item -Recurse -Force (Join-Path $root "backend\*") $backendStage -Exclude @(".venv", "financial.db", "financial.db.backup-*", "__pycache__", ".pytest_cache")
# Recursively delete __pycache__ that survived the top-level exclude.
Get-ChildItem -Recurse -Directory -Force -Path $backendStage -Filter "__pycache__" | Remove-Item -Recurse -Force

# 5) Stage app-scripts (start.ps1 + stop.ps1 only - no package.ps1 or build.bat)
Write-Host "[5/N] Staging launcher scripts..."
$appScripts = Join-Path $staging "app-scripts"
New-Item -ItemType Directory -Force -Path $appScripts | Out-Null
Copy-Item (Join-Path $root "scripts\start.ps1") $appScripts
Copy-Item (Join-Path $root "scripts\stop.ps1") $appScripts

# 6) Stage friend-facing root templates (RUN.bat, STOP.bat, README.txt)
Write-Host "[6/N] Staging RUN.bat, STOP.bat, README.txt..."
Copy-Item (Join-Path $root "scripts\portable\RUN.bat") $staging
Copy-Item (Join-Path $root "scripts\portable\STOP.bat") $staging
Copy-Item (Join-Path $root "scripts\portable\README.txt") $staging

Write-Host ""
Write-Host "Stage complete: $staging"
Write-Host "Next steps (later tasks): run Inno Setup."

# 7) Download Python 3.14 embedded distribution
$pythonEmbedUrl = "https://www.python.org/ftp/python/3.14.2/python-3.14.2-embed-amd64.zip"
$cacheDir = Join-Path $root "dist\cache"
$pythonZip = Join-Path $cacheDir "python-3.14.2-embed-amd64.zip"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
if (-not (Test-Path $pythonZip)) {
    Write-Host "[7/N] Downloading Python 3.14 embeddable distribution..."
    Invoke-WebRequest -Uri $pythonEmbedUrl -OutFile $pythonZip
}
else {
    Write-Host "[7/N] Python embed zip cached at $pythonZip - skipping download."
}

# 8) Extract Python embed into staging/python
$pythonStage = Join-Path $staging "python"
Write-Host "[8/N] Extracting Python embed to $pythonStage..."
New-Item -ItemType Directory -Force -Path $pythonStage | Out-Null
Expand-Archive -Path $pythonZip -DestinationPath $pythonStage -Force

# 9) Enable site-packages by editing python314._pth
# The embed distribution ships with `import site` commented out, which
# disables site-packages loading. Uncomment it so pip-installed packages
# are importable.
$pthFile = Get-ChildItem -Path $pythonStage -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) { throw "python._pth not found in $pythonStage" }
Write-Host "[9/N] Enabling site-packages in $($pthFile.Name)..."
$pthContent = Get-Content $pthFile.FullName
$pthContent = $pthContent | ForEach-Object { if ($_ -eq "#import site") { "import site" } else { $_ } }
Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ascii

# 10) Bootstrap pip via get-pip.py
$getPip = Join-Path $cacheDir "get-pip.py"
if (-not (Test-Path $getPip)) {
    Write-Host "[10/N] Downloading get-pip.py..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
}
Write-Host "[10/N] Bootstrapping pip..."
$pythonExe = Join-Path $pythonStage "python.exe"
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $pythonExe $getPip --no-warn-script-location 2>&1 | Out-Null
$ErrorActionPreference = $prevEAP
if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed" }

# 11) Install backend deps into site-packages
Write-Host "[11/N] Installing backend dependencies..."
$ErrorActionPreference = "Continue"
& $pythonExe -m pip install --no-warn-script-location -r (Join-Path $root "backend\requirements.txt") 2>&1 | Out-Null
$ErrorActionPreference = $prevEAP
if ($LASTEXITCODE -ne 0) { throw "pip install -r requirements.txt failed" }

# 12) Smoke-test: can the embed Python import the backend?
# Note: the embeddable distribution's ._pth file controls sys.path and
# ignores PYTHONPATH entirely. We inject the backend path via sys.path.insert
# instead, which matches what uvicorn sees at runtime (WorkingDirectory=backend).
Write-Host "[12/N] Smoke-test: importing backend..."
$backendPathEscaped = (Join-Path $staging "backend").Replace("\", "\\")
$smokeCmd = "import sys; sys.path.insert(0, r'$backendPathEscaped'); import app.main; print('app.main imports OK')"
$ErrorActionPreference = "Continue"
& $pythonExe -c $smokeCmd
$smokeRc = $LASTEXITCODE
$ErrorActionPreference = $prevEAP
if ($smokeRc -ne 0) { throw "Embed-Python smoke test failed" }

Write-Host ""
Write-Host "=== Stage 12 complete. Python embed ready at $pythonStage ==="
