# Worker CLI

Status: Phase 3 — fake-GPU path

This runbook registers a worker, approves it, submits a benchmark, runs a fake-GPU job, and inspects
the result.

## Register

Registration uses the browser session and CSRF token, not the worker token:

```sh
uv run community-llm-worker register \
  --name gpu-1 \
  --api-url http://localhost:8000 \
  --session-cookie "$COMMUNITY_LLM_SESSION_COOKIE" \
  --csrf-token "$COMMUNITY_LLM_CSRF_TOKEN"
```

Get the session cookie from the browser developer tools and the CSRF token from `GET /v1/me`. See
[API keys and worker tokens](api-keys-and-workers.md).

The worker token is shown once, saved to `~/.config/community-llm/worker.json` with mode `0600`, and
used for polling and heartbeats.

## Approve

An admin approves the worker:

```sh
curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/workers/<worker-id>/approve
```

Add your numeric GitHub ID to `COMMUNITY_LLM_ADMIN_GITHUB_IDS` and sign in again if needed.

## Status

```sh
uv run community-llm-worker status
```

This sends a worker heartbeat and prints the worker status and last heartbeat time.

## Submit a benchmark

```sh
uv run community-llm-worker benchmark --suite smoke
```

This creates a `benchmark` job owned by the signed-in user. The worker will pick it up on its next
poll.

## Run a fake-GPU job

```sh
uv run community-llm-worker run --once --fake-gpu
```

The worker:

1. Heartbeats.
2. Polls for a queued job.
3. Starts the attempt and extends the lease.
4. Executes the fake-GPU executor.
5. Uploads `result.json`.
6. Completes the job with redacted logs and metrics.

Use `--poll-interval` and `--heartbeat-interval` to tune the loop. Real GPU execution is not wired
yet; `run` without `--fake-gpu` exits with an error.

## Logs

```sh
uv run community-llm-worker logs <attempt-id>
```

This prints the redacted logs, metrics, and error for the worker's attempt.

## API flow

| Step | Endpoint |
|---|---|
| Poll | `POST /v1/worker/jobs/next` |
| Start | `POST /v1/worker/jobs/{attempt_id}/start` |
| Heartbeat | `POST /v1/worker/jobs/{attempt_id}/heartbeat` |
| Upload | `POST /v1/worker/jobs/{attempt_id}/artifacts` |
| Complete | `POST /v1/worker/jobs/{attempt_id}/complete` |
| Fail | `POST /v1/worker/jobs/{attempt_id}/fail` |

The API assigns jobs with `FOR UPDATE SKIP LOCKED`, creates one attempt per assignment, and expires
leases. A failed or expired attempt requeues the job until `max_job_attempts`; then the job fails.
Workers can only access their own attempts.

## Artifacts and logs

The API computes SHA-256 over uploaded bytes, verifies an optional expected checksum, and stores the
file under `.sandbox/artifacts/<job>/<attempt>/`. Logs are redacted before storage; API tokens,
worker tokens, bearer headers, passwords, and secrets are masked.

An admin verifies an uploaded job:

```sh
curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/admin/jobs/<job-id>/verify
```

Verification pays the job reward once: benchmark 10, eval 20, LoRA fine-tune 50 points.

## Configuration

The worker reads `~/.config/community-llm/worker.json` or `--config`. Environment overrides:

- `COMMUNITY_LLM_API_URL`
- `COMMUNITY_LLM_WORKER_TOKEN`
- `COMMUNITY_LLM_SESSION_COOKIE`
- `COMMUNITY_LLM_CSRF_TOKEN`
- `COMMUNITY_LLM_WORKER_CONFIG`
