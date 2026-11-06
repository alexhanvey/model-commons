# Implementation Roadmap

Status: Phase 2 — Core backend and ledger
Last updated: 2026-11-06
Source plan: `/Users/alex/.opencode/plan/community-llm-mvp.md`

## Phase overview

| Phase | Goal | Exit gate | Status |
|---|---|---|---|
| 0 | Lock the MVP | Model, eval, data, and legal direction | Engineering spikes done; non-code validation open |
| 1 | Repo scaffold | Clone, bootstrap, run, test, CI green | CI green; tagged `v0.1.0-scaffold` |
| 2 | Core backend and ledger | Auth, workers, jobs, points, audit | Complete; CI green |
| 3 | Worker and jobs | Sandboxed worker loop and verification | Complete (fake-GPU); real GPU sandbox pending |
| 4 | ML pipeline | Reproducible data, training, eval, registry | In progress — pipeline/registry implemented; v3 below base |
| 5 | Inference | OpenAI-compatible API with metering | Not started |
| 6 | Web dashboard | Contributor and admin flows | Not started |
| 7 | Security and observability | Threat model, hardening, dashboards, runbooks | Not started |
| 8 | Deploy and beta | Staging and production, real users | Not started |
| 9 | First public model release | Beats baseline and passes release gates | Not started |

## Repository topology

The long-term topology is two repositories with a one-way contract:

- `model-commons` (this repository) — the engine: control plane, worker, inference proxy, web,
  protocol/SDK, the `community-llm-ml` runner, container images, and the model registry.
- `model-commons/recipes` — the community tuning repository: recipes, eval definitions, manifests,
  results, model cards, serving profiles, and license records.

The seam is "engine vs recipes", not "platform vs ML code". The runner stays in this repository and
is consumed by the recipes repository as a versioned package and container image.

Phase 4 creates `tuning/` in this repository with the same layout and ownership rules, so
extraction is a directory move plus a version pin, not a redesign.

Rules:

- Recipes are declarative and schema-validated. They do not execute arbitrary code.
- Every run records a pinned `recipe_ref`: repository, commit, path, and manifest SHA256. Mutable
  refs are rejected.
- Merging a recipe makes it a candidate. Only the release gate can make it the served model.
- Eval sets are versioned and owned separately from tuning recipes.
- Datasets, adapters, and built models live in object storage by checksum, not in git.
- Private recipes use the same contract in tenant-scoped storage and never enter the public recipes
  repository.

Extraction triggers (any one):

- more than two actively maintained recipes;
- the first external recipe contributor;
- the first release candidate;
- a governance or licensing need for independent recipe history.

Hard deadline: Phase 9 requires the release recipe to live in the standalone recipes repository at
an immutable tag.

## Phase 0 — Lock the MVP

Status: Engineering complete; interviews and legal review open.

### Done

- Target user: solo developers and small teams building local/agentic apps.
- First capability: tool use / function calling.
- Narrow domain: GitHub-style issue-tracker tool calling with a deterministic mock API.
- Base model: `ibm-granite/granite-4.1-3b` (Apache-2.0).
- Dataset direction: ToolACE-derived experiments plus a custom held-out set.
- 40-case hard tool-calling eval and 60-case issue-tracker eval.
- Issue-tracker mock API, 14 tools, fixtures, and state-based harness.
- 800-example v2 training set with no eval prompt overlap.
- QLoRA v1 and v2 runs; vLLM serving; adapter evaluation.
- Token-length analysis: max 2,526 tokens, 4,096 context safe.
- Evidence: `spikes/issue_tracker/results/README.md`.

### Result

| Model | Issue-tracker eval | p50 |
|---|---:|---:|
| Granite 4.1 3B base | **70.0% (42/60)** | 1,075ms |
| Adapter v1 | 53.3% (32/60) | 7,110ms |
| Adapter v2 | 68.3% (41/60) | 1,289ms |

The base model remains the MVP choice. Fine-tuning is not validated.

### Open

