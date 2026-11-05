---
description: Plan and add a safe Alembic migration
agent: build
---

Create a database migration for: $ARGUMENTS

Before editing, read `docs/architecture.md` and `.opencode/skills/api-change/SKILL.md`.

Required:

1. Describe the current schema and the intended change.
2. Use a reversible Alembic migration with a downgrade path.
3. Add indexes and constraints deliberately; avoid table rewrites on large tables.
4. Include a backfill plan when existing rows are affected.
5. Add tests for the new constraints or ledger behavior.
6. Run migrations against a fresh local database and run the test suite.

Do not edit an applied migration. Add a new revision instead.
