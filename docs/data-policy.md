# Data Policy

Status: Draft — Phase 0

## Principles

- Public or permissively licensed data only in the MVP.
- No user prompts or completions used for training without explicit consent.
- No PII in released datasets.
- Provenance and license recorded for every dataset.
- Test sets are never used for training.
- Data is versioned and checksummed.
- Tuning recipes record dataset and eval checksums plus license identifiers.

## Allowed sources

- Public datasets with clear licenses.
- Community-contributed data with a signed contribution agreement.
- Synthetic data generated with licensed tools and documented provenance.
- Partner data with a written agreement.

## Disallowed sources

- Scraped copyrighted content without permission.
- Leaked data.
- Personal data without consent.
- Data from private user prompts.
- Data with unclear provenance.
- Test sets from the evaluation suite.

## Processing

- Normalize to the project chat schema.
- Exact dedup.
- Near dedup.
- PII regex scrub.
- Manual review for flagged PII.
- Contamination check against eval sets.
- Train/validation/test split.
- SHA-256 checksum.
- Dataset card.

## Recipes and manifests

- A tuning recipe references data by URI and SHA256, never by a mutable path or branch.
- Every recipe has a manifest lock covering the base model revision, dataset and eval checksums,
  runner version, image digest, and license identifiers.
- Datasets are not committed to git. Small eval fixtures may be, with a version and checksum.
- A recipe that cannot be rebuilt from its manifest is not eligible for release.
- Changing a dataset creates a new checksum and a new dataset card.

## Dataset card

Every dataset must document:

- source;
- license;
- collection method;
- processing steps;
- dedup and PII handling;
- contamination checks;
- split sizes and token counts;
- known limitations;
- intended use;
- non-intended use;
- contact.

## Retention

- Training data retained while the model version is supported.
- Deleted on request where legally required.
- Released datasets are immutable.
- New versions get new checksums and cards.

## User data

- Prompts and completions are not logged by default.
- No training on user data without opt-in.
- Enterprise/private data is never used for community training.

## Private data

- Private data is never used for public datasets, public training, or the public model without
  explicit, documented consent.
- Private tuning runs on trusted or dedicated workers, not anonymous community workers.
- Private data requires a data processing agreement, retention period, deletion process, and access
  audit.
- Private training data must have commercial-use rights if the resulting model is sold.
- Private recipes, manifests, and weights are tenant-scoped and are not committed to the public
  recipes repository.
- A private model still records data provenance, license, and checksums in its manifest.

## Review

Data policy is a release gate. Legal review is required before any public dataset release.
