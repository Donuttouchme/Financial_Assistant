# Diagnostic bundler. Run via COLLECT-LOGS.bat from the install root.
# Produces FA-diagnostics-<timestamp>.zip on the user's Desktop.
#
# What goes in:
#   - All *.log files from app-scripts/ (launcher, uvicorn-stdout/stderr, powershell-error, stop)
#   - environment.txt: OS/PS version, install paths, port 8000 holder, embedded
#     Python version, install-dir file listing (top-level + app-scripts + backend depth 2)
#   - db-schema.txt: sqlite_master + row counts (NO row contents)
#
# Pure ASCII only - this script is also subject to package.ps1's parse-check.

param(
    [string]$OutZip = ""
)

$ErrorActionPreference = "Continue"

$appScripts  = $PSScriptRoot
$installRoot = Split-Path -Parent $PSScriptRoot
$desktop     = [Environment]::GetFolderPath("Desktop")
$stamp       = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $OutZip) {
    $OutZip = Join-Path $desktop "FA-diagnostics-$stamp.zip"
}
$outZip = $OutZip

$tmp = Join-Path ([System.IO.Path]::GetTempPath()) "fa-diag-$([Guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

Write-Host "Collecting diagnostics..."

try {
    # 1) Copy all log files
    Write-Host "  - Copying log files..."
    Get-ChildItem -Path $appScripts -Filter "*.log*" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName -Destination $tmp -Force -ErrorAction SilentlyContinue
    }

    # 2) Environment snapshot
    Write-Host "  - Gathering environment info..."
    $report = [System.Collections.Generic.List[string]]::new()
    $report.Add("=== Financial Assistant Diagnostics ===")
    $report.Add("Timestamp:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    $report.Add("OS:           $([System.Environment]::OSVersion.VersionString)")
    $report.Add("PowerShell:   $($PSVersionTable.PSVersion)")
    $report.Add("User:         $env:USERNAME")
    $report.Add("Computer:     $env:COMPUTERNAME")
    $report.Add("InstallRoot:  $installRoot")
    $report.Add("")
    $report.Add("=== Database location ===")
    $dbPath = Join-Path $env:APPDATA "FinancialAssistant\financial.db"
    $report.Add("Expected at:  $dbPath")
    $report.Add("Exists:       $(Test-Path $dbPath)")
    if (Test-Path $dbPath) {
        $dbInfo = Get-Item $dbPath
        $report.Add("Size:         $($dbInfo.Length) bytes")
        $report.Add("LastWrite:    $($dbInfo.LastWriteTime)")
    }
    $report.Add("")
    $report.Add("=== Port 8000 ===")
    $listeners = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($listeners) {
        foreach ($l in $listeners) {
            $procName = (Get-Process -Id $l.OwningProcess -ErrorAction SilentlyContinue).ProcessName
            $report.Add("  State=$($l.State) PID=$($l.OwningProcess) Process=$procName")
        }
    } else {
        $report.Add("  (no connections on port 8000)")
    }
    $report.Add("")
    $report.Add("=== Embedded Python ===")
    $pyExe = Join-Path $installRoot "python\python.exe"
    if (Test-Path $pyExe) {
        $report.Add("Path:         $pyExe")
        try {
            $pyVer = & $pyExe --version 2>&1 | Out-String
            $report.Add("Version:      $($pyVer.Trim())")
        } catch {
            $report.Add("Version:      ERROR running --version: $($_.Exception.Message)")
        }
    } else {
        $report.Add("MISSING at:   $pyExe")
    }
    $report.Add("")
    $report.Add("=== Install root contents (top level) ===")
    Get-ChildItem -Path $installRoot -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $kind = if ($_.PSIsContainer) { "DIR " } else { "FILE" }
        $size = if ($_.PSIsContainer) { "" } else { " ($($_.Length) bytes)" }
        $report.Add("  $kind  $($_.Name)$size")
    }
    $report.Add("")
    $report.Add("=== app-scripts/ contents ===")
    Get-ChildItem -Path $appScripts -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $size = if ($_.PSIsContainer) { "" } else { " ($($_.Length) bytes)" }
        $report.Add("  $($_.Name)$size")
    }
    $report.Add("")
    $report.Add("=== backend/app/services/ contents ===")
    $svcDir = Join-Path $installRoot "backend\app\services"
    if (Test-Path $svcDir) {
        Get-ChildItem -Path $svcDir -Force -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer } | ForEach-Object {
            $report.Add("  $($_.Name)  ($($_.Length) bytes, modified $($_.LastWriteTime))")
        }
    } else {
        $report.Add("  (missing: $svcDir)")
    }

    $report | Out-File -FilePath (Join-Path $tmp "environment.txt") -Encoding utf8

    # 3) DB schema (NO row contents)
    Write-Host "  - Reading DB schema (no row data)..."
    if ((Test-Path $pyExe) -and (Test-Path $dbPath)) {
        $pyScript = Join-Path $tmp "_schema_dump.py"
        $pyCode = @"
import sqlite3, sys
db_path = sys.argv[1]
c = sqlite3.connect(db_path)
cur = c.cursor()
print('=== sqlite_master (tables + indexes) ===')
for r in cur.execute("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY type, name").fetchall():
    print(f'{r[0]}: {r[1]}')
    if r[2]:
        for line in r[2].splitlines():
            print('  ' + line)
    print()
print('=== Row counts (table size only; no row contents) ===')
for (tbl,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
    try:
        n = cur.execute(f'SELECT COUNT(*) FROM \"{tbl}\"').fetchone()[0]
        print(f'{tbl}: {n}')
    except Exception as e:
        print(f'{tbl}: ERROR {e}')
"@
        $pyCode | Out-File -FilePath $pyScript -Encoding utf8
        & $pyExe $pyScript $dbPath 2>&1 | Out-File -FilePath (Join-Path $tmp "db-schema.txt") -Encoding utf8
        Remove-Item $pyScript -Force -ErrorAction SilentlyContinue
    } else {
        "Skipped: python.exe exists=$(Test-Path $pyExe), DB exists=$(Test-Path $dbPath)" |
            Out-File -FilePath (Join-Path $tmp "db-schema.txt") -Encoding utf8
    }

    # 4) Compress
    Write-Host "  - Creating zip..."
    if (Test-Path $outZip) { Remove-Item $outZip -Force }
    Compress-Archive -Path "$tmp\*" -DestinationPath $outZip -Force

    Write-Host ""
    Write-Host "Diagnostics bundled at:"
    Write-Host "  $outZip"
    Write-Host ""
    Write-Host "Send that file to whoever is helping you."

} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
