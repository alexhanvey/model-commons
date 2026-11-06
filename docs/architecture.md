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

Inference is centralized in the MVP. Community inference routing and private model hosting are
post-MVP; private models are covered by [ADR-0005](adr/0005-private-model-commerce.md).

## Components

| Path | Responsibility | State |
|---|---|---|
| `apps/api` | HTTP control plane, auth, jobs, ledger, admin | Health, metadata, and database foundation |
| `apps/web` | Contributor and admin dashboard | Landing page and API status |
| `apps/worker` | GPU registration, polling, job execution | `version` and `doctor` CLI |
| `apps/inference` | OpenAI-compatible proxy in front of vLLM | Health and empty model list |
| `packages/protocol` | Shared Pydantic models | Health, metadata, error models |
| `packages/sdk-python` | Python client for the control plane | Health, auth, API keys, workers, jobs, and points methods |
| `ml` | Dataset, training, evaluation, model cards | Config validation skeleton |
| `tuning/` | Model tuning recipes, eval sets, manifests, results, model cards | Phase 4; extracted to a standalone recipes repository |
| `infra/compose` | Local dependencies | Postgres, Redis, RustFS, Mailpit |
| `spikes` | Phase 0 research code and results | Archived experiments |

## Repository topology

The long-term topology is two repositories with a one-way contract; see
[ADR-0004](adr/0004-engine-recipe-split.md).

- `model-commons` (this repository) is the engine: control plane, worker, inference proxy, web,
  protocol/SDK, the `community-llm-ml` runner, container images, the recipe schema, and the model
  registry.
- `model-commons/recipes` is the community tuning repository: recipes, eval definitions, manifests,
  results, model cards, serving profiles, and license records.

The seam is "engine vs recipes", not "platform vs ML code". The runner stays in this repository and
is consumed by the recipes repository as a versioned package and container image.

Phase 4 creates a repo-shaped `tuning/` tree here first. Extraction is a directory move plus a
version pin. It happens when any trigger fires: more than two actively maintained recipes, the
first external recipe contributor, the first release candidate, or a governance or licensing need
for independent recipe history.

Built datasets, adapters, and models stay in object storage by checksum. Git holds the recipe and
its manifest, not the bytes.

## Boundaries

- The API schedules work. It does not train models, hold GPU state, or proxy inference.
- Workers execute platform-defined jobs in a sandbox and upload artifacts through the API.
- The platform executes only pinned, approved recipes. It never runs a recipe from a mutable ref.
- The recipes repository is the source of truth for what to train and evaluate. The model registry
  is the source of truth for what was built, verified, and released.
- Merging a recipe makes it a candidate; only the release gate changes the served model.
- The inference proxy is the only public inference surface. vLLM stays internal.
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
- The `paid` state means points were issued. It is not a fiat settlement.

## Points ledger

Double-entry accounts:

- `user_available`
- `user_held` (Phase 5)
- `system_issued`
- `system_revenue` (points only; fiat revenue uses a separate ledger)

Transaction types: grant, spend, hold, settle, release, refund, adjustment.

Invariants:

- Debits equal credits per transaction.
- User balances never go negative.
- Entries are immutable; corrections are new transactions.
- Mutations are idempotent by key.
- A reconciliation job checks account totals.

Posting rules:

- A grant debits `system_issued` and credits `user_available`.
- A spend debits `user_available` and credits `system_revenue`.
- The user account is locked while checking for a negative balance.
- A repeated idempotency key returns the original transaction instead of posting again.
- Audit events record ledger grants and job create/cancel actions.
- `just ledger-reconcile` checks transaction balance, global debits/credits, and negative user
  accounts. The admin API exposes the same report at `GET /v1/admin/ledger/reconciliation`.

Points are non-contractual, non-transferable, and have no cash value. They are not a token, equity,
or a financial instrument. The points ledger never holds fiat; private-model billing uses a separate
ledger.

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

## Private models (post-MVP)

Private tuned models are a separate commercial track. They reuse the shared recipe schema but live
in tenant-scoped storage, not the public recipes repository.

