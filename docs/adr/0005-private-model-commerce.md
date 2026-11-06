# ADR-0005: Private Models and Paid Access

Status: Proposed — direction accepted, implementation not started
Date: 2026-11-06

## Context

Contributors may want to tune models for a specific task, keep the recipe and weights private, and
earn money from them. The MVP explicitly excludes payments and paid inference. Community Points are
non-monetary and must stay that way. The public recipes repository is open by design.

Private data and private weights have a different trust boundary from public recipes. Anonymous
community workers cannot be trusted with private data, and private artifacts cannot be committed to
the public recipes repository.

## Decision

Treat private model commerce as a separate post-MVP track:

1. Private models are optional and separate from the public community model and open recipes.
2. The platform may host private models, license weights, or support paid private tuning. The first
   product shape is an open decision; a hosted private endpoint for entitled customers is the
   recommended first step.
3. Private recipes and weights use the same schema and manifest contract but live in tenant-scoped,
   encrypted storage. They are never committed to the public recipes repository.
4. Private data training runs on trusted or dedicated workers, not anonymous community workers.
5. Paid private work uses dedicated or paid capacity, not point-subsidized community compute.
6. Billing and payouts are fiat and use a ledger separate from Community Points. No conversion
   between points and fiat is permitted.
7. A private-model gate covers data rights, license compliance, safety/AUP, task quality, and a
   model card. It does not use the public benchmark threshold.
8. Derivatives of the public community model keep their public license, attribution, and model-card
   obligations.
9. Legal, payment, tax, KYC/AML, and security review complete before any money is accepted.

## Consequences

- The platform eventually needs multi-tenant isolation, entitlements, metering, fiat billing,
  payouts, support, and trust-and-safety operations.
- Private models may require dedicated inference capacity and cannot rely on best-effort community
  GPUs.
- Contributor ownership, revenue share, disputes, model retirement, and customer terms must be
  published before launch.
- The public model and its recipes remain open; private derivatives do not remove public lineage or
  community improvements.
- The commercial track may fund the commons, but revenue is not a claim on Community Points and
  points are not a claim on revenue.

## Rejected alternatives

### Make points redeemable for cash or private models

- Converts a beta recognition system into a financial instrument.
- Creates regulatory, tax, and consumer-protection obligations the project is not ready for.
- Contradicts the points policy and governance.

### Put private recipes in the public recipes repository

- Leaks private data, weights, and customer information.
- Breaks the open-by-default review model.
- Private manifests can be stored tenant-scoped with only hashes or attestations shared.

### Train private data on anonymous community workers

- A worker operator can read the data and the resulting adapter.
- Requires trusted or dedicated workers, or confidential computing.
- Consent and a data processing agreement are required even then.

### Launch a public marketplace immediately

- Needs discovery, ranking, reviews, disputes, refunds, and marketplace liability.
- A bring-your-own-customer hosted endpoint proves demand with less surface area.
- Marketplace discovery can come later if the commercial track works.

## Open questions

- Which product shape ships first: hosted endpoint, weight license, paid tuning, or dedicated
  capacity?
- Does the platform hold the customer contract, or does the contributor?
- What is the revenue share, and who bears refunds, chargebacks, and taxes?
- Are private models invitation-only or discoverable in a marketplace?
- Do private recipes live in customer-owned private git repositories or platform-managed storage?
- What quality and safety evidence is required before a private model can be sold?

## Implementation

See the post-MVP track in [`docs/roadmap/implementation.md`](../roadmap/implementation.md).
