#requires -Version 5.1
<#
.SYNOPSIS
  Start the integrated stack: OpenAGI + bridge.

.USAGE
  .\start.ps1
  .\start.ps1 -DryRun
  .\start.ps1 -BridgeOnly
#>
param(
  [switch]$BridgeOnly,
  [switch]$DryRun,
  [switch]$WithBuzzAcp,
  [int]$HealthTimeoutSec = 60
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
# Support root wrappers: .\start.ps1 -> scripts\start.ps1
if (-not (Test-Path (Join-Path $Root "bridge"))) {
  $Root = Split-Path -Parent $MyInvocation.MyCommand.Path
  if (-not (Test-Path (Join-Path $Root "bridge"))) {
    $Root = Get-Location
  }
}
$Deps = Join-Path $Root "deps"
$PathPs1 = Join-Path $Deps "path.ps1"
$LogDir = Join-Path $Root ".bridge-state"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Wait-OpenAgiHealth {
  param([string]$Url, [int]$TimeoutSec = 60)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  $health = ($Url.TrimEnd("/") + "/health")
  Write-Host "Waiting for OpenAGI at $health ..."
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Uri $health -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
        Write-Host "OpenAGI is up (HTTP $($r.StatusCode))." -ForegroundColor Green
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 800
    }
  }
  return $false
}

function Start-OpenAgi {
  param([string]$OaDir)
  if (-not (Test-Path $OaDir)) {
    throw "OpenAGI not found at $OaDir — run .\install.ps1 first"
  }

  $node = (Get-Command node -ErrorAction SilentlyContinue)?.Source
  if (-not $node) {
    throw "node.exe not found. Install Node.js 22+ from https://nodejs.org"
  }

  # Prefer direct node entry (avoids Windows npm.ps1 / Notepad trap with Start-Process)
  $entry = Join-Path $OaDir "examples\hosted-server.js"
  if (-not (Test-Path $entry)) {
    $entry = Join-Path $OaDir "examples\hosted-server.js"
  }

  $stdout = Join-Path $LogDir "openagi.stdout.log"
  $stderr = Join-Path $LogDir "openagi.stderr.log"

  if (Test-Path $entry) {
    Write-Host "Starting OpenAGI via: node $entry"
    Write-Host "Logs: $stdout"
    $proc = Start-Process -PassThru `
      -WorkingDirectory $OaDir `
      -FilePath $node `
      -ArgumentList $entry `
      -RedirectStandardOutput $stdout `
      -RedirectStandardError $stderr `
      -WindowStyle Hidden
  } else {
    # Fallback: npm.cmd (never bare "npm" — that resolves to npm.ps1 and can open Notepad)
    $npmCmd = Join-Path (Split-Path $node -Parent) "npm.cmd"
    if (-not (Test-Path $npmCmd)) {
      $npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue)?.Source
    }
    if (-not $npmCmd) {
      throw "Neither examples/hosted-server.js nor npm.cmd found under $OaDir"
    }
    Write-Host "Starting OpenAGI via: npm.cmd run serve"
    $proc = Start-Process -PassThru `
      -WorkingDirectory $OaDir `
      -FilePath $npmCmd `
      -ArgumentList "run","serve" `
      -RedirectStandardOutput $stdout `
      -RedirectStandardError $stderr `
      -WindowStyle Hidden
  }

  Start-Sleep -Seconds 1
  if ($proc.HasExited) {
    $err = ""
    if (Test-Path $stderr) { $err = Get-Content $stderr -Raw -ErrorAction SilentlyContinue }
    throw "OpenAGI process exited immediately (code $($proc.ExitCode)). stderr:`n$err"
  }
  return $proc
}

if (Test-Path $PathPs1) {
  . $PathPs1
} else {
  Write-Warning "deps/path.ps1 missing — run .\install.ps1 first (or set OPENAGI_PATH etc.)"
  if (-not $env:OPENAGI_PATH) { $env:OPENAGI_PATH = Join-Path $Deps "openAGI" }
  if (-not $env:ZEROCLAW_PATH) { $env:ZEROCLAW_PATH = Join-Path $Deps "zeroclaw" }
  if (-not $env:BUZZ_PATH) { $env:BUZZ_PATH = Join-Path $Deps "buzz" }
}

