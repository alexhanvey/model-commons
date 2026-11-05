---
description: Run the issue-tracker or hard tool-use evaluation
agent: build
---

Plan and run the evaluation requested here: $ARGUMENTS

Follow `.opencode/skills/ml-experiment/SKILL.md`.

Required:

1. State the model, adapter, dataset, harness, parser, and max sequence length.
2. Confirm the eval set has no train overlap.
3. Capture aggregate and category-level results, p50 latency, and failures.
4. Compare against the recorded base baseline.
5. Save raw results under `spikes/` or the appropriate results directory.
6. Destroy any rented GPU instance when finished.

Never treat a fine-tune as a release candidate unless it beats the base model on the primary metric
without an unacceptable category regression.
