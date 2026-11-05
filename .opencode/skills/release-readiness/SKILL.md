---
name: Release Readiness
description: Evaluate model, dataset, and inference release gates before publishing
---

# Release Readiness

This is a gate report, not an approval. Do not publish, tag, upload, or announce anything until a
maintainer explicitly approves.

## Gates

| Gate | Evidence |
|---|---|
| Dataset license | License review and source link |
| Dataset frozen | Checksum, split sizes, contamination check |
| Training reproducible | Config, code revision, seeds, package versions |
| Primary metric | Same harness and parser as baseline; per-category results |
| Regression guard | Generic tool-use, no-tool restraint, and safety results |
| Latency and cost | p50/p95, GPU type, hourly cost, tokens/sec |
| Model card | Intended use, limits, eval results, license |
| Dataset card | Source, license, preprocessing, known gaps |
| Serving | vLLM config, model revision, warmup, readiness check |
| Security | No secrets or prompt logging; private vLLM; auth and rate limits |
| Governance | Maintainer approval and points-policy review |

## Rules

- A release candidate must beat the base model on the primary metric.
- A gain that hides a category collapse is a rejection.
- Do not compare runs produced by different harnesses or parsers.
- Do not release an adapter trained on data with unclear licensing.
- Do not claim frontier-model capability.
- Points are not equity, money, or a transferable asset.

## Output

Write a short report with each gate marked pass, fail, or unknown, link the evidence, and list the
blockers. If any gate is unknown, the release is not ready.
