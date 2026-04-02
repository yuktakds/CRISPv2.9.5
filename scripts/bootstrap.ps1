[CmdletBinding()]
param(
    [switch]$Offline
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    $uv = $uvCommand.Source
} else {
    $fallback = Join-Path $env:USERPROFILE ".local\\bin\\uv.exe"
    if (-not (Test-Path $fallback)) {
        throw "uv was not found. Install uv first, then rerun scripts\\bootstrap.ps1."
    }
    $uv = $fallback
}

$platformTag = "windows-" + $env:PROCESSOR_ARCHITECTURE.ToLowerInvariant()
$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache\\$platformTag"

$syncArgs = @(
    "sync",
    "--locked",
    "--all-groups",
    "--python",
    "3.13",
    "--no-python-downloads"
)
if ($Offline) {
    $syncArgs += "--offline"
}

Push-Location $repoRoot
try {
    & $uv @syncArgs
} finally {
    Pop-Location
}
