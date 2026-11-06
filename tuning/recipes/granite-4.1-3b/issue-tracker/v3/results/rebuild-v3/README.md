# Rebuild: v3

Rebuild of the v3 recipe from `manifest.lock` on a Vast RTX 4090 24GB on 2026-11-06. The rebuild
tests that the recorded recipe, base revision, dataset, and eval set reproduce the original result.

## Result

The rebuild passed the documented reproducibility tolerance. The adapter scored **40/60 (66.7%)**
versus the original **41/60 (68.3%)**, a one-case difference, and still did not beat the base
model's **42/60 (70.0%)**. It is not a release candidate.

| Run | Train loss | Eval loss | Adapter | Base | p50 | Adapter SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| Original v3 | 0.753665 | 0.732349 | 41/60 (68.3%) | 42/60 (70.0%) | 1,390ms | `64290c5d…6373a` |
| Rebuild | 0.753900 | 0.732557 | 40/60 (66.7%) | 42/60 (70.0%) | 1,370ms | `89d12722…f3ae7` |

The base result is the recorded baseline from `results/v3/eval-base.json`; the rebuild reran the
adapter only. Adapter bytes differ, as expected across runs. The full SHA-256 values are in
`run.json`. Category results:

| Category | Original | Rebuild |
|---|---:|---:|
| clarify | 8/10 | 8/10 |
| confirmation | 0/5 | 0/5 |
| multi_tool | 10/15 | 9/15 |
| nested_search | 4/5 | 4/5 |
| no_tool | 2/5 | 2/5 |
| prompt_injection | 5/5 | 5/5 |
| single_tool | 12/15 | 12/15 |

Only `multi_tool` changed, by one case. The release decision is unchanged.

## Environment

- Base: `ibm-granite/granite-4.1-3b` at `c0650403e44e78ec0262dab1c90914c65b196c4e`.
- Dataset SHA-256: `94958b7d…8d7034ff`.
- Eval SHA-256: `2fc3fd32…4955d4d0`.
- Manifest SHA-256: `a5b9e9f1…bc366077`.
- GPU: NVIDIA GeForce RTX 4090 24GB.
- Python 3.12.3, torch 2.15.0+cu132, transformers 5.22.1, vLLM 0.33.0.
- Runner image: `local-dev` (pin a real digest before a release).

## Commands

Training:

```sh
community-llm-train \
  --recipe tuning/recipes/granite-4.1-3b/issue-tracker/v3/recipe.yaml \
  --output-dir runs/rebuild-v3
```

Evaluation:

```sh
vllm serve ibm-granite/granite-4.1-3b \
  --revision c0650403e44e78ec0262dab1c90914c65b196c4e \
  --port 8000 --max-model-len 4096 --gpu-memory-utilization 0.85 \
  --enable-auto-tool-choice --tool-call-parser granite4 \
  --enable-lora --max-lora-rank 16 \
  --lora-modules issue-tracker=/workspace/community-llm/runs/rebuild-v3/adapter

python eval_harness.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model issue-tracker \
  --output results/rebuild-adapter-v3.json
```

The recorded run omitted `--revision`; the server resolved `main`, which pointed at the pinned commit
during that run. The command above is the strict-pinning form to use when rerunning.

## Evidence

- `metrics.json` — training metrics from the rebuilt run.
- `eval-adapter-v3.json` — 60-case adapter eval output.
- `run.json` — checksums, comparison, and reproducibility verdict.
