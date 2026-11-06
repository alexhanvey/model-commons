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

Trained and evaluated on a Vast RTX 4090 24GB with the pinned recipe. Adapter checksum:
`64290c5dce51d5b0de507bbb852dd3c8db2f6286f01bde6646cfa0eaf2b6373a`.

| Model | Passed | Rate | p50 |
|---|---:|---:|---:|
| Granite 4.1 3B base | 42/60 | **70.0%** | 1,002ms |
| Issue tracker v3 adapter | 41/60 | 68.3% | 1,390ms |

The adapter matched v2 at 68.3% and did not beat the base model. It is **not a release
candidate**.

Category notes:

- single_tool: 12/15 (80%) vs base 15/15.
- no_tool: 2/5 (40%) vs base 1/5.
- multi_tool: 10/15 (67%) vs base 9/15.
- confirmation: 0/5 vs base 0/5.
- prompt_injection: 5/5.

Raw run records are in `results/v3/`: `metrics.json`, `run.json`, `summary.json`, `train-output.txt`, and
the base/adapter eval outputs.

## Limitations

- Synthetic data; not a substitute for real issue-tracker traffic.
- Narrow tool-calling task only.
- Not evaluated for general chat, safety-critical use, or frontier-model capability.
