---
name: Repository Workflow
description: Bootstrap, run, test, and change the Community LLM monorepo safely
---

# Repository Workflow

## Bootstrap

```sh
mise install
just bootstrap
cp .env.example .env   # only if .env does not exist
just compose-up
```

`just bootstrap` runs `uv sync --all-packages`, installs web dependencies, and creates `.env` from
`.env.example` only when it is missing. Never print or commit `.env`.

## Run

| Service | Command |
|---|---|
| API | `just api` (port 8000) |
| Web | `just web` (port 3000) |
| Inference proxy (post-MVP) | `just inference` (port 8001) |
| Worker CLI | `just worker` |
| Dependencies | `just compose-up` |

The web app rewrites `/api/*` to the control plane. API docs are available at
`http://localhost:8000/docs`.

## Checks

```sh
just lint
just typecheck
just test
just build
```

Definition of done:

- Tests cover behavior, not implementation details.
- Types and lint pass.
- Docs and ADRs are updated when behavior, commands, or architecture change.
- A migration is included when the schema changes.
- No `.env`, key, token, or private data is staged.
- `git diff` is reviewed before handoff.

## Conventions

- Python 3.12, `uv`, `ruff`, `mypy`, `pytest`, Pydantic v2.
- TypeScript strict, Next.js App Router, Tailwind.
- Keep research code in `spikes/`; production code lives in `apps/` and `packages/`.
- Do not add a framework, queue, database, or cloud dependency without an ADR.
- Points are non-contractual, non-transferable, and have no cash value.

## When to stop and ask

- A change needs a new cloud account, paid service, or GPU rental.
- A command would delete data, rewrite history, or force-push.
- A test requires production credentials.
- A model or dataset license is unclear.
