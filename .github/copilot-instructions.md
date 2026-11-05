# GitHub Copilot Instructions

The canonical repository instructions are in `AGENTS.md`. Read that file first.

Key points:

- Python 3.12 monorepo managed by `uv`; web app uses Next.js and `pnpm`.
- `just lint`, `just typecheck`, `just test`, and `just build` are the definition-of-done checks.
- The MVP model is `ibm-granite/granite-4.1-3b` base. Current adapters are research artifacts.
- Never commit `.env`, API keys, worker tokens, prompts, or private data.
- Points are non-contractual, non-transferable, and have no cash value.
- Add tests and update docs for behavior changes.
- Use `.opencode/skills/*/SKILL.md` for repeatable workflows and `docs/architecture.md` for
  boundaries.
