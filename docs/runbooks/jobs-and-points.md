# Jobs and Points

Status: Phase 2

This runbook covers creating and cancelling jobs and inspecting the points ledger. Examples use
`$COOKIE` for the `community_session` cookie and `$CSRF` for the `/v1/me` CSRF token. See
[API keys and worker tokens](api-keys-and-workers.md) for how to obtain them.

## Jobs

Create a job:

```sh
curl -s -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{"kind":"eval","spec":{"suite":"smoke"}}' \
  http://localhost:3000/api/v1/jobs
```

Kinds: `benchmark`, `eval`, `lora_finetune`.

List and fetch:

```sh
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/jobs
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/jobs/<job-id>
```

Cancel a job:

```sh
curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/jobs/<job-id>/cancel
```

Illegal transitions return 409. Terminal jobs cannot be cancelled.

## Job state machine

```text
queued -> assigned -> running -> uploaded -> verified -> paid
   |          |          |          |
   +----------+----------+----------+-> cancelled
              |          |
              +----------+-> failed
                         |
                         +-> rejected
```

`queued` jobs can also expire. Allowed transitions are defined in
`apps/api/src/community_llm_api/job_state.py`.

## Admin grant

The admin must be listed in `COMMUNITY_LLM_ADMIN_GITHUB_IDS` and signed in again after a change.

Find the target user ID from `GET /v1/me` as that user, or from the admin user list once it exists.

```sh
curl -s -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<user-id>","amount":100,"reason":"beta grant","idempotency_key":"grant-001"}' \
  http://localhost:3000/api/v1/admin/grants
```

The same `idempotency_key` returns the original transaction and does not double-credit.

## Balance and history

```sh
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/points/balance
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/points/transactions
```

The ledger is double-entry: each transaction has matching debits and credits. Grants debit
`system_issued` and credit `user_available`; spends debit `user_available` and credit
`system_revenue`.

## Reconciliation

Check ledger invariants:

```sh
just ledger-reconcile
```

Admins can also fetch the report:

```sh
curl -s -H "Cookie: $COOKIE" http://localhost:3000/api/v1/admin/ledger/reconciliation
```

The report checks that every transaction is balanced, global debits equal credits, and no
`user_available` account is negative. The script exits nonzero if the ledger is not OK.

Points are non-monetary, non-transferable, and have no cash value.
