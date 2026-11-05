# Contributing

Thanks for helping build a community-owned small-model lab. This project is early; small,
well-tested changes are more useful than large speculative ones.

## Before you start

- Read [`AGENTS.md`](AGENTS.md) and [`docs/architecture.md`](docs/architecture.md).
- For a bug or a behavior change, open an issue first.
- For a new dependency, service, or architecture change, propose an ADR in `docs/adr/`.
- Never include secrets, private data, prompts from real users, or production artifacts.

## Setup

Prerequisites: Git, Docker, [`mise`](https://mise.jdx.dev/), and a POSIX shell. `mise install`
provides Python 3.12, Node 22, `pnpm`, `uv`, and `just`.

```sh
git clone <your-fork-url> community-llm
cd community-llm
mise install
just bootstrap
cp .env.example .env   # only if .env is missing
just compose-up
just api               # terminal 1
just web               # terminal 2
```

If you do not use `mise`, install Python 3.12, `uv`, Node 22, `corepack enable`, `pnpm`, and `just`
yourself. The versions are pinned in `mise.toml`.

## Checks

Run these before opening a pull request:

```sh
just lint
just typecheck
just test
just build
```

`just build` builds the web app and container images; it is slower. Run it when you change a
Dockerfile, dependency, or build configuration.

Pre-commit is optional but recommended:

```sh
uv run pre-commit install
uv run pre-commit run --all-files
```

## Pull requests

- Keep the change focused. Separate refactors from behavior changes.
- Add a test that fails without your fix.
- Update docs, ADRs, and `.env.example` when behavior or configuration changes.
- Include a migration when the database schema changes.
- Describe security implications in the PR.
- Do not commit `.env`, lockfile churn unrelated to the change, or generated artifacts.
- AI-assisted contributions are welcome. You are responsible for reviewing the result and for the
  accuracy of the description.

The PR template includes the full checklist.

## Code conventions

### Python

- Python 3.12, type hints on public functions.
- `ruff` for lint and format, `mypy` for types, `pytest` for tests.
- Pydantic v2 models at service boundaries.
- Prefer small pure functions for scoring, parsing, and ledger math.
- Do not log prompts, completions, API keys, or worker tokens.

### TypeScript

- Strict mode, Next.js App Router.
- Server components by default; use client components only for interaction.
- No tokens in `localStorage`.
- Keep API calls same-origin through `/api/*`.

### Research code

`spikes/` holds Phase 0 experiments. It is not production code, but it should still be
reproducible. Record the command, dataset checksum, model revision, and raw results.

## Data and model contributions

- Only contribute data you have the right to license.
- Record the source, license, and preprocessing steps.
- Do not add data that contains personal information, credentials, or private conversations.
- A fine-tuned adapter is not a release candidate until it beats the base model on the primary
  metric without an unacceptable category regression.

## Points and governance

Points are a beta accounting mechanism. They are non-contractual, non-transferable, have no cash
value, and may expire. Contributing does not create equity, employment, or a financial claim.

See [`GOVERNANCE.md`](GOVERNANCE.md) and [`docs/points-policy.md`](docs/points-policy.md).

## License

By contributing, you agree that your contribution is licensed under the Apache License 2.0. See
[`LICENSE`](LICENSE).
