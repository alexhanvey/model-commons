# Runbooks

Runbooks are added in Phase 7 for:

- API outage and rollback.
- Inference outage and model warmup failure.
- Worker lease expiry or stuck jobs.
- Ledger reconciliation failure.
- Postgres backup and restore.
- Secret rotation.
- Suspected key or worker-token compromise.
- Incident communication.

Each runbook must include detection, impact, immediate mitigation, verification, and follow-up.

## Setup guides

- [GitHub OAuth setup](github-oauth.md) — local OAuth app, sessions, and CSRF.
