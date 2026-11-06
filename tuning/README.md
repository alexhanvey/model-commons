# Tuning Recipes

This directory holds the community tuning recipes, eval definitions, manifests, results, and model
cards. It is repo-shaped so it can move to the standalone `model-commons/recipes` repository without
a redesign.

## Layout

```text
tuning/
  schema/recipe.schema.json
  recipes/<base-model>/<capability>/<version>/
    recipe.yaml
    manifest.lock
    README.md
    results/
    model-card.md
  evals/<capability>/<version>/
    cases.jsonl
    rubric.md
    version.lock
```

## Rules

- Recipes are declarative. They do not execute arbitrary code.
- Every recipe pins the base model commit, dataset SHA-256, and eval SHA-256 in `manifest.lock`.
- Eval sets are versioned and immutable once used for a release.
- Eval and recipe changes must not share a pull request.
- Merging a recipe makes it a candidate. Only the release gate can make it a released model.
- Datasets, adapters, and built models live in object storage by checksum, not in git.
- Private recipes are tenant-scoped and never enter this public tree.

## Validation

```sh
just validate-tuning
```

This checks the recipe schema, immutable base revision, manifest hashes, local dataset/eval
checksums, and eval contamination.

## Distribution and model tiers

Long-term, releases are downloadable from Hugging Face with quantized artifacts for local and
mobile runtimes. There is no hosted inference in the MVP.

- Mobile tier: 0.5–1.5B parameters at 4-bit.
- Laptop/server tier: 1–3B parameters at 4-bit.
- Recipes can target different base models; add a new `<base-model>/<capability>/<version>/` track.
- Release artifacts and checksums are recorded outside git; see
  [`docs/runbooks/model-release.md`](../docs/runbooks/model-release.md).

## Reproducibility

A rebuild must use the recipe, manifest lock, and pinned base revision. Record the new run's
metrics, adapter SHA-256, GPU, package versions, and eval output next to the original result.

Adapter bytes may differ across GPUs and library versions. The documented tolerance is:

- the rebuilt eval pass count is within one case of the recorded result on the same eval version;
- the release decision is unchanged;
- any larger difference is an unverified result, not a reproduction.

## Extraction trigger

Extract this tree to the standalone recipes repository when any of these is true:

- more than two actively maintained recipes;
- the first external recipe contributor;
- the first release candidate;
- a governance or licensing need for independent recipe history.

Phase 9 requires the release recipe to live in the standalone repository at an immutable tag.
