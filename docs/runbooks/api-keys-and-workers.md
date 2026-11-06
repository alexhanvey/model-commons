# API Keys and Worker Tokens

Status: Phase 2

API keys authenticate user-facing API calls. Worker tokens authenticate worker endpoints only.
Both are shown once and stored as SHA-256 hashes.

## Getting the session values

The examples use:

- `COOKIE` — the `community_session` cookie from the browser developer tools. It is HttpOnly, so
  JavaScript cannot read it.
- `CSRF` — the `csrf_token` returned by `GET /v1/me`.

If you use a tunnel, replace `http://localhost:3000` with the tunnel origin.

## API key scopes

| Scope | Use |
|---|---|
| `inference:write` | Call the inference API |
| `jobs:read` | Read jobs |
| `jobs:write` | Create and cancel jobs |

API keys cannot create, list, or revoke API keys or workers. Those actions require a browser
session with CSRF.

## Create an API key

Use the web origin and a signed-in browser session:

```sh
CSRF=$(curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/me | jq -r .csrf_token)

curl -s -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{"name":"agent","scopes":["inference:write","jobs:read"]}' \
  http://localhost:3000/api/v1/api-keys
```

The response contains the raw key once:

```json
{
  "api_key": {"id": "...", "prefix": "clm_...", "scopes": ["inference:write", "jobs:read"]},
  "token": "clm_..."
}
```

List keys:

```sh
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/api-keys
```

Revoke a key:

```sh
curl -s -X DELETE -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/api-keys/<key-id>
```

Use a key:

```sh
curl -s -H "Authorization: Bearer clm_..." http://localhost:3000/api/v1/me
```

The response has `"auth_method": "api_key"` and `"csrf_token": null`.

## Worker tokens

Register a worker (browser session + CSRF):

```sh
curl -s -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{"name":"gpu-1"}' \
  http://localhost:3000/api/v1/workers
```

The response contains the raw worker token once. The worker starts as `pending`.

An admin approves it:

```sh
curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/workers/<worker-id>/approve
```

Send a heartbeat with the worker token:

```sh
curl -s -X POST -H "Authorization: Bearer wrk_..." \
  http://localhost:3000/api/v1/workers/heartbeat
```

Pending workers get 403. Revoked workers get 401. Worker tokens cannot access user endpoints.

Revoke a worker:

```sh
curl -s -X DELETE -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/workers/<worker-id>
```

## Admin access

Worker approval requires `is_admin`, which comes from `COMMUNITY_LLM_ADMIN_GITHUB_IDS` at login.
Add your numeric GitHub ID there and sign in again.