- [ ] 10 contributor interviews, or a documented reduced target.
- [ ] 10 user interviews, or a documented reduced target.
- [ ] 3 contributor commitments.
- [ ] 3 user commitments.
- [ ] Legal checklist sign-off.
- [ ] Open-weight release terms.
- [ ] Points policy review.

> Note: Phase 1 scaffolding started before all Phase 0 non-engineering gates closed, at the
> project owner's direction. Do not invite external beta users until the open items are resolved.

## Phase 1 — Repo scaffold

Goal: a new contributor can clone, bootstrap, and run in under 15 minutes, with CI green and
AI-agent instructions installed.

### Deliverables

- [x] Monorepo layout: `apps/`, `packages/`, `ml/`, `infra/`, `docs/`, `spikes/`.
- [x] Apache-2.0 `LICENSE`.
- [x] README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, GOVERNANCE.
- [x] `mise.toml`, `justfile`, `.env.example`, `.pre-commit-config.yaml`, `.editorconfig`.
- [x] Python `uv` workspace: API, worker, inference, protocol, SDK, ML.
- [x] Next.js web app with Tailwind and API status.
- [x] Docker Compose: Postgres, Redis, RustFS, Mailpit.
- [x] FastAPI `/healthz`, `/readyz`, `/v1/meta`.
- [x] Worker CLI: `version`, `doctor`.
- [x] Protocol package and Python SDK skeleton.
- [x] ML config validation skeleton.
- [x] CI: lint, format, typecheck, tests, web build, container builds, compose config, Trivy.
- [x] CodeQL and Dependabot.
- [x] `AGENTS.md`, `opencode.jsonc`, skills, commands, reviewer agents.
- [x] `CLAUDE.md`, Copilot instructions, Cursor rules.
- [x] Architecture doc and ADR-0003 (RustFS replaces MinIO locally).

### Acceptance

