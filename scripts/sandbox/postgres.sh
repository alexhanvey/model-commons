#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

PG_VERSION="${PG_VERSION:-16.9.1}"
PG_ARCH="$(detect_arch)"
PG_TARBALL="postgresql-${PG_VERSION}-${PG_ARCH}-unknown-linux-gnu.tar.gz"
PG_URL="https://github.com/theseus-rs/postgresql-binaries/releases/download/${PG_VERSION}/${PG_TARBALL}"
PG_DIST="${PG_DIST:-$SANDBOX_DIR/pg16}"
PGDATA="${PGDATA:-$SANDBOX_DIR/pgdata}"
PGPORT="${POSTGRES_PORT:-5433}"
PGUSER="${POSTGRES_USER:-community}"
PGDATABASE="${POSTGRES_DB:-community_llm}"
PGSOCKET="${PGSOCKET:-$SANDBOX_DIR/pgsocket}"
PGLOG="${PGLOG:-$SANDBOX_DIR/postgres.log}"

use_pg() {
  export LD_LIBRARY_PATH="$PG_DIST/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export PATH="$PG_DIST/bin:$PATH"
}

install_pg() {
  ensure_linux
  if [ -x "$PG_DIST/bin/postgres" ]; then
    log "Postgres already installed at $PG_DIST"
    return
  fi

  require_cmd curl
  require_cmd tar
  require_cmd sha256sum

  mkdir -p "$SANDBOX_DIR"
  if [ ! -f "$SANDBOX_DIR/$PG_TARBALL" ]; then
    log "Downloading $PG_TARBALL"
    curl -fL --retry 3 -o "$SANDBOX_DIR/$PG_TARBALL" "$PG_URL"
  fi
  if [ ! -f "$SANDBOX_DIR/$PG_TARBALL.sha256" ]; then
    curl -fL --retry 3 -o "$SANDBOX_DIR/$PG_TARBALL.sha256" "$PG_URL.sha256"
  fi
  (cd "$SANDBOX_DIR" && sha256sum -c "$PG_TARBALL.sha256")

  mkdir -p "$PG_DIST"
  tar -xzf "$SANDBOX_DIR/$PG_TARBALL" -C "$PG_DIST" --strip-components=1
  log "Installed Postgres $PG_VERSION at $PG_DIST"
}

init_pg() {
  install_pg
  use_pg

  if [ -f "$PGDATA/PG_VERSION" ]; then
    return
  fi

  mkdir -p "$PGDATA" "$PGSOCKET"
  log "Initializing database at $PGDATA"
  initdb -D "$PGDATA" -U "$PGUSER" --auth=trust --encoding=UTF8 --locale=C.UTF-8 >/dev/null
}

start_db() {
  init_pg
  use_pg

  if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    log "Postgres is already running on port $PGPORT"
  else
    mkdir -p "$PGSOCKET"
    log "Starting Postgres on 127.0.0.1:$PGPORT"
    pg_ctl -D "$PGDATA" -l "$PGLOG" -w \
      -o "-p $PGPORT -k $PGSOCKET -c listen_addresses=localhost" start >/dev/null
  fi

  if ! psql -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$PGDATABASE'" | grep -q 1; then
    createdb -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
    log "Created database $PGDATABASE"
  fi

  log "Postgres ready: postgresql+asyncpg://$PGUSER@127.0.0.1:$PGPORT/$PGDATABASE"
}

stop_db() {
  if [ ! -x "$PG_DIST/bin/pg_ctl" ]; then
    log "Postgres is not installed"
    return
  fi
  use_pg
  if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    pg_ctl -D "$PGDATA" -m fast -w stop >/dev/null
    log "Postgres stopped"
  else
    log "Postgres is not running"
  fi
}

status_db() {
  if [ ! -x "$PG_DIST/bin/pg_ctl" ]; then
    log "Postgres is not installed"
    return 1
  fi
  use_pg
  if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    pg_isready -h 127.0.0.1 -p "$PGPORT" -U "$PGUSER"
    log "Data directory: $PGDATA"
  else
    log "Postgres is not running"
    return 1
  fi
}

logs_db() {
  [ -f "$PGLOG" ] || {
    log "No log file at $PGLOG"
    return 1
  }
  tail -n 100 "$PGLOG"
}

url_db() {
  echo "postgresql+asyncpg://$PGUSER@127.0.0.1:$PGPORT/$PGDATABASE"
}

case "${1:-}" in
  install) install_pg ;;
  init) init_pg ;;
  start) start_db ;;
  stop) stop_db ;;
  status) status_db ;;
  logs) logs_db ;;
  url) url_db ;;
  *) die "usage: $0 {install|init|start|stop|status|logs|url}" ;;
esac