- Private artifacts are encrypted at rest and isolated per tenant.
- Private models may require dedicated inference capacity; the best-effort MVP GPU host is not a
  tenant-isolated commercial service.
- Inference uses per-customer entitlements and private model deployments. Private models are not
  listed in the public `/v1/models` response.
- Metering feeds a fiat billing ledger, separate from points. Points never convert to fiat.
- Private data training runs on trusted or dedicated workers, not anonymous community workers.
- A private-model gate covers data rights, license compliance, safety/AUP, task quality, and a
  model card. It does not use the public release threshold.
- The public community model and its recipes remain open and unaffected.

## Security boundaries

- Public: landing page, docs, auth callbacks, inference endpoints.
- Authenticated contributor: workers, jobs, keys, points.
- Admin: verification, grants, model releases, audit.
- Worker: scoped token, lease-bound job access, presigned uploads.
- GPU host: private network, no public vLLM port, no Docker socket exposed to jobs.
- Private model artifacts: tenant-scoped, encrypted, and never listed publicly.
- Fiat billing records: restricted, separate from points, and audited.

Additional rules:

- API keys and worker tokens are hashed at rest and shown once.
- Session cookies are HttpOnly, Secure, SameSite=Lax; cookie-auth mutations use CSRF tokens.
- OAuth state is bound to a short-lived cookie; session tokens are hashed at rest and CSRF tokens
  are derived from the session token.
- Worker sandboxes are non-root, read-only, networkless, and GPU-scoped.
- Secrets stay in environment variables or a secret manager, never in git.
- Logs redact tokens, prompts, completions, and personal data.

## Authentication and authorization

- Browser sessions use GitHub OAuth. Session tokens are hashed at rest; cookies are HttpOnly,
  SameSite=Lax, and Secure outside local/test.
- API keys use a `clm_` prefix and are hashed at rest. The raw key is shown once and carries explicit
  scopes: `inference:write`, `jobs:read`, `jobs:write`.
- API keys can call user endpoints but cannot manage API keys or workers. Those require a browser
  session with CSRF.
- Worker tokens use a `wrk_` prefix and are hashed at rest. They only authenticate worker endpoints;
  workers must be approved by an admin before heartbeats are accepted.
- Cookie-auth mutations require the CSRF token returned by `/v1/me`.

## Data and storage

Local S3-compatible storage is RustFS. MinIO is not used because its open-source project was
archived and its Docker images were removed in 2026; see
[ADR-0003](adr/0003-local-object-storage.md). Production uses Cloudflare R2.

Buckets:

- `artifacts` — job outputs and checksums.
- `datasets` — versioned training and eval data.
- `models` — adapters and merged models.
- `logs` — redacted job logs.
- `private` — tenant-scoped private recipes, adapters, and customer artifacts (post-MVP).

Recipes and manifests are small text files in git. Datasets, adapters, and built models are object
storage entries addressed by checksum and referenced from a recipe manifest.

Data classes:

- Public: docs, model cards, released datasets.
- Internal: job metadata, usage counts.
- Sensitive: credentials, private prompts, user identifiers.
- Restricted: any real user correction data, until a consent and retention policy exists.
- Tenant-confidential: private recipes, adapters, customer data, and billing records.

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
just migrate      # apply database migrations
just api          # http://localhost:8000
just web          # http://localhost:3000
just inference    # http://localhost:8001
```

The web `/api/*` rewrite points at `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

## Decisions

- [ADR-0001: MVP stack](adr/0001-stack.md)
- [ADR-0002: Base model](adr/0002-base-model.md)
- [ADR-0003: Local object storage](adr/0003-local-object-storage.md)
- [ADR-0004: Engine and recipe split](adr/0004-engine-recipe-split.md)
- [ADR-0005: Private models and paid access](adr/0005-private-model-commerce.md)

## Non-goals

- Pretraining from scratch.
- Distributed training across home GPUs.
- Community inference routing.
- Payments, paid credits, tokens, or blockchain in the MVP. Private-model commerce is a post-MVP
  track; see ADR-0005.
- Kubernetes, multi-tenant organizations, or enterprise deployment in the MVP.
- Frontier-model capability claims.
