#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

export PATH="$LOCAL_BIN:$PATH"

JUST_VERSION="${JUST_VERSION:-1.59.0}"
PNPM_VERSION="${PNPM_VERSION:-12.16.1}"

install_just() {
  if command -v just >/dev/null 2>&1; then
    log "just already installed: $(just --version)"
    return
  fi

  require_cmd curl
  require_cmd tar
  require_cmd sha256sum

  local arch tarball url expected path
  arch="$(detect_arch)"
  tarball="just-${JUST_VERSION}-${arch}-unknown-linux-musl.tar.gz"
  url="https://github.com/casey/just/releases/download/${JUST_VERSION}/${tarball}"

  case "$arch" in
    aarch64) expected="23871b1702bfd550fb5f901778fd4290ecf2ee034a45a889fbe96d89b188086d" ;;
    x86_64) expected="409044617b6f06517c1035e55ca38c8c856ff8b650e41bc2aa1ef82d5903a23e" ;;
    *) die "unsupported architecture: $arch" ;;
  esac

  mkdir -p "$SANDBOX_DIR/downloads" "$LOCAL_BIN"
  path="$SANDBOX_DIR/downloads/$tarball"
  if [ ! -f "$path" ]; then
    log "Downloading $tarball"
    curl -fL --retry 3 -o "$path" "$url"
  fi
  echo "$expected  $path" | sha256sum -c -

  tar -xzf "$path" -C "$SANDBOX_DIR/downloads"
  install -m 0755 "$SANDBOX_DIR/downloads/just" "$LOCAL_BIN/just"
  log "Installed just $JUST_VERSION to $LOCAL_BIN/just"
}

install_pnpm() {
  if command -v pnpm >/dev/null 2>&1 && [ "$(pnpm --version)" = "$PNPM_VERSION" ]; then
    log "pnpm $PNPM_VERSION already installed"
    return
  fi

  require_cmd npm
  mkdir -p "$LOCAL_BIN"
  rm -f "$LOCAL_BIN/pnpm" "$LOCAL_BIN/pnpx" "$LOCAL_BIN/pnpm.cmd" "$LOCAL_BIN/pnpx.cmd"
  npm install --prefix "$(dirname "$LOCAL_BIN")" -g "pnpm@$PNPM_VERSION" >/dev/null
  log "Installed pnpm $PNPM_VERSION to $LOCAL_BIN/pnpm"
}

install_python() {
  local uv
  uv="$(find_uv)"
  "$uv" python install 3.12
  (cd "$ROOT_DIR" && "$uv" sync --all-packages)
}

install_web() {
  "$LOCAL_BIN/pnpm" --dir "$ROOT_DIR/apps/web" install --frozen-lockfile
}

ensure_env() {
  if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    log "Created .env from .env.example. Fill in the GitHub OAuth values before login."
  fi
}

main() {
  install_just
  install_pnpm
  install_python
  install_web
  ensure_env

  cat >&2 <<'EOF'

Sandbox bootstrap complete.

Add this to your shell if it is not already on PATH:

  export PATH="$HOME/.local/bin:$PATH"

Then:

  just sandbox-up
  just dev

See docs/runbooks/local-sandbox.md for OAuth and tunnel setup.
EOF
}

main "$@"
