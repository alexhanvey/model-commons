# OpenCode Setup

This directory contains project-local instructions for coding agents. `AGENTS.md` is canonical.

## Layout

```text
.opencode/
├── agents/       # read-only reviewer subagents
├── commands/     # slash commands
└── skills/       # repeatable workflows
opencode.jsonc    # project config, permissions, instruction files
```

## Commands

| Command | Purpose |
|---|---|
| `/check` | Run lint, typecheck, and tests |
| `/review` | Correctness and regression review |
| `/security-review` | Security review |
| `/ml-review` | ML and eval integrity review |
| `/new-endpoint` | Add a typed API endpoint |
| `/db-migration` | Plan and add a migration |
| `/run-evals` | Run an evaluation experiment |
| `/release-model` | Check release gates |
| `/phase-status` | Update the roadmap status |

## Skills

| Skill | Use when |
|---|---|
| `repo-workflow` | Bootstrapping, running, testing, or changing the repo |
| `ml-experiment` | Renting a GPU or running training/eval |
| `api-change` | Adding endpoints, protocol models, or migrations |
| `release-readiness` | Preparing a model or dataset release |

Agents load skills automatically by description. You can also ask for one by ID.

## Permissions

`.env`, private keys, and SSH keys are read-denied. Destructive git, Docker, and GitHub actions
require approval. GPU rentals require approval. See `opencode.jsonc`.

## Adding a skill or command

- Skill: `.opencode/skills/<kebab-case-id>/SKILL.md` with `name` and `description` frontmatter.
- Command: `.opencode/commands/<name>.md`; the body is the prompt template, `$ARGUMENTS` is
  supported.
- Agent: `.opencode/agents/<name>.md`; use `mode: subagent` and explicit permissions.

Keep instructions short enough to be read on every task, and point to docs instead of duplicating
them.
