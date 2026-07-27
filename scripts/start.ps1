#requires -Version 5.1
<#
.SYNOPSIS
  Start the integrated stack: OpenAGI + bridge (+ optional buzz-acp notes).

.USAGE
  .\scripts\start.ps1
  .\scripts\start.ps1 -BridgeOnly
  .\scripts\start.ps1 -DryRun
#>
param(
  [switch]$BridgeOnly,
  [switch]$DryRun,
  [switch]$WithBuzzAcp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Deps = Join-Path $Root "deps"
$PathPs1 = Join-Path $Deps "path.ps1"

if (Test-Path $PathPs1) {
  . $PathPs1
} else {
  Write-Warning "deps/path.ps1 missing — run .\scripts\install.ps1 first (or set OPENAGI_PATH etc.)"
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
  $env:BRIDGE_STATE_DIR = Join-Path $Root ".bridge-state"
}

Write-Host "=== BuzzClawAGI start ===" -ForegroundColor Cyan
Write-Host "OPENAGI_URL=$($env:OPENAGI_URL)"
Write-Host "ZEROCLAW_ACP_CMD=$($env:ZEROCLAW_ACP_CMD)"
Write-Host "DRY_RUN=$($env:DRY_RUN)"

$oaProc = $null
if (-not $BridgeOnly) {
  $oaDir = $env:OPENAGI_PATH
  if (-not (Test-Path $oaDir)) {
    throw "OpenAGI not found at $oaDir — run .\scripts\install.ps1"
  }
  Write-Host "Starting OpenAGI daemon..."
  $oaProc = Start-Process -PassThru -WorkingDirectory $oaDir -FilePath "npm" -ArgumentList "run","serve" -WindowStyle Minimized
  Write-Host "OpenAGI pid=$($oaProc.Id)"
  Start-Sleep -Seconds 3
}

if ($WithBuzzAcp) {
  Write-Host @"

WithBuzzAcp: start buzz-acp in another terminal after relay is up:

  `$env:BUZZ_PRIVATE_KEY = '...'
  `$env:BUZZ_RELAY_URL = 'ws://localhost:3000'
  `$env:BUZZ_ACP_AGENT_COMMAND = (Join-Path `$env:ZEROCLAW_PATH 'target\release\zeroclaw.exe')
  `$env:BUZZ_ACP_AGENT_ARGS = 'acp'
  buzz-acp

Buzz relay: cd deps\buzz; just relay   (if just + stack configured)
"@
}

Write-Host "Starting bridge (Ctrl+C stops bridge; stop OpenAGI window separately)..."
Set-Location (Join-Path $Root "bridge")
try {
  python openagi_to_zeroclaw.py
} finally {
  if ($oaProc -and -not $oaProc.HasExited) {
    Write-Host "Stopping OpenAGI pid=$($oaProc.Id)"
    Stop-Process -Id $oaProc.Id -Force -ErrorAction SilentlyContinue
  }
}