$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
  }
}

if ($DryRun) { $env:DRY_RUN = "1" }
if (-not $env:OPENAGI_URL) { $env:OPENAGI_URL = "http://127.0.0.1:43210" }
if (-not $env:ZEROCLAW_ACP_CMD) {
  $zc = Join-Path $env:ZEROCLAW_PATH "target\release\zeroclaw.exe"
  if (-not (Test-Path $zc)) { $zc = Join-Path $env:ZEROCLAW_PATH "target\release\zeroclaw" }
  if (Test-Path $zc) {
    $env:ZEROCLAW_ACP_CMD = "`"$zc`" acp"
  } else {
    $env:ZEROCLAW_ACP_CMD = "zeroclaw acp"
  }
}
if (-not $env:BRIDGE_STATE_DIR) {
  $env:BRIDGE_STATE_DIR = $LogDir
}

# Bridge was previously writing state under bridge/.bridge-state when cwd was bridge/
$env:BRIDGE_STATE_DIR = $LogDir

Write-Host "=== BuzzClawAGI start ===" -ForegroundColor Cyan
Write-Host "Root=$Root"
Write-Host "OPENAGI_PATH=$($env:OPENAGI_PATH)"
Write-Host "OPENAGI_URL=$($env:OPENAGI_URL)"
Write-Host "ZEROCLAW_ACP_CMD=$($env:ZEROCLAW_ACP_CMD)"
Write-Host "DRY_RUN=$($env:DRY_RUN)"

$oaProc = $null
if (-not $BridgeOnly) {
  $oaProc = Start-OpenAgi -OaDir $env:OPENAGI_PATH
  Write-Host "OpenAGI pid=$($oaProc.Id)"
  if (-not (Wait-OpenAgiHealth -Url $env:OPENAGI_URL -TimeoutSec $HealthTimeoutSec)) {
    $stderr = Join-Path $LogDir "openagi.stderr.log"
    $tail = ""
    if (Test-Path $stderr) { $tail = Get-Content $stderr -Tail 40 -ErrorAction SilentlyContinue | Out-String }
    Write-Host @"

OpenAGI did not become healthy on $($env:OPENAGI_URL) within ${HealthTimeoutSec}s.

Common fixes:
  1. Run install:  .\install.ps1 -SkipRust
  2. Check logs:   $LogDir\openagi.stderr.log
  3. Manual test:  cd deps\openAGI; node examples\hosted-server.js

Last stderr:
$tail
"@ -ForegroundColor Yellow
    if ($oaProc -and -not $oaProc.HasExited) {
      Stop-Process -Id $oaProc.Id -Force -ErrorAction SilentlyContinue
    }
    throw "OpenAGI failed to start — aborting so the bridge does not spam connection errors."
  }
}

if ($WithBuzzAcp) {
  Write-Host @"

WithBuzzAcp: after relay is up, in another terminal:

  `$env:BUZZ_PRIVATE_KEY = '...'
  `$env:BUZZ_RELAY_URL = 'ws://localhost:3000'
  `$env:BUZZ_ACP_AGENT_COMMAND = (Join-Path `$env:ZEROCLAW_PATH 'target\release\zeroclaw.exe')
  `$env:BUZZ_ACP_AGENT_ARGS = 'acp'
  buzz-acp
"@
}

Write-Host "Starting bridge (Ctrl+C stops bridge + OpenAGI)..." -ForegroundColor Cyan
Set-Location (Join-Path $Root "bridge")
try {
  python openagi_to_zeroclaw.py
} finally {
  if ($oaProc -and -not $oaProc.HasExited) {
    Write-Host "Stopping OpenAGI pid=$($oaProc.Id)"
    Stop-Process -Id $oaProc.Id -Force -ErrorAction SilentlyContinue
    # also kill node children if npm was used
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($oaProc.Id)" -ErrorAction SilentlyContinue |
      ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  }
}
