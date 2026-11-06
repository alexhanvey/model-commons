# Community LLM

[![CI](https://github.com/alexhanvey/model-commons/actions/workflows/ci.yml/badge.svg)](https://github.com/alexhanvey/model-commons/actions/workflows/ci.yml)
[![CodeQL](https://github.com/alexhanvey/model-commons/actions/workflows/codeql.yml/badge.svg)](https://github.com/alexhanvey/model-commons/actions/workflows/codeql.yml)

A community-owned small-model lab and inference co-op.

Contributors run verified evaluation and LoRA jobs on their GPUs, earn best-effort points, and spend
those points on an OpenAI-compatible inference API serving a small open model. The MVP focuses on
tool use / function calling for agent builders.

> Points are non-contractual, non-transferable, have no cash value, and may expire. There is no
> token, blockchain, payments, or credit exchange in the MVP. Private-model commerce is a post-MVP
> track.

## Status

**Phase 2 — core backend and ledger (in progress).** Phase 1 is tagged `v0.1.0-scaffold`: the
monorepo, API/web/worker/inference skeletons, local dependencies, CI, and AI-agent setup are in
place, and GitHub CI passes. Phase 2 has started with the database and auth foundation: async SQLAlchemy, Alembic migrations,
`users` and `sessions` tables, GitHub OAuth, and CSRF-protected sessions. See
[`docs/roadmap/status.md`](docs/roadmap/status.md).

Phase 0 selected `ibm-granite/granite-4.1-3b` as the base model and built a 60-case GitHub-style
issue-tracker tool-calling eval. Results:

| Model | Passed | Rate | p50 |
|---|---:|---:|---:|
| Granite 4.1 3B base | 42/60 | **70.0%** | 1,075ms |
| Issue-tracker adapter v1 | 32/60 | 53.3% | 7,110ms |
| Issue-tracker adapter v2 | 41/60 | 68.3% | 1,289ms |

Neither adapter beat the base model. The MVP serves the base model; the adapters remain research
artifacts. See [`spikes/issue_tracker/results/README.md`](spikes/issue_tracker/results/README.md).

## What the MVP will do

1. A contributor signs in and registers a GPU worker.
2. The worker runs a benchmark, a verified evaluation, or a LoRA fine-tune.
3. The platform verifies the job and issues points.
4. The community model is served through an OpenAI-compatible API.
5. Contributors spend points on inference.

The first capability is tool use / function calling. The first narrow domain is GitHub-style
issue-tracker tool calling against a deterministic mock API. No real GitHub access is used.

Out of scope for the MVP: pretraining, distributed training across home GPUs, community inference
routing, paid inference, private model commerce, tokens, blockchain, enterprise deployment, and 7B+
models.

Long-term, contributors may offer privately tuned models for specific tasks and earn money from
them. That is a separate commercial track with its own legal, billing, and isolation requirements;
see [ADR-0005](docs/adr/0005-private-model-commerce.md).

## Quickstart

Prerequisites:

- Git and Docker with Compose, or the no-Docker sandbox below.
- [`mise`](https://mise.jdx.dev/) (recommended), or Python 3.12, [`uv`](https://docs.astral.sh/uv/),
  Node 22, `pnpm`, and [`just`](https://github.com/casey/just).

```sh
git clone <your-fork-url> community-llm
cd community-llm
mise install
just bootstrap   # creates .env from .env.example if missing
just compose-up
```

Or run both app services with `just dev`. To run them separately:

```sh
just api          # http://localhost:8000  (docs at /docs)
just web          # http://localhost:3000
just inference    # http://localhost:8001
just worker       # worker CLI help
```

### No Docker (Linux sandbox)

On Linux without Docker, use the native Postgres sandbox:

```sh
bash scripts/sandbox/bootstrap.sh
export PATH="$HOME/.local/bin:$PATH"
just sandbox-up
just sandbox-check
just dev
```

See [`docs/runbooks/local-sandbox.md`](docs/runbooks/local-sandbox.md) for OAuth, tunnels, and
limitations.

Local dependencies:

| Service | Port | Purpose |
|---|---:|---|
| Postgres 16 | 5433 | Control-plane state |
| Redis 7 | 6379 | Queues and rate limits |
| RustFS | 9000 / 9001 | S3-compatible storage and console |
| Mailpit | 1025 / 8025 | Local email capture |

RustFS replaces MinIO because the MinIO images were removed in 2026; see
[ADR-0003](docs/adr/0003-local-object-storage.md).

## Checks

```sh
just lint
just typecheck
just test
just build
```

`just build` builds the web app and container images. It is slower and is not required for every
small change.

Pre-commit:

```sh
uv run pre-commit install
uv run pre-commit run --all-files
```

## Repository layout

```text
apps/
  api/          FastAPI control plane
  web/          Next.js dashboard
  worker/       GPU worker agent
  inference/    OpenAI-compatible inference proxy
packages/
  protocol/     Shared Pydantic models
  sdk-python/   Python client
ml/             Dataset, training, evaluation, model cards
infra/compose/  Local Postgres, Redis, RustFS, Mailpit
docs/           Architecture, ADRs, specs, roadmap, policies
spikes/         Phase 0 research code and results
.opencode/      Agent skills, commands, and read-only reviewers
```

Model tuning recipes will live in a standalone `model-commons/recipes` repository. Phase 4 creates
a repo-shaped `tuning/` tree here first; see
[ADR-0004](docs/adr/0004-engine-recipe-split.md).

## AI-agent setup

- [`AGENTS.md`](AGENTS.md) is the canonical instruction file.
- `CLAUDE.md` points to it; `.github/copilot-instructions.md` and `.cursor/rules/project.mdc` carry
  the short version.
- [`opencode.jsonc`](opencode.jsonc) configures permissions and instructions.
- `.opencode/skills/` contains repeatable workflows; `.opencode/commands/` contains slash commands;
  `.opencode/agents/` contains reviewer subagents. See [`.opencode/README.md`](.opencode/README.md).

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — components, boundaries, data flow, security.
- [`docs/roadmap/implementation.md`](docs/roadmap/implementation.md) — phases and exit gates.
- [`docs/roadmap/status.md`](docs/roadmap/status.md) — current status and known gaps.
- [`docs/specs/mvp.md`](docs/specs/mvp.md) — MVP scope and success metrics.
- [`docs/evaluation.md`](docs/evaluation.md) — evaluation design.
- [`docs/points-policy.md`](docs/points-policy.md) — non-contractual beta points.
- [`docs/data-policy.md`](docs/data-policy.md) — data and licensing rules.
- [`docs/runbooks/`](docs/runbooks/) — operational setup and recovery notes.
- [GitHub OAuth setup](docs/runbooks/github-oauth.md) — local OAuth app, sessions, and CSRF.
- [Local sandbox without Docker](docs/runbooks/local-sandbox.md) — native Postgres, API, and web.
- [`docs/adr/`](docs/adr/) — architecture decisions.
- [`docs/legal/checklist.md`](docs/legal/checklist.md) — legal and licensing checklist.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`GOVERNANCE.md`](GOVERNANCE.md). For security issues,
use private reporting as described in [`SECURITY.md`](SECURITY.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE). Model and dataset licenses are tracked separately in
[`docs/data-policy.md`](docs/data-policy.md).
