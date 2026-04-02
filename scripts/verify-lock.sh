#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v uv >/dev/null 2>&1; then
    uv_cmd="uv"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
    uv_cmd="$HOME/.local/bin/uv"
else
    echo "uv was not found. Install uv first, then rerun ./scripts/verify-lock.sh." >&2
    exit 1
fi

cd "$repo_root"

verify_dir="$repo_root/.uv-verify"
mkdir -p "$verify_dir"

requirements_path="$verify_dir/requirements.txt"
"$uv_cmd" -q export --locked --all-groups --format requirements.txt --output-file "$requirements_path"

"$uv_cmd" pip sync "$requirements_path" --dry-run --python-version 3.13 --python-platform x86_64-pc-windows-msvc --only-binary :all: --target "$verify_dir/windows"
"$uv_cmd" pip sync "$requirements_path" --dry-run --python-version 3.13 --python-platform x86_64-apple-darwin --only-binary :all: --target "$verify_dir/macos-x64"
"$uv_cmd" pip sync "$requirements_path" --dry-run --python-version 3.13 --python-platform aarch64-apple-darwin --only-binary :all: --target "$verify_dir/macos-arm64"
