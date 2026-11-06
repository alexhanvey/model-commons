# Model Card: Granite Issue Tracker v3

Status: candidate, not a release.

## Base model

`ibm-granite/granite-4.1-3b` at a pinned commit.

## Training data

The synthetic issue-tracker SFT set in `spikes/issue_tracker/data/issue_tracker_train_v2.jsonl`.
The dataset manifest records the SHA-256 and license.

## Evaluation

Issue-tracker eval `issue-tracker@2026-11`, 60 cases. See `tuning/evals/issue-tracker/2026-11/`.

## Results

Results will be attached after the training run. A candidate is not a release candidate until it
beats the base model on the primary metric without an unacceptable category regression.

## Limitations

- Synthetic data; not a substitute for real issue-tracker traffic.
- Narrow tool-calling task only.
- Not evaluated for general chat, safety-critical use, or frontier-model capability.
