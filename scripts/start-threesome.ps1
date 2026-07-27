# BuzzClawAGI launcher (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Parents = Split-Path -Parent $Root
$BuzzDir = if ($env:BUZZ_PATH) { $env:BUZZ_PATH } else { Join-Path $Parents "buzz" }
$ZcDir = if ($env:ZEROCLAW_PATH) { $env:ZEROCLAW_PATH } else { Join-Path $Parents "zeroclaw" }
$OaDir = if ($env:OPENAGI_PATH) { $env:OPENAGI_PATH } else { Join-Path $Parents "openAGI" }

Write-Host "=== BuzzClawAGI launcher ==="
Write-Host "root=$Root"

$envFile = Join-Path $Root ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
    $k, $v = $_.Split('=', 2)
    [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
  }
  Write-Host "loaded .env"
}

if (Test-Path $BuzzDir) {
  Write-Host "Buzz fork: $BuzzDir — start relay separately (just relay) if not running"
} else {
  Write-Host "Missing Buzz at $BuzzDir"
}

if (Test-Path $OaDir) {
  Write-Host "Starting OpenAGI: $OaDir"
  Start-Process -WorkingDirectory $OaDir -FilePath "npm" -ArgumentList "run","serve" -WindowStyle Minimized
} else {
  Write-Host "Missing OpenAGI at $OaDir"
}

Start-Sleep -Seconds 3

if (-not $env:OPENAGI_URL) { $env:OPENAGI_URL = "http://127.0.0.1:43210" }
if (-not $env:ZEROCLAW_ACP_CMD) { $env:ZEROCLAW_ACP_CMD = "zeroclaw acp" }

Set-Location (Join-Path $Root "bridge")
python -m pip install -q -r requirements.txt
python openagi_to_zeroclaw.py
