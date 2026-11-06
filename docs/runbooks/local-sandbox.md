# Local Sandbox Without Docker

Status: Phase 2

This runbook runs the control plane and web app directly inside a Linux container or host without
Docker. It uses a self-contained PostgreSQL binary and local Node/Python processes.

## What runs

| Component | Local sandbox |
|---|---|
| Control-plane API | Yes |
| Next.js web app | Yes |
| PostgreSQL 16 | Yes, native binary |
| Redis | Not yet; Phase 3 |
| RustFS / S3 | Not yet; Phase 3/4 |
| vLLM / GPU jobs | No; use an external GPU host or Vast |

The sandbox is for development and UI/auth work. It is not a production deployment.

## Prerequisites

- Linux on `aarch64` or `x86_64`.
- `curl`, `tar`, `sha256sum`, `node`, and `npm`.
- No Docker and no root are required.

## Bootstrap

```sh
bash scripts/sandbox/bootstrap.sh
export PATH="$HOME/.local/bin:$PATH"
```

The script installs `just`, pnpm `12.16.1`, Python 3.12 via `uv`, project dependencies, and web
dependencies. It downloads PostgreSQL 16.9.1 on first start.

## Start and stop

```sh
just sandbox-up      # start Postgres and apply migrations
just dev             # start API and web together
```

Or run them separately:

```sh
just api             # http://localhost:8000
just web             # http://localhost:3000
```

Stop the database:

```sh
just sandbox-down
```

Status and logs:

```sh
just sandbox-status
just sandbox-logs
```

Validate `.env` before starting the API:

```sh
just sandbox-check
```

PostgreSQL listens on `127.0.0.1:5433` with a local data directory in `.sandbox/pgdata`.
Authentication is `trust` for local development only. Do not expose this port.

## OAuth

The web app proxies `/api/*` to the API, so the GitHub callback should go through the web origin:

```sh
COMMUNITY_LLM_GITHUB_CLIENT_ID=...
COMMUNITY_LLM_GITHUB_CLIENT_SECRET=...
COMMUNITY_LLM_GITHUB_REDIRECT_URI=http://localhost:3000/api/v1/auth/github/callback
COMMUNITY_LLM_WEB_BASE_URL=http://localhost:3000
COMMUNITY_LLM_SESSION_SECRET=<output of: openssl rand -hex 32>
COMMUNITY_LLM_ADMIN_GITHUB_IDS=[12345]
```

Configure the GitHub OAuth app with:

- Homepage URL: `http://localhost:3000`
- Authorization callback URL: `http://localhost:3000/api/v1/auth/github/callback`

Find your numeric GitHub ID with:

```sh
curl -s https://api.github.com/users/<your-login> | jq .id
```

If the browser cannot reach `localhost:3000`, expose the web app with a tunnel:

```sh
just sandbox-tunnel
```

Set both URLs to the `https://*.trycloudflare.com` origin and update the GitHub OAuth app callback.
Quick tunnel URLs change on every restart.

See [GitHub OAuth setup](github-oauth.md) for the full flow and security notes.

## Exposing ports

The web app binds `127.0.0.1` by default. If the web server must be reachable from outside the
container, use:

```sh
WEB_HOST=0.0.0.0 just web
```

The API can stay on `127.0.0.1` because the web proxy reaches it internally. Use
`API_HOST=0.0.0.0` only if you need direct API access.

## Reset the database

Stop Postgres first, then remove its data directory:

```sh
just sandbox-down
rm -rf .sandbox/pgdata
just sandbox-up
```

This deletes all local development data.

## Limitations and GPU work

- The sandbox has no GPU. vLLM, real LoRA training, and large-model evaluation need an external GPU
  host. Use Vast only with explicit approval.
- Ollama can serve small models for smoke tests, but it is not the production inference path.
- Redis and RustFS are added when Phase 3 needs them. RustFS publishes arm64 Linux builds, so they
  can run natively too.
- The PostgreSQL binary comes from the `theseus-rs/postgresql-binaries` GitHub release and its
  published SHA256. It is a development dependency, not a production package.

## Troubleshooting

- **Port 5433 already in use**: stop Docker Compose or the other Postgres instance, then rerun
  `just sandbox-up`.
- **Postgres will not start**: check `just sandbox-logs`.
- **OAuth returns 503**: `COMMUNITY_LLM_GITHUB_CLIENT_ID` or `..._SECRET` is empty in `.env`.
  Run `just sandbox-check` to validate the file.
- **OAuth callback mismatch**: the GitHub app callback and `..._REDIRECT_URI` must match exactly.
- **Web port not reachable**: run with `WEB_HOST=0.0.0.0` or use `just sandbox-tunnel`.
