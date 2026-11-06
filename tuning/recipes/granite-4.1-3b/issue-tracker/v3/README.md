# Granite Issue Tracker v3

Candidate recipe for the GitHub-style issue-tracker tool-calling task.

## Hypothesis

The v2 adapter reached 68.3% versus the base model's 70.0%. The remaining failures were
concentrated in confirmation and no-tool restraint. This candidate keeps the v2 data mix and
training budget, but is the first recipe represented in the repo-shaped tuning tree.

## Changes from v2

- No hyperparameter change yet; this is the reproducible baseline recipe.
- Base model revision is pinned.
- Dataset and eval checksums are locked.
- Evaluation is versioned separately from the recipe.

## Expected effect

Reproduce the v2 result within the documented tolerance. Any improvement must come from a later
recipe change with its own evaluation run.

## Cost

One 24GB GPU for a short QLoRA run (roughly 15–30 minutes including setup).
