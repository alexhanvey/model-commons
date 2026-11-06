#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

CLOUDFLARED="${CLOUDFLARED:-$SANDBOX_DIR/bin/cloudflared}"

install_tunnel() {
  if [ -x "$CLOUDFLARED" ]; then
    log "cloudflared already installed at $CLOUDFLARED"
    return
  fi

  require_cmd curl

  local arch
  case "$(uname -m)" in
    aarch64 | arm64) arch="arm64" ;;
    x86_64 | amd64) arch="amd64" ;;
    *) die "unsupported architecture: $(uname -m)" ;;
  esac

  mkdir -p "$(dirname "$CLOUDFLARED")"
  log "Downloading cloudflared for linux-$arch"
  curl -fL --retry 3 -o "$CLOUDFLARED" \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}"
  chmod 0755 "$CLOUDFLARED"
}

start_tunnel() {
  install_tunnel
  local port="${WEB_PORT:-3000}"
  cat >&2 <<EOF

Starting a Cloudflare quick tunnel to http://localhost:${port}

Copy the https://*.trycloudflare.com URL printed below, then set:

  COMMUNITY_LLM_WEB_BASE_URL=<url>
  COMMUNITY_LLM_GITHUB_REDIRECT_URI=<url>/api/v1/auth/github/callback

Update the GitHub OAuth app callback to the same URL, then restart the API.
Quick tunnel URLs change every time you restart the tunnel.

EOF
  exec "$CLOUDFLARED" tunnel --url "http://localhost:${port}" --no-autoupdate
}

case "${1:-start}" in
  install) install_tunnel ;;
  start) start_tunnel ;;
  *) die "usage: $0 {install|start}" ;;
esac
