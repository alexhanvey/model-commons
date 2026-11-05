# Architecture

Status: Phase 1 scaffold
Last updated: 2026-11-04

## Purpose

The MVP lets a contributor run verified evaluation or LoRA jobs on a GPU worker, earn
best-effort points, and spend those points on OpenAI-compatible inference from a small community
model.

The selected MVP model is `ibm-granite/granite-4.1-3b` base. The fine-tuned adapters from Phase 0
are research artifacts, not release candidates.

## System context

```text
Contributor / API user
        |
        v
  Web dashboard (Next.js)
        |
        v
  Control-plane API (FastAPI) ---- Postgres (users, workers, jobs, ledger)
        |        |                 Redis (queues, rate limits)
        |        +--------------- S3-compatible storage (artifacts, datasets, models, logs)
        |
        +----> GPU worker (poll, lease, run, upload)
        |
        +----> Inference proxy (auth, quota, metering)
                   |
                   v
                vLLM on one trusted GPU host
```

Inference is centralized in the MVP. Community inference routing is post-MVP.

## Components

| Path | Responsibility | Phase 1 state |
|---|---|---|
| `apps/api` | HTTP control plane, auth, jobs, ledger, admin | Health and metadata skeleton |
| `apps/web` | Contributor and admin dashboard | Landing page and API status |
| `apps/worker` | GPU registration, polling, job execution | `version` and `doctor` CLI |
| `apps/inference` | OpenAI-compatible proxy in front of vLLM | Health and empty model list |
| `packages/protocol` | Shared Pydantic models | Health, metadata, error models |
| `packages/sdk-python` | Python client for the control plane | Health and metadata methods |
| `ml` | Dataset, training, evaluation, model cards | Config validation skeleton |
| `infra/compose` | Local dependencies | Postgres, Redis, RustFS, Mailpit |
| `spikes` | Phase 0 research code and results | Archived experiments |

## Boundaries

- The API schedules work. It does not train models, hold GPU state, or proxy inference.
- Workers execute platform-defined jobs in a sandbox and upload artifacts through the API.
- The inference proxy is the only public inference surface. vLLM stays private.
- Postgres is the source of truth for jobs, users, points, and audit events.
- Redis is for queues, leases, and rate limits, not durable state.
- Artifacts live in S3-compatible storage and are addressed by checksum.
- The web app talks to the API through a same-origin `/api/*` rewrite.

## Job lifecycle

```text
queued -> assigned -> running -> uploaded -> verified -> paid
                           |          |
                           v          v
                         failed     rejected
                           |
                           v
                        expired / cancelled
```

Rules:

- One worker, one job, one GPU at a time in the MVP.
- Job assignment uses `FOR UPDATE SKIP LOCKED`.
- Leases expire; heartbeats extend them.
- Job attempts are append-only; a retry creates a new attempt.
- Points are issued only after verification.
- Illegal transitions are rejected at the API and database layers.

## Points ledger

Double-entry accounts:

- `user_available`
- `user_held` (Phase 5)
- `system_issued`
- `system_revenue`

Transaction types: grant, spend, hold, settle, release, refund, adjustment.

Invariants:

- Debits equal credits per transaction.
- User balances never go negative.
- Entries are immutable; corrections are new transactions.
- Mutations are idempotent by key.
- A reconciliation job checks account totals.

Points are non-contractual, non-transferable, and have no cash value. They are not a token, equity,
or a financial instrument.

## Inference path

```text
client -> inference proxy -> vLLM
              |
              +-> API key lookup and scope check
              +-> per-key and per-user rate limit
              +-> points hold
              +-> token metering
              +-> settle or release
```

- OpenAI-compatible `POST /v1/chat/completions` and `GET /v1/models`.
- Streaming SSE is supported in Phase 5.
- No prompt or completion logging by default.
- Usage records contain counts and metadata, not content.
- The proxy maps upstream failures to stable 4xx/5xx errors.

## Security boundaries

- Public: landing page, docs, auth callbacks, inference endpoints.
- Authenticated contributor: workers, jobs, keys, points.
- Admin: verification, grants, model releases, audit.
- Worker: scoped token, lease-bound job access, presigned uploads.
- GPU host: private network, no public vLLM port, no Docker socket exposed to jobs.

Additional rules:

- API keys and worker tokens are hashed at rest and shown once.
- Session cookies are HttpOnly, Secure, SameSite=Lax; cookie-auth mutations use CSRF tokens.
- Worker sandboxes are non-root, read-only, networkless, and GPU-scoped.
- Secrets stay in environment variables or a secret manager, never in git.
- Logs redact tokens, prompts, completions, and personal data.

## Data and storage

Local S3-compatible storage is RustFS. MinIO is not used because its open-source project was
archived and its Docker images were removed in 2026; see
[ADR-0003](adr/0003-local-object-storage.md). Production uses Cloudflare R2.

Buckets:

- `artifacts` — job outputs and checksums.
- `datasets` — versioned training and eval data.
- `models` — adapters and merged models.
- `logs` — redacted job logs.

Data classes:

- Public: docs, model cards, released datasets.
- Internal: job metadata, usage counts.
- Sensitive: credentials, private prompts, user identifiers.
- Restricted: any real user correction data, until a consent and retention policy exists.

## Deployment

Proposed MVP deployment:

- API: Fly.io.
- Web: Vercel.
- Postgres: Neon.
- Redis: Upstash.
- Object storage: Cloudflare R2.
- GPU: one trusted host running vLLM and the inference proxy.
- Observability: OpenTelemetry, Prometheus/Grafana, Sentry.

The GPU host is deliberately separate from the control plane. Do not expose vLLM directly.

## Local development

```sh
just compose-up   # Postgres (5433), Redis, RustFS, Mailpit
just api          # http://localhost:8000
just web          # http://localhost:3000
just inference    # http://localhost:8001
```

The web `/api/*` rewrite points at `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

## Decisions

- [ADR-0001: MVP stack](adr/0001-stack.md)
- [ADR-0002: Base model](adr/0002-base-model.md)
- [ADR-0003: Local object storage](adr/0003-local-object-storage.md)

## Non-goals

- Pretraining from scratch.
- Distributed training across home GPUs.
- Community inference routing.
- Payments, paid credits, tokens, or blockchain.
- Kubernetes, multi-tenant organizations, or enterprise deployment.
- Frontier-model capability claims.
