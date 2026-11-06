#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SANDBOX_DIR="${SANDBOX_DIR:-$ROOT_DIR/.sandbox}"
LOCAL_BIN="${LOCAL_BIN:-$HOME/.local/bin}"

log() {
  printf '%s\n' "$*" >&2
}

die() {
  log "error: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

detect_arch() {
  case "$(uname -m)" in
    aarch64 | arm64) echo "aarch64" ;;
    x86_64 | amd64) echo "x86_64" ;;
    *) die "unsupported architecture: $(uname -m)" ;;
  esac
}

ensure_linux() {
  [ "$(uname -s)" = "Linux" ] || die "sandbox scripts currently support Linux only"
}

find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return
  fi
  if [ -x "$LOCAL_BIN/uv" ]; then
    echo "$LOCAL_BIN/uv"
    return
  fi
  die "uv not found; install it or add $LOCAL_BIN to PATH"
}
