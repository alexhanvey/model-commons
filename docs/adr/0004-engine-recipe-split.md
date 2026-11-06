# ADR-0004: Separate Tuning Recipes from the Platform

Status: Accepted
Date: 2026-11-06

## Context

The MVP lets contributors run verified evaluation and LoRA jobs. Community ownership requires more
than running platform-defined work: contributors must be able to change what the model is tuned on
and how, review each other's changes, and cite a reproducible recipe for every released model.

Today `ml/` holds the runner and two smoke configs, while the real Phase 0 recipes and results live
in `spikes/`. That mixes research artifacts with platform code and ties tuning changes to platform
releases. It also forces anyone who wants to propose a hyperparameter change to clone and bootstrap
the full stack.

A recipe names a base model, a dataset, hyperparameters, and an eval set. If the platform executes
it, a recipe is executable input. The platform needs a narrow, reviewed, pinned contract rather
than arbitrary configuration.

## Decision

Split along **engine vs recipes**, not "platform vs ML code".

- The engine repository (`model-commons`) keeps the control plane, worker, inference proxy, web,
  protocol/SDK, the `community-llm-ml` runner, container images, the recipe schema, and the model
  registry.
- The recipes repository (`model-commons/recipes`) holds recipes, eval definitions, manifests,
  results, model cards, serving profiles, and license records.
- Datasets, adapters, and built models stay in object storage by checksum. They are not committed
  to either repository.

The transition and contract:

- Phase 4 creates a repo-shaped `tuning/` tree in the monorepo. Extraction is a directory move plus
  a version pin, not a redesign.
- Every recipe has a `schema_version` and passes a closed schema. Unknown keys, arbitrary model
  sources, and remote code are rejected.
- Every recipe has a `manifest.lock` covering the base model revision, dataset and eval checksums,
  runner version, image digest, and license identifiers.
- Every job records a pinned `recipe_ref`: repository, commit, path, and manifest SHA256. Mutable
  refs such as `main` are rejected.
- Merging a recipe makes it a candidate. Only the release gate can make it the served model.
- Eval sets are versioned, immutable once used for a release, and owned separately from recipes. A
  pull request may not change a recipe and its eval set together.
- Extraction happens when any trigger fires: more than two actively maintained recipes, the first
  external recipe contributor, the first release candidate, or a governance or licensing need for
  independent recipe history.
- Phase 9 requires the release recipe, eval version, and manifest to live in the standalone
  recipes repository at an immutable tag.

## Consequences

- Contributors get a small repository and a lightweight validation path instead of the full
  platform stack.
- Tuning history becomes independently citable and can follow its own review and release cadence.
- License and dataset provenance stay attached to the recipe that used them.
- The platform executes a smaller, reviewed, pinned input surface.
- Eventually there are two repositories, two issue trackers, and cross-repo version pinning.
- The runner must be published as a versioned package and container image before extraction.
- Release coordination must link the recipe tag, manifest hash, built artifact, and model card.
- The extraction triggers keep the two-repository cost from being paid before it is useful.

## Rejected alternatives

### Keep everything in one repository forever

- Viable for the MVP, but platform CI and review rules dominate tuning changes.
- Tuning history stays tied to platform release cadence.
- External contributors must clone and bootstrap the full stack to change a hyperparameter.
- Does not meet the community-governance requirement for a public model release.

### Split the ML runner code into its own repository

- Creates schema drift between the job protocol and the recipe schema.
- Forces cross-repo releases for every worker or runner change.
- The runner is engine code and benefits from monorepo tests.
- Publishing the package and image already gives standalone use without the split.

### Split datasets into a third repository

- Datasets are large and versioned; git is the wrong store.
- Object storage plus SHA256 already provides immutability and provenance.
- More repositories multiply coordination without adding a contribution surface.

### Let recipes reference mutable branches

- Breaks reproducibility and release audit.
- Allows a merged pull request to change a future run silently.
- Rejected in favor of a commit plus manifest hash.

## Implementation

See Phase 4 scope and acceptance in [`docs/roadmap/implementation.md`](../roadmap/implementation.md).
