# Roadmap Status

Date: 2026-11-06
Current phase: Phase 5 — Packaging and distribution (planning)
Overall status: Phase 4 complete; v3 is below the base model and is not a release candidate;
distribution-first releases are next

## Snapshot

| Area | State | Evidence |
|---|---|---|
| Phase 0 model selection | Done | ADR-0002 |
| Phase 0 issue-tracker eval | Done | `spikes/issue_tracker/results/README.md` |
| Phase 0 fine-tuning | Not validated | base 70.0% vs v1 53.3% vs v2 68.3% |
| Phase 0 interviews | Open | `docs/specs/validation.md` |
| Phase 0 legal review | Open | `docs/legal/checklist.md` |
| Phase 1 scaffold | Built | this repository |
| Phase 1 verification | Passed locally and in CI | see table below |
| Phase 2 | Complete | users, sessions, OAuth, API keys, workers, jobs, ledger, audit, sandbox; CI green |
| Phase 3 | Complete (fake-GPU) | worker protocol, leases, retries, artifact checksums, fake-GPU E2E; CI green |
| Phase 4 | Complete | dataset pipeline, recipe validation, QLoRA, GPU smoke, base/adapter eval, registry, manifest rebuild; CI green |
| Phase 5 | Planning | distribution-first Hugging Face and local/mobile artifacts |

## Phase 0 evidence

- Base Granite 4.1 3B: 70.0% (42/60), p50 1,075ms.
- Adapter v1: 53.3% (32/60), p50 7,110ms.
- Adapter v2: 68.3% (41/60), p50 1,289ms.
- V2 data: 800 examples, no eval prompt overlap, max 2,526 tokens.
- Decision: keep the base model as the distributable baseline; keep adapters as research artifacts.

Full detail: `spikes/issue_tracker/results/README.md`.

## Phase 1 deliverables

- Python workspace: `apps/api`, `apps/worker`, `apps/inference`, `packages/protocol`,
  `packages/sdk-python`, `ml`.
- Next.js app in `apps/web`.
- Compose stack: Postgres 16, Redis 7, RustFS 1.0.4, Mailpit.
- API: `/healthz`, `/readyz`, `/v1/meta`.
- Worker: `version`, `doctor`.
- Inference proxy: `/healthz`, `/readyz`, `/v1/models`.
- CI: Python lint/format/typecheck/test, web lint/typecheck/test/build, container builds, compose
  config, Trivy.
- CodeQL and Dependabot.
- AI setup: `AGENTS.md`, `opencode.jsonc`, 4 skills, 9 commands, 3 reviewer agents, Copilot and
  Cursor instructions.
- Docs: architecture, roadmap, ADRs, contributing, security, conduct, governance.

## Phase 1 verification

