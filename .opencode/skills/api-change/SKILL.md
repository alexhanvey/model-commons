---
name: API Change
description: Add or change a control-plane API endpoint, schema, or migration
---

# API Change

## Boundaries

- `apps/api` owns HTTP routes and control-plane behavior.
- `packages/protocol` owns models shared across services.
- `packages/sdk-python` owns the Python client.
- `ml` owns training and evaluation entry points.
- The API schedules work; it does not train models or serve inference.

## Add an endpoint

1. Define request/response models in `packages/protocol` if another service consumes them.
2. Add a router in `apps/api/src/community_llm_api/api/` and include it in `main.py`.
3. Use dependency injection for settings, database sessions, and auth.
4. Return typed errors with stable machine-readable codes.
5. Add tests for success, validation failure, authorization failure, and idempotency where relevant.
6. Update `packages/sdk-python` and the OpenAPI-derived client when consumers change.
7. Update `docs/architecture.md` or the relevant spec.

## Database changes

- Use SQLAlchemy 2 models and Alembic migrations.
- Every migration needs a downgrade path.
- Add indexes deliberately; do not rewrite large tables in a blocking migration.
- Ledger entries are immutable. Corrections are new transactions, never updates or deletes.
- Enforce no-negative-balance in the database transaction, not only in application code.
- Add property tests for ledger invariants.

## Security

- Authenticate and authorize every non-public route.
- Check resource ownership, not just role.
- API keys and worker tokens are hashed at rest and shown once.
- Never log prompts, completions, tokens, secrets, or full request bodies.
- Cookie-auth state changes require CSRF protection.

## Validation

```sh
just lint
just typecheck
just test
```

If the schema changed, run a fresh migration and the test suite against it.
