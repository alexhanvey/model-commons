# ML Pipeline and Model Registry

Status: Phase 4

This runbook covers dataset preparation, tuning validation, QLoRA, evaluation, and model-version
release gates.

## Prepare a dataset

```sh
uv run community-llm-prepare-data \
  --input spikes/issue_tracker/data/issue_tracker_train_v2.jsonl \
  --output-dir .sandbox/datasets/issue-tracker-v2 \
  --name issue-tracker \
  --version 2 \
  --source "synthetic issue-tracker data" \
  --license Apache-2.0 \
  --eval-cases tuning/evals/issue-tracker/2026-11/cases.jsonl
```

This writes `train.jsonl`, `validation.jsonl`, `test.jsonl`, `manifest.json`, and
`dataset-card.md`. It fails on eval contamination by default.

## Validate recipes

```sh
just validate-tuning
```

This checks the closed schema, pinned base revision, manifest hashes, local dataset/eval checksums,
eval contamination, and schema freshness. Regenerate the JSON Schema with:

```sh
uv run python scripts/validate_tuning.py --write-schema
```

## Tiny CPU smoke

Use an isolated environment so the API/worker dependencies stay intact:

```sh
uv venv .sandbox/ml-venv --python 3.12
uv pip install --python .sandbox/ml-venv/bin/python --torch-backend=cpu \
  torch datasets transformers peft accelerate pyyaml pydantic
uv pip install --python .sandbox/ml-venv/bin/python -e ml --no-deps

.sandbox/ml-venv/bin/python -m community_llm_ml.training.train_lora \
  --recipe tuning/recipes/granite-4.1-3b/issue-tracker/v3/recipe.yaml \
  --output-dir .sandbox/smoke-run \
  --smoke
```

## GPU QLoRA

The Vast runner loads `VAST_API_KEY` from `.env`, requires a registered SSH key, and excludes `.env`
and local caches from sync. It uses rsync when available and a tar-over-SSH fallback otherwise.

```sh
uv run python scripts/vast_ephemeral.py run \
  --gpu-name "RTX 4090" --min-vram 24000 --disk 48 --max-hourly 2.00 \
  --geolocation US CA --sync . --remote-dir /workspace/community-llm \
  --remote-command 'curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH" && uv sync --package community-llm-ml --extra train --no-dev && mkdir -p runs/vast-lora-v3 && timeout 2400 .venv/bin/community-llm-train --recipe tuning/recipes/granite-4.1-3b/issue-tracker/v3/recipe.yaml --output-dir runs/vast-lora-v3 > runs/vast-lora-v3/train.log 2>&1; status=$?; cat runs/vast-lora-v3/train.log; exit $status' \
  --download /workspace/community-llm/runs/vast-lora-v3 .sandbox/ \
  --keep-on-failure
```

The adapter and `metrics.json` are written under `runs/vast-lora-v3`. Adapters are not committed;
store them in object storage by checksum.

## Evaluate base and adapter

Install vLLM in the spike environment:

```sh
uv sync --project spikes/phase0 --extra vllm
```

Serve the base model:

```sh
cd spikes/issue_tracker
../phase0/.venv/bin/vllm serve ibm-granite/granite-4.1-3b \
  --port 8000 --max-model-len 4096 --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice --tool-call-parser granite4
```

Run the eval in another shell:

```sh
../phase0/.venv/bin/python eval_harness.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model ibm-granite/granite-4.1-3b \
  --output results/base.json
```

Serve the adapter with LoRA enabled, then evaluate `issue-tracker`:

```sh
../phase0/.venv/bin/vllm serve ibm-granite/granite-4.1-3b \
  --port 8000 --max-model-len 4096 --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice --tool-call-parser granite4 \
  --enable-lora --max-lora-rank 16 \
  --lora-modules issue-tracker=/workspace/community-llm/runs/vast-lora-v3/adapter

../phase0/.venv/bin/python eval_harness.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model issue-tracker \
  --output results/adapter.json
```

The v3 recipe scored 68.3% versus the base model's 70.0%, so it is not a release candidate.

## Model registry

Create a candidate (admin session + CSRF):

```sh
curl -s -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"granite-issue-tracker",
    "version":"v3",
    "base_model":"ibm-granite/granite-4.1-3b",
    "base_revision":"<40-char-commit>",
    "recipe_ref":{
      "repository":"model-commons/recipes",
      "commit":"<40-char-commit>",
      "path":"recipes/granite-4.1-3b/issue-tracker/v3",
      "manifest_sha256":"<64-char-sha256>"
    },
    "adapter_uri":"s3://models/granite-issue-tracker-v3/adapter",
    "adapter_sha256":"<64-char-sha256>",
    "metrics":{
      "primary_metric":0.6833,
      "baseline_metric":0.70,
      "general_regression":0.0,
      "safety_pass":true,
      "sample_size":60
    },
    "model_card":"# Model Card\n\nCandidate."
  }' \
  http://localhost:3000/api/v1/admin/model-versions
```

Release or reject:

```sh
curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  http://localhost:3000/api/v1/admin/model-versions/<model-id>/release

curl -s -X POST -H "Cookie: $COOKIE" -H "X-CSRF-Token: $CSRF" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"did not beat baseline"}' \
  http://localhost:3000/api/v1/admin/model-versions/<model-id>/reject
```

The release gate requires:

- primary metric at least 5 percentage points above the baseline;
- general regression at most 2 percentage points;
- safety pass;
- a non-empty model card;
- adapter URI and SHA-256;
- immutable base and recipe refs.
