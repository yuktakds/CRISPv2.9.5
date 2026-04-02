[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    $uv = $uvCommand.Source
} else {
    $fallback = Join-Path $env:USERPROFILE ".local\\bin\\uv.exe"
    if (-not (Test-Path $fallback)) {
        throw "uv was not found. Install uv first, then rerun scripts\\verify-lock.ps1."
    }
    $uv = $fallback
}

Push-Location $repoRoot
try {
    $verifyDir = Join-Path $repoRoot ".uv-verify"
    New-Item -ItemType Directory -Force $verifyDir | Out-Null

    $requirementsPath = Join-Path $verifyDir "requirements.txt"
    & $uv -q export --locked --all-groups --format requirements.txt --output-file $requirementsPath

    & $uv pip sync $requirementsPath --dry-run --python-version 3.13 --python-platform x86_64-pc-windows-msvc --only-binary :all: --target (Join-Path $verifyDir "windows")
    & $uv pip sync $requirementsPath --dry-run --python-version 3.13 --python-platform x86_64-apple-darwin --only-binary :all: --target (Join-Path $verifyDir "macos-x64")
    & $uv pip sync $requirementsPath --dry-run --python-version 3.13 --python-platform aarch64-apple-darwin --only-binary :all: --target (Join-Path $verifyDir "macos-arm64")
} finally {
    Pop-Location
}
