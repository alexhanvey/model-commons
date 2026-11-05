# Governance

Status: Draft for the beta. This document is not a legal agreement.

## Principles

- The project is community-owned in intent: contributors should be able to inspect, run, and help
  improve the models, datasets, and platform.
- Decisions are documented in `docs/adr/` and `docs/specs/decisions.md`.
- Security and user safety take priority over growth.
- Points are a beta accounting mechanism, not equity, money, or a transferable asset.

## Roles

### Maintainers

Maintainers merge changes, manage releases, and protect the security and integrity of the platform.
The current maintainers are listed in `.github/CODEOWNERS`. Maintainers are added by consensus of
existing maintainers.

### Contributors

Anyone who submits code, data, documentation, evaluations, or GPU time under the project's
policies. Contributions are licensed under Apache-2.0 unless stated otherwise.

### Admins

Admins operate the deployed control plane and GPU host. They approve workers, verify jobs, grant
points, and release models. Admin actions must be auditable. Admin access is limited to trusted
maintainers during the beta.

## Decision making

- Routine changes: pull-request review by one maintainer.
- Architecture, security, licensing, points, or model release changes: an ADR or spec change,
  reviewed by at least two maintainers when available.
- Deadlocks: the maintainers decide by rough consensus; if consensus fails, the current maintainers
  may decide by majority and record the dissent.
- Emergency security fixes may be merged by one maintainer and documented afterward.

## Model and dataset releases

A release requires the gates in `.opencode/skills/release-readiness/SKILL.md`, a model card, a
dataset card, and maintainer approval. A release candidate must beat the base model on the primary
metric without an unacceptable category regression.

## Points

The points policy is in `docs/points-policy.md`. Points:

- are non-contractual and may be changed or expired;
- are non-transferable;
- have no cash value;
- do not represent equity, revenue share, or employment;
- are granted only for verified work and are subject to admin review.

The ledger must remain balanced and auditable. Disputes are reviewed by maintainers, and the
recorded ledger entries are the source of truth.

## Changes to this document

Open a pull request with the proposed change and rationale. Do not merge without maintainer review.
Material changes should be announced in the repository before they take effect.