- [x] `mise install` works.
- [x] `just bootstrap` works.
- [x] `just dev` starts the API and web app.
- [x] API health and readiness work.
- [x] Web loads and shows API status.
- [x] Worker `--help` and `doctor` work.
- [x] `just test`, `just lint`, `just typecheck`, `just build` pass.
- [x] Docker Compose services healthy.
- [x] Pre-commit passes.
- [x] CI green ([run 42113861255](https://github.com/alexhanvey/model-commons/actions/runs/42113861255)).
- [x] Tag `v0.1.0-scaffold`.

Evidence is recorded in `docs/roadmap/status.md`. Do not mark future phase items complete from
inspection alone; run the command or link the result.

## Phase 2 — Core backend and ledger

Status: Complete.

Goal: auth, users, API keys, workers, jobs, double-entry points, and audit.

Scope:

- Tables: users, sessions, api_keys, workers, gpu_devices, jobs, job_attempts, artifacts,
  ledger_accounts, ledger_transactions, ledger_entries, audit_events, idempotency_keys.
- GitHub OAuth in the API, HttpOnly session cookie, CSRF for cookie-auth mutations.
- Hashed API keys with scopes; hashed worker tokens.
- Job state machine with illegal-transition rejection.
- Ledger with balanced debits/credits, no negative user balance, immutable entries, idempotency,
  and reconciliation.
- Admin allowlist and audit events.

Acceptance:

- [x] Fresh database migrates.
- [x] OAuth login works with a mocked provider.
- [x] API key create/use/revoke works.
- [x] Worker register/heartbeat/approve works.
- [x] Job create/cancel and illegal transitions rejected.
- [x] Admin grant; balance and transactions correct.
- [x] Ledger property tests pass.
- [x] Audit events exist.
- [x] OpenAPI client current. The Python SDK covers the current API; the generated TypeScript
      client is Phase 6.
- [x] CI green ([run 42267648845](https://github.com/alexhanvey/model-commons/actions/runs/42267648845)).

## Phase 3 — Worker and jobs

Status: Complete for the fake-GPU acceptance path; real GPU/sandbox executor pending.

Goal: a worker polls work, runs benchmark/eval/LoRA jobs in a sandbox, uploads artifacts, and earns
points after verification.

Scope:

- Worker CLI: register, doctor, benchmark, run, status, logs.
- Scheduler with `FOR UPDATE SKIP LOCKED`, leases, heartbeats, retries, max attempts.
- Job protocol: next, start, heartbeat, complete, fail, presign.
- Sandbox: pinned image, non-root, read-only root, tmpfs, no network, no Docker socket, GPU only
  through `--gpus`.
- Job types: benchmark, eval, lora_finetune.
- Checksummed artifacts and redacted logs.

Acceptance:

- [x] Worker registers, heartbeats, polls.
- [x] Benchmark, eval, and LoRA smoke each complete and pay once (fake-GPU path).
- [x] Lease expiry requeues.
- [x] Failure retries then fails.
- [x] Worker cannot access another job.
- [x] Artifacts checksummed and logs redacted.
- [x] Fake-GPU end-to-end test passes.
- [x] CI green ([run 42271051686](https://github.com/alexhanvey/model-commons/actions/runs/42271051686)).

The fake-GPU path is complete and merged. The real Docker/GPU sandbox executor remains the main
Phase 4 prerequisite.

## Phase 4 — ML pipeline

Status: In progress — pipeline and registry implemented; v3 candidate did not beat the base model.
Rebuild reproduction and CI evidence are pending.

Scope:

- Dataset normalize, dedup, PII scrub, contamination check, splits, checksums, dataset card.
- Dataset registry.
- Training config schema, QLoRA runner, metrics, reproducibility metadata.
- Adapter merge and load check.
- Evaluation with baselines and thresholds.
- Model registry and release gates.
- Model cards and integration with LoRA jobs.
- Versioned recipe schema (`schema_version`), published as JSON Schema and enforced in CI.
- Schema fields for recipe visibility and artifact access, so private models do not require a
  schema break.
- In-repo `tuning/` tree with recipes, evals, manifests, results, and model cards.
- `manifest.lock` for base model revision, dataset and eval checksums, runner version, image
  digest, and license identifiers.
- Pinned `recipe_ref` on jobs and model versions; reject `main` and other mutable refs.
- Candidate vs released model versions; merge does not deploy.
- Separate CODEOWNERS for recipes, evals, and the recipe schema.
- Extraction of `tuning/` to the standalone recipes repository when a trigger fires.

Acceptance:

- [x] Dataset reproducible by checksum.
- [x] Dataset card complete.
- [x] Tiny-model CPU LoRA smoke passes.
- [x] Real-GPU QLoRA smoke passes when available.
- [x] Adapter and metrics attach to a model version.
- [x] Eval compares against baseline.
- [x] Model card generated.
- [x] Release gate blocks incomplete versions.
- [x] Admin can release or reject.
- [x] Recipe schema rejects unknown keys, unpinned refs, and disallowed model sources.
- [x] Recipe schema can represent a private recipe without exposing private data or weights.
- [x] `just validate-tuning` checks schema, dataset checksums, eval checksums, and contamination.
- [ ] Every recipe has `manifest.lock` and rebuilds from it. Manifest exists; rebuild reproduction
      is pending.
- [x] Job and model records store the full `recipe_ref`; no run uses a mutable ref.
- [ ] Rebuild reproduces the adapter checksum or eval score within a documented tolerance.
- [x] A recipe PR cannot change its own eval set; eval changes are versioned and separately
      approved.
- [x] Merged recipes remain candidates until the release gate passes.
- [x] `tuning/` depends only on the published package/schema, not on `apps/`.
- [ ] CI green.

The v3 candidate reproduced 68.3% (41/60) versus the base model's 70.0% (42/60), so the release gate
correctly blocks it. It is not a release candidate.

## Phase 5 — Inference

Goal: serve a released model through an OpenAI-compatible API with auth, rate limits, metering, and
points.

Scope:

- Proxy in front of an internal vLLM.
- `POST /v1/chat/completions`, `GET /v1/models`.
- API-key auth with `inference:write`.
- Per-key and per-user rate limits.
- Model readiness and warmup.
- Token metering, usage records.
- Points hold, settle, release.
- Streaming SSE and stable error mapping.
- No prompt or completion logging by default.

Acceptance:

- [ ] Models list works.
- [ ] Non-streaming and streaming chat work.
- [ ] Usage recorded.
- [ ] Holds and settlements correct.
- [ ] Insufficient quota rejected.
- [ ] Rate limit returns 429.
- [ ] Revoked key rejected.
- [ ] Model not ready returns 503.
- [ ] Timeout returns 504.
- [ ] Client disconnect releases unused hold.
- [ ] Load test passes.
- [ ] No prompt logging.
- [ ] CI green.

## Phase 6 — Web dashboard

Goal: contributor and admin UI for onboarding, workers, jobs, models, datasets, keys, points, and
admin operations.

Scope:

- Public: `/`, `/login`, `/docs`.
- Contributor: `/app`, onboarding, workers, jobs, models, datasets, API keys, points, settings.
- Admin: workers, jobs, models, datasets, points, audit.
- Next.js App Router, server components, TanStack Query, shadcn/ui.
- Generated TypeScript client from OpenAPI.
- Same-origin `/api/*` rewrite; no tokens in localStorage.
- Accessible, responsive, loading/empty/error states.

Acceptance:

- [ ] Login/logout works; protected routes redirect.
- [ ] Admin routes return 403 for non-admins.
- [ ] Onboarding completes.
- [ ] API key and worker token shown once.
- [ ] Worker status visible.
- [ ] Job list/detail/cancel works.
- [ ] Admin verify/reject/requeue works.
- [ ] Model/dataset pages work.
- [ ] Points and grant work.
- [ ] Audit log visible.
- [ ] Mobile/desktop layouts and accessibility checks pass.
- [ ] End-to-end tests pass.
- [ ] CI green.

## Phase 7 — Security and observability

Goal: a safe and operable beta.

Scope:

- Threat model, risk register, security checklist.
- Auth hardening, sandbox verification, secrets inventory, rotation.
- CodeQL, Trivy, Dependabot, detect-secrets, SBOM.
- Structured logs with no prompts or secrets.
- OpenTelemetry, Prometheus/Grafana, Sentry.
- Alerts and runbooks.
- SLOs for API, inference, jobs, and ledger reconciliation.
- Backups and restore drill.

Acceptance:

- [ ] Threat model reviewed.
- [ ] No secrets in git.
- [ ] Admin routes server-side gated.
- [ ] CSRF verified.
- [ ] Revoked credentials fail.
- [ ] Sandbox tests pass.
- [ ] No prompt logging.
- [ ] Traces/metrics/dashboards live.
- [ ] Alerts and runbooks exist.
- [ ] Backup restore verified.
- [ ] Security sign-off.

## Phase 8 — Deploy and beta

Goal: production-like deployment and a controlled beta.

Scope:

- Local, staging, production with separate data and secrets.
- API on Fly.io, web on Vercel, Neon Postgres, Upstash Redis, R2 storage.
- GPU host with internal vLLM and inference proxy.
- CI/CD, gated migrations, smoke tests, rollback, preview deployments.
- Pinned model and image versions.
- Beta: 3–10 workers, 10 users, 1M tokens, real jobs and settlements.

Acceptance:

- [ ] Staging and production live.
- [ ] API/web deployed.
- [ ] Postgres/Redis/R2 configured.
- [ ] GPU host serving.
- [ ] CI/CD works.
- [ ] Smoke tests pass and rollback rehearsed.
- [ ] Workers/users onboarded.
- [ ] 1M tokens served.
- [ ] Dashboards/alerts live.
- [ ] Backups verified.
- [ ] No critical incidents.

## Phase 9 — First public model release

Goal: release the first community model with credible evaluation.

Release gates:

- [ ] Dataset frozen and licensed.
- [ ] Training reproducible.
- [ ] Beats baseline on the primary metric.
- [ ] General regression within threshold.
- [ ] Safety passes.
- [ ] Latency and cost within budget.
- [ ] Model card and dataset card complete.
- [ ] License review passed.
- [ ] API serves the model.
- [ ] Governance approval.
- [ ] Release recipe, eval version, and manifest are in the standalone recipes repository at an
      immutable tag.
- [ ] Model version links the recipe tag, manifest SHA256, raw results, and model card.
- [ ] Served artifact was built from that tag and verified by rebuild or attestation.
- [ ] Recipe history and contributor attribution are public.

The Phase 9 release is the public community model. Private model commerce is a separate post-MVP
track and does not block or satisfy these gates.

Deliverables: final training run, evaluation report, safety report, model card, dataset card,
Hugging Face release, checksums, launch post, contributor attribution, monitoring, and a 30-day
review.

## Post-MVP branches

These are options, not sequential phases:

- Community inference routing.
- Multi-GPU or distributed training.
- More model sizes and domains.
- Private tuned models and paid access (requires legal, payments, and isolation work; see below).
- Enterprise or on-prem deployment.
- A second capability, such as structured extraction or code review.
- Community recipe CI: maintainer-triggered GPU evaluation for recipe pull requests.
- Recipe registry UI and per-recipe adoption metrics.
- Multiple base models and capability tracks in the recipes repository.

## Post-MVP track: private tuned models and paid access

Status: Direction accepted; product shape, revenue share, and legal model open.

Goal: a contributor can tune a model for a specific task, keep the recipe and weights private, and
earn money by selling access to the model, licensing it, or delivering a private tuning job.

This is a separate commercial track. It does not change the public community model, the open
recipes repository, or Community Points.

Product shapes (choose before implementation):

- Hosted private endpoint: the platform serves the private adapter to entitled customers and bills
  per token or subscription. Recommended first shape.
- Weight license: the contributor delivers the private adapter to a customer under a license; the
  platform handles delivery and compliance.
- Paid private tuning: a customer pays for a private tune on their data, with the contributor and
  platform sharing the fee.
- Dedicated capacity: a customer reserves GPU capacity and a private deployment.

Prerequisites:

- Legal entity, terms of service, acceptable use, privacy policy, and data processing agreements.
- Payment processor, invoicing, refunds, chargebacks, tax/VAT, KYC/AML where required, and
  contributor payouts.
- A fiat billing and payout ledger separate from the points ledger.
- Tenant isolation, encrypted private artifact storage, per-customer entitlements, and audit logs.
- A trusted or dedicated worker pool for private data. Anonymous community workers must not process
  private data.
- A rule that paid private work uses dedicated or paid capacity, not point-subsidized community
  compute.
- License review confirming that private weights and commercial use are permitted for the base
  model, data, and any public recipe used.
- A private-model gate: data rights, license compliance, safety/AUP, task quality, and model card.
  It does not use the public benchmark threshold.
- Revenue-share, ownership, dispute, and model-retirement policies.

Hard boundaries:

- Points remain non-monetary and cannot be bought, sold, transferred, redeemed for cash, or used to
  pay for private models.
- Private recipes and weights are not committed to the public recipes repository. They use the same
  schema and manifest contract in tenant-scoped storage.
- Private data never enters public datasets or the public model without explicit, documented
  consent.
- Private recipes, weights, and data are not used to improve the public model without explicit,
  documented consent.
- Private commercial training uses dedicated or paid capacity, never point-subsidized community
  jobs.
- Derivatives of the public community model keep their public license, attribution, and model-card
  obligations.
- No paid service starts before legal, payment, and security sign-off.

Future acceptance:

- [ ] A contributor can offer a private model to entitled customers.
- [ ] Usage is metered and billed in fiat.
- [ ] Contributor payouts reconcile with charges, refunds, and chargebacks.
- [ ] Private artifacts are isolated per tenant and encrypted at rest.
- [ ] Private data training runs only on trusted or dedicated workers.
- [ ] Private-model safety and license gates block incomplete listings.
- [ ] Points and fiat ledgers cannot be converted into each other.
