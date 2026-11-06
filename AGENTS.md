# AGENTS.md

Canonical instructions for coding agents working in this repository.

## What this is

A community-owned small-model lab and inference co-op. The MVP lets contributors run verified
evaluation and LoRA jobs, earn best-effort points, and use those points for inference on a small
open model.

The selected MVP model is `ibm-granite/granite-4.1-3b` base. The current fine-tuned adapters are
research artifacts, not release candidates.

## Commands

```sh
just bootstrap   # install deps and local env
just compose-up  # Postgres, Redis, RustFS, Mailpit
just sandbox-up  # native Postgres without Docker
just sandbox-down
just sandbox-status
just sandbox-check
just sandbox-tunnel
just ledger-reconcile # check ledger invariants
just migrate     # apply database migrations
just api         # control-plane API
just web         # Next.js app
just worker      # worker CLI help
just inference   # inference proxy
just test        # all tests
just lint        # Python + web lint
just typecheck   # Python + web type checks
just build       # web build + container builds
```

## Architecture

- `apps/api` — FastAPI control plane.
- `apps/web` — Next.js dashboard.
- `apps/worker` — GPU worker agent.
- `apps/inference` — OpenAI-compatible inference proxy.
- `packages/protocol` — shared Pydantic models.
- `packages/sdk-python` — Python client.
- `ml` — dataset, training, evaluation, model cards.
- `tuning` — model tuning recipes, evals, and manifests (Phase 4; extracted to a standalone repo).
- `infra/compose` — local dependencies.
- `scripts/sandbox` — no-Docker local Postgres, bootstrap, and tunnel helpers.
- `spikes` — Phase 0 research artifacts, not production code.

## Conventions

- Python 3.12, `uv`, `ruff`, `mypy`, `pytest`.
- TypeScript strict, Next.js App Router.
- Pydantic v2 models at boundaries.
- No secrets in git. `.env` is ignored.
- Keep changes small and task-focused.
- Add tests for behavior, not implementation details.
- Update docs when commands, APIs, or architecture change.

## Safety

- Do not commit `.env`, API keys, worker tokens, prompts, or private data.
- Do not expose vLLM publicly.
- Do not run an unpinned or unreviewed tuning recipe.
- Do not mix private-model revenue with Community Points; paid services require legal and security
  review.
- Do not put private recipes, weights, or customer data in the public recipes repository.
- Do not run destructive Vast actions without explicit user approval.
- Do not treat points as money, equity, or a transferable asset.
- Do not claim frontier-model capability.

## Definition of done

- Tests pass.
- Types pass.
- Lint passes.
- Docs updated.
- Migration included if schema changed.
- OpenAPI/client regenerated if API changed.
- Recipe schema, manifest, and eval set updated if tuning behavior changed.
- Security implications considered.
- Agent skills updated if the workflow changed.

## Skills

Use `.opencode/skills/*/SKILL.md` for repeatable workflows. See `.opencode/README.md`.
