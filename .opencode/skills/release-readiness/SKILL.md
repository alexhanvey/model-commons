---
name: Release Readiness
description: Evaluate model, dataset, and distribution release gates before publishing
---

# Release Readiness

This is a gate report, not an approval. Do not publish, tag, upload, or announce anything until a
maintainer explicitly approves.

## Gates

| Gate | Evidence |
|---|---|
| Dataset license | License review and source link; redistribution allowed |
| Dataset frozen | Checksum, split sizes, contamination check |
| Training reproducible | Config, code revision, seeds, package versions, manifest rebuild |
| Primary metric | Same harness and parser as baseline; per-category results |
| Regression guard | Generic tool-use, no-tool restraint, and safety results |
| Artifact integrity | SHA-256 checksums, release manifest, recipe and base revisions |
| Runtime compatibility | Adapter loads; GGUF Q4_K_M/Q5_K_M load in llama.cpp/Ollama; MLX where practical |
| Model card | Intended use, limits, eval results, runtimes, licenses |
| Dataset card | Source, license, preprocessing, known gaps |
| Mobile tier | Reference-device matrix and on-device tool-call results, if mobile |
| Security | No secrets or prompt logging; signed/checksummed artifacts; supply-chain review |
| Governance | Maintainer approval and license review |

Hosted serving is post-MVP. Do not include a vLLM deployment or public inference endpoint in an MVP
release gate.

## Rules

- A release candidate must beat the base model on the primary metric.
- A gain that hides a category collapse is a rejection.
- Do not compare runs produced by different harnesses or parsers.
- Do not release an adapter trained on data with unclear licensing.
- Do not publish a negative result as a model release; record it as a research result.
- Do not claim mobile support from desktop benchmarks alone.
- Do not claim frontier-model capability.
- Points are not equity, money, or a transferable asset.

## Output

Write a short report with each gate marked pass, fail, or unknown, link the evidence, and list the
blockers. If any gate is unknown, the release is not ready.
