#!/usr/bin/env bash
set -euo pipefail

offline=0
if [[ "${1:-}" == "--offline" ]]; then
    offline=1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v uv >/dev/null 2>&1; then
    uv_cmd="uv"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
    uv_cmd="$HOME/.local/bin/uv"
else
    echo "uv was not found. Install uv first, then rerun ./scripts/bootstrap.sh." >&2
    exit 1
fi

uname_s="$(uname -s)"
uname_m="$(uname -m)"
if [[ "$uname_s" != "Darwin" ]]; then
    echo "bootstrap.sh targets macOS. Current OS: $uname_s" >&2
    exit 1
fi

case "$uname_m" in
    arm64|aarch64) platform_tag="macos-arm64" ;;
    x86_64) platform_tag="macos-x64" ;;
    *)
        echo "Unsupported macOS architecture: $uname_m" >&2
        exit 1
        ;;
esac

export UV_CACHE_DIR="$repo_root/.uv-cache/$platform_tag"
cd "$repo_root"

sync_args=(
    sync
    --locked
    --all-groups
    --python
    3.13
    --no-python-downloads
)

if [[ "$offline" -eq 1 ]]; then
    sync_args+=(--offline)
fi

"$uv_cmd" "${sync_args[@]}"
