---
description: Add a typed API endpoint with protocol, tests, and docs
agent: build
---

Add or change an API endpoint for: $ARGUMENTS

Follow `docs/architecture.md` and `.opencode/skills/api-change/SKILL.md`.

Required:

1. Define request/response models in `packages/protocol` when they cross a service boundary.
2. Add the route under `apps/api/src/community_llm_api/api/`.
3. Add tests under `apps/api/tests/`.
4. Update the SDK or generated client if consumers need it.
5. Update docs when behavior or error codes change.
6. Run `just lint`, `just typecheck`, and `just test`.

Do not add a migration unless the database schema changes.
