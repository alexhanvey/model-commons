---
name: ML Experiment
description: Run reproducible tool-use training and evaluation experiments on rented GPUs
---

# ML Experiment

## Before renting a GPU

1. State the hypothesis and the metric that would falsify it.
2. Confirm the eval set has zero prompt overlap with training data.
3. Record the base model, revision, dataset checksum, harness, parser, and max sequence length.
4. Run the smallest useful smoke test first.
5. Set a hard cost and time budget.

## GPU lifecycle

Use `scripts/vast_ephemeral.py`. It auto-destroys the instance unless `--keep-on-failure` is set.

```sh
python3 scripts/vast_ephemeral.py search --gpu-name "RTX 4090" --min-vram 48000 --limit 5
python3 scripts/vast_ephemeral.py run \
  --gpu-name "RTX 4090" --min-vram 48000 --disk 48 --max-hourly 3.00 \
  --sync /Users/alex/community-llm \
  --remote-dir /workspace/community-llm \
  --remote-command "bash scripts/run_issue_tracker_qlora.sh" \
  --download /workspace/community-llm/spikes/issue_tracker/results/RESULT.json \
             /Users/alex/community-llm/spikes/issue_tracker/results/RESULT.json
```

- Never put `VAST_API_KEY` in a command, log, or commit. The runner loads `.env`.
- Download results before the instance is destroyed.
- Verify the instance is gone with `python3 scripts/vast_ephemeral.py list`.
- `--keep-on-failure` costs money; destroy the instance manually when done.

## Evaluation discipline

- Use the same harness, prompt template, tool schemas, and parser for base and adapter.
- Report aggregate and category-level pass rates.
- Report p50 latency and the number of invalid tool calls.
- Keep failures, not just the score.
- Treat differences within a few cases as noise.
- Never call an adapter a release candidate if it does not beat the baseline.

## Current evidence

- Base Granite 4.1 3B: 70.0% (42/60) on the issue-tracker eval, p50 1075ms.
- Adapter v1: 53.3% (32/60).
- Adapter v2: 68.3% (41/60).
- The base model remains the MVP model. See `spikes/issue_tracker/results/README.md`.

## Reporting

Save raw JSON, a short summary, and the exact command. Update `docs/roadmap/status.md` only with
verified results. Fine-tuning is not validated until a narrow behavior improves without a material
regression elsewhere.
