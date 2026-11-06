#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

if [ ! -f "$ENV_FILE" ]; then
  die "missing $ENV_FILE; copy .env.example or run the bootstrap script"
fi

status=0
line_no=0

while IFS= read -r line || [ -n "$line" ]; do
  line_no=$((line_no + 1))
  trimmed="${line#"${line%%[![:space:]]*}"}"
  [ -z "$trimmed" ] && continue
  case "$trimmed" in
    \#*) continue ;;
  esac
  if ! [[ "$trimmed" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
    log "invalid .env line $line_no: $line"
    status=1
  fi
done <"$ENV_FILE"

value() {
  grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- || true
}

client_id="$(value COMMUNITY_LLM_GITHUB_CLIENT_ID)"
client_secret="$(value COMMUNITY_LLM_GITHUB_CLIENT_SECRET)"
redirect_uri="$(value COMMUNITY_LLM_GITHUB_REDIRECT_URI)"
web_base_url="$(value COMMUNITY_LLM_WEB_BASE_URL)"
session_secret="$(value COMMUNITY_LLM_SESSION_SECRET)"
environment="$(value COMMUNITY_LLM_ENVIRONMENT)"

if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
  log "GitHub OAuth is incomplete: set COMMUNITY_LLM_GITHUB_CLIENT_ID and ..._SECRET."
  status=1
fi

expected_redirect="${web_base_url%/}/api/v1/auth/github/callback"
if [ -z "$redirect_uri" ]; then
  log "COMMUNITY_LLM_GITHUB_REDIRECT_URI is empty; expected $expected_redirect"
  status=1
elif [ -n "$web_base_url" ] && [ "$redirect_uri" != "$expected_redirect" ]; then
  log "COMMUNITY_LLM_GITHUB_REDIRECT_URI is $redirect_uri"
  log "expected $expected_redirect for the web proxy"
  status=1
fi

if [ -z "$web_base_url" ]; then
  log "COMMUNITY_LLM_WEB_BASE_URL is empty; expected http://localhost:3000"
  status=1
fi

if [ "${environment:-local}" != "local" ] && [ "${environment:-local}" != "test" ] &&
  [ "${#session_secret}" -lt 32 ]; then
  log "COMMUNITY_LLM_SESSION_SECRET must be at least 32 characters outside local/test."
  status=1
fi

if [ "$status" -eq 0 ]; then
  log "Environment looks good for the web-proxy OAuth flow."
fi

exit "$status"
