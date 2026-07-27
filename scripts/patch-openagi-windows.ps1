#requires -Version 5.1
<#
  OpenAGI writeTextAtomic opens a file with "r" then fsyncSync — on Windows
  that often throws EPERM and aborts boot. Patch fsync to soft-fail on EPERM/EINVAL.
#>
param(
  [string]$OpenAgiPath = $env:OPENAGI_PATH
)

$ErrorActionPreference = "Stop"
if (-not $OpenAgiPath) {
  $Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
  $OpenAgiPath = Join-Path $Root "deps\openAGI"
}

$target = Join-Path $OpenAgiPath "src\file-utils.js"
if (-not (Test-Path $target)) {
  Write-Warning "patch-openagi-windows: missing $target"
  exit 0
}

$text = Get-Content $target -Raw
if ($text -match "buzzclaw-fsync-softfail") {
  Write-Host "OpenAGI file-utils already patched"
  exit 0
}

$old = @'
export function writeTextAtomic(filePath, data, mode = 0o600) {
  ensureDir(path.dirname(filePath));
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tempPath, data, { mode });
  const fd = fs.openSync(tempPath, "r");
  try {
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tempPath, filePath);
}
'@

$new = @'
export function writeTextAtomic(filePath, data, mode = 0o600) {
  // buzzclaw-fsync-softfail: Windows may EPERM fsync on read-only fds
  ensureDir(path.dirname(filePath));
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tempPath, data, { mode });
  try {
    const fd = fs.openSync(tempPath, "r+");
    try {
      fs.fsyncSync(fd);
    } catch (err) {
      if (err && (err.code === "EPERM" || err.code === "EINVAL" || err.code === "ENOTSUP")) {
        // non-fatal on Windows / some network FS
      } else {
        throw err;
      }
    } finally {
      fs.closeSync(fd);
    }
  } catch (err) {
    if (!(err && (err.code === "EPERM" || err.code === "EINVAL" || err.code === "ENOTSUP"))) {
      throw err;
    }
  }
  fs.renameSync(tempPath, filePath);
}
'@

if ($text -notlike "*$($old.Substring(0, 40))*") {
  # flexible replace on fsyncSync blocks
  $patched = [regex]::Replace(
    $text,
    'fs\.fsyncSync\(fd\);',
    @'
try { fs.fsyncSync(fd); } catch (err) { /* buzzclaw-fsync-softfail */ if (err && err.code !== "EPERM" && err.code !== "EINVAL" && err.code !== "ENOTSUP") throw err; }
'@
  )
  if ($patched -eq $text) {
    Write-Warning "Could not locate fsyncSync to patch in $target"
    exit 1
  }
  Set-Content -Path $target -Value $patched -Encoding utf8NoBOM
  Write-Host "Patched fsync soft-fail in $target"
  exit 0
}

$text2 = $text.Replace($old, $new)
if ($text2 -eq $text) {
  Write-Warning "Exact block replace failed; trying regex"
  $text2 = [regex]::Replace(
    $text,
    'fs\.fsyncSync\(fd\);',
    'try { fs.fsyncSync(fd); } catch (err) { /* buzzclaw-fsync-softfail */ if (err && err.code !== "EPERM" && err.code !== "EINVAL" && err.code !== "ENOTSUP") throw err; }'
  )
}
Set-Content -Path $target -Value $text2 -Encoding utf8NoBOM
Write-Host "Patched OpenAGI Windows fsync: $target"
