---
description: Check release gates before publishing a model
agent: build
---

Assess release readiness for: $ARGUMENTS

Follow `.opencode/skills/release-readiness/SKILL.md`.

Do not publish, tag, or upload anything yet. Produce a gate-by-gate report with evidence links:
dataset license and checksum, training reproducibility, baseline comparison, category regressions,
safety, latency and cost, model card, dataset card, license review, and serving readiness. List
blockers explicitly and ask for approval before any external action.
