# Roadmap Status

Date: 2026-11-05
Current phase: Phase 1 complete; Phase 2 next
Overall status: CI green; tagged `v0.1.0-scaffold`

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
| Phase 2 | Not started | — |

## Phase 0 evidence

- Base Granite 4.1 3B: 70.0% (42/60), p50 1,075ms.
- Adapter v1: 53.3% (32/60), p50 7,110ms.
- Adapter v2: 68.3% (41/60), p50 1,289ms.
- V2 data: 800 examples, no eval prompt overlap, max 2,526 tokens.
- Decision: serve the base model; keep adapters as research artifacts.

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

## Known gaps

- The development machine does not have `uv`, `pnpm`, or `just` globally; use `mise` or install
  them manually before `just bootstrap`.
- The web app is a landing page only. Auth and dashboard routes are Phase 2 and Phase 6.
- The API has no database, auth, jobs, or ledger yet. Those are Phase 2.
- The inference proxy has no upstream vLLM connection yet. That is Phase 5.
- MinIO was replaced by RustFS for local storage because the MinIO images were removed in 2026.
  See ADR-0003.
- Phase 0 interviews, commitments, legal review, release terms, and points-policy review remain
  open. Do not invite external beta users yet.

## Next actions

1. Start Phase 2: database, auth, workers, jobs, ledger, and audit.
2. Merge or close Dependabot PR #2 once its rebased CI run is green.
3. Run Phase 0 interviews and legal review in parallel; do not mark them complete without evidence.
