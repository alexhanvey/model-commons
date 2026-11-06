# GitHub OAuth Setup

Status: Phase 2

This guide configures local GitHub OAuth for the control-plane API.

## Create a local OAuth app

1. Open <https://github.com/settings/developers> and create a new OAuth app.
2. Homepage URL: `http://localhost:3000`
3. Authorization callback URL: `http://localhost:8000/v1/auth/github/callback`
4. Copy the client ID and client secret into `.env`.

```sh
COMMUNITY_LLM_GITHUB_CLIENT_ID=...
COMMUNITY_LLM_GITHUB_CLIENT_SECRET=...
COMMUNITY_LLM_GITHUB_REDIRECT_URI=http://localhost:8000/v1/auth/github/callback
COMMUNITY_LLM_WEB_BASE_URL=http://localhost:3000
COMMUNITY_LLM_SESSION_SECRET=<output of: openssl rand -hex 32>
COMMUNITY_LLM_ADMIN_GITHUB_IDS=[12345]
```

Outside `local` and `test`, the API refuses to start with the development session secret or a
session secret shorter than 32 characters.

Find your numeric GitHub ID with:

```sh
curl -s https://api.github.com/users/<your-login> | jq .id
```

## Flow

- `GET /v1/auth/github/login` sets a short-lived state cookie and redirects to GitHub.
- `GET /v1/auth/github/callback` validates the state cookie, exchanges the code, upserts the user,
  creates a server-side session, and sets the session cookie.
- `GET /v1/me` returns the current user and a CSRF token.
- `POST /v1/auth/logout` requires `X-CSRF-Token` and revokes the session.

## Security notes

- Session tokens are hashed at rest; the raw token is only in the HttpOnly cookie.
- Cookies are HttpOnly, SameSite=Lax, and Secure outside `local` and `test`.
- CSRF tokens are derived from the session token with the server secret.
- Admin status is recomputed from `COMMUNITY_LLM_ADMIN_GITHUB_IDS` on each login.
- Expired and revoked sessions are rejected. A periodic cleanup job is deferred.

## Tests

```sh
uv run pytest apps/api/tests -q
```

The OAuth tests use a fake GitHub client. They do not call GitHub or require real credentials.