| Check | Result |
|---|---|
| `uv sync --all-packages` | Pass |
| `just bootstrap` | Pass |
| `just dev` | Pass (API :8020, web :3001 during verification) |
| `just lint` | Pass |
| `just typecheck` | Pass (28 files) |
| `just test` | Pass (40 tests, 65 subtests) |
| `just build` | Pass (web + 4 container images) |
| `docker compose config` | Pass |
| Compose services healthy | Pass (Postgres, Redis, RustFS, Mailpit) |
| RustFS buckets | Pass (`artifacts`, `datasets`, `models`, `logs`) |
| API health/readiness/meta | Pass (local and container) |
| Web loads | Pass (local and container) |
| Worker `version` / `doctor` | Pass |
| Pre-commit | Pass |
| Trivy (CRITICAL/HIGH, unfixed ignored) | Pass (no findings) |
| actionlint | Pass |
| OpenCode config and custom agents | Load successfully |
| `mise install` | Pass (Python 3.12.16, Node 22.23.4, pnpm 12.16.1, uv 0.13.7, just 1.59) |
| GitHub CI | Pass ([run 42113861255](https://github.com/alexhanvey/model-commons/actions/runs/42113861255)) |
| GitHub CodeQL | Pass ([run 42113861552](https://github.com/alexhanvey/model-commons/actions/runs/42113861552)) |

Update this table only with real command output or a CI link.

## Phase 2 progress

- Database: async SQLAlchemy engine/session, Alembic scaffold, and `users` and `sessions` migrations.
- GitHub OAuth login, server-side sessions, CSRF-protected logout, and `GET /v1/me`.
- API keys with scopes (`inference:write`, `jobs:read`, `jobs:write`), hashed at rest, with
  create/list/revoke.
- Worker registration, admin approval, heartbeat, and revoke. Worker tokens use a `wrk_` prefix and
  are hashed at rest.
- Job creation, listing, detail, and cancellation with an explicit state machine. Illegal
  transitions return 409.
- Double-entry ledger with accounts, transactions, and entries. Posting validates balanced
  debits/credits, supports idempotency keys, rejects negative user balances, and records admin
  grants.
- Point balance and transaction history endpoints.
- Ledger reconciliation endpoint and `just ledger-reconcile`.
- `gpu_devices`, `artifacts`, and `idempotency_keys` tables are in place for Phase 3.
- Python SDK covers auth, API keys, workers, jobs, points, and admin grants.
- Audit events for ledger grants and job create/cancel.
- Session tokens are hashed at rest; cookies are HttpOnly, SameSite=Lax, and Secure outside
  local/test.
- Admin status comes from `COMMUNITY_LLM_ADMIN_GITHUB_IDS`.
- No-Docker sandbox: `scripts/sandbox` downloads and runs PostgreSQL 16.9.1 natively.
  `just sandbox-up` starts it and applies migrations; `just sandbox-check` validates `.env`.
- `just migrate` and `just migration <name>` are wired.
- CI runs `alembic upgrade head` and `alembic check` against a Postgres 16 service.
- Local verification: `ruff`, `mypy`, and `pytest` pass. All 97 tests, including the Postgres
  migration test, pass against the native sandbox database; `alembic check` passes. Web lint,
  typecheck, and formatting pass.
- Phase 2 CI green ([run 42267648845](https://github.com/alexhanvey/model-commons/actions/runs/42267648845)).

## Phase 3 progress

- Worker job protocol: atomic next-job assignment, attempt leases, start/heartbeat/complete/fail,
  artifact upload, and result logs.
- Lease expiry requeues jobs up to `max_job_attempts`; failures retry then fail.
- Workers can only access their own attempts.
- Artifacts are SHA-256 checked and stored under `.sandbox/artifacts`; logs are redacted.
- Admin verify/reject; successful jobs pay once through the ledger.
- Worker CLI: `register`, `doctor`, `status`, `benchmark`, `run --fake-gpu`, and `logs`.
- Fake-GPU end-to-end tests cover benchmark, eval, and LoRA smoke jobs.
- Real Docker/GPU sandbox execution remains open; the current executor is the fake-GPU path.
- Local verification: 118 tests pass, including the Postgres migration test; ruff, mypy, web lint,
  typecheck, formatting, and build pass.
- Phase 3 CI green ([run 42271051686](https://github.com/alexhanvey/model-commons/actions/runs/42271051686)).

## Phase 4 progress

- Dataset pipeline: normalize, exact/prompt dedup, PII scrub, contamination check, deterministic
  splits, SHA-256 checksums, manifest, and dataset card.
- Closed recipe schema and manifest lock with pinned base revisions, dataset/eval checksums,
  licenses, visibility, and eval version locks.
- Repo-shaped `tuning/` tree with a v3 recipe, eval set, rubric, model card, and run results.
- `just validate-tuning` checks schema, manifests, local asset checksums, contamination, and schema
  freshness.
- Config-driven QLoRA runner with a tiny-model CPU smoke and a real RTX 4090 QLoRA run.
- Real base-vs-adapter eval: base **70.0% (42/60)**, v3 adapter **68.3% (41/60)**. The v3 candidate
  did not beat the base and is not a release candidate.
- Manifest rebuild on 2026-11-06: **66.7% (40/60)**, one case below the original and within the
  documented tolerance; release decision unchanged. Evidence is in
  `tuning/recipes/granite-4.1-3b/issue-tracker/v3/results/rebuild-v3/`.
- Model registry and release gate: candidate/released/rejected states, pinned `recipe_ref`,
  metrics, model card, admin release/reject, and a gate that blocks underperformance, regression,
  safety failure, mutable refs, or missing artifacts.
- Jobs can store a pinned `recipe_ref`; model versions store the same ref.
- Local verification: 139 tests (1 skipped), including the Postgres migration test; ruff, mypy, web
  checks, CPU LoRA smoke, GPU QLoRA smoke, and base/adapter eval pass.
- Phase 4 CI green ([run 42287033122](https://github.com/alexhanvey/model-commons/actions/runs/42287033122));
  PR #10 is merged (`8ad4b76`).

Remaining Phase 4 work: none. The next recipe needs to beat the base model; the LoRA-job-to-registry
automation is a Phase 5 integration item.

## Distribution-first plan

ADR-0006 makes downloadable model releases the first-class output. Hosted inference is post-MVP.
The plan now includes:

- Hugging Face model repos with adapters, merged weights where licensed, GGUF, MLX, model cards,
  eval results, licenses, manifests, and checksums.
- Runtime quickstarts for llama.cpp, Ollama, LM Studio, and MLX.
- A mobile tier at 0.5–1.5B parameters, alongside the laptop/server 1–3B tier.
- No platform-hosted inference or persistent GPU serving host in the MVP.
- Points as recognition, job-queue priority, and early access until hosted inference exists.

## Architecture decisions

- ADR-0004: engine and recipe split, with `tuning/` in Phase 4 and extraction before Phase 9.
- ADR-0005: private tuned models and paid access, as a separate post-MVP track.
- ADR-0006: distribution-first releases through Hugging Face and local/mobile runtimes; no hosted
  inference in the MVP.

## Known gaps

- The sandbox installs `just` and pnpm into `~/.local/bin`; add it to `PATH` or use `mise`.
- GPU-backed training is unavailable in the sandbox. Use an external GPU host or Vast with explicit
  approval. Hosted inference is post-MVP.
- Worker jobs still use the fake-GPU executor. The real GPU worker executor and LoRA-job-to-registry
  automation are pending.
- The Phase 4 v3 candidate did not beat the base model; a release candidate is still needed.
- `manifest.lock` and `run.json` record `image_digest: local-dev`; pin a real runner image digest
  before a release.
- Hosted inference and community inference routing are post-MVP under ADR-0006.
- The mobile tier base model, runtime, and on-device evaluation matrix are open.
- The worker artifact store is the local filesystem under `.sandbox/artifacts`; production R2
  presigned uploads are not wired yet.
- The web app has a landing page and GitHub sign-in. The full contributor dashboard is Phase 6.
- The API has users, sessions, API keys, workers, jobs, the ledger, and audit events. Phase 2 is
  complete and merged.
- The Python SDK is current with the Phase 2 API. The generated TypeScript client is Phase 6.
- The ledger currently supports integer grants and spends. Inference holds, settlements, refunds,
  and metering are post-MVP with hosted inference.
- The inference proxy has no upstream vLLM connection; it is post-MVP.
- MinIO was replaced by RustFS for local storage because the MinIO images were removed in 2026.
  See ADR-0003.
- Phase 0 interviews, commitments, legal review, release terms, and points-policy review remain
  open. Do not invite external beta users yet.

## Next actions

1. Start Phase 5: adapter merge, GGUF/MLX artifacts, release manifest and checksums, Hugging Face
   repo, download page, runtime quickstarts, and the mobile-tier decision.
2. Design a v4 recipe targeting confirmation and no-tool restraint; do not release an adapter that
   does not beat the base model.
3. Add LoRA-job-to-registry automation and the real GPU worker executor.
4. Run Phase 0 interviews and legal review in parallel; do not mark them complete without evidence.
