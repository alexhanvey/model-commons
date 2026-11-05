# Phase 0 Spikes

Run these on a remote Linux + NVIDIA GPU host. Do not expose vLLM publicly; use an SSH tunnel or private network.

## Target hardware

- 1x 24GB NVIDIA GPU minimum for QLoRA.
- 1x 40–48GB GPU preferred for serving.
- CUDA 12.x.
- 100GB free disk.

## Candidate models

- `Qwen/Qwen3-1.7B` — Apache 2.0
- `ibm-granite/granite-4.1-3b` — Apache 2.0
- `HuggingFaceTB/SmolLM3-3B` — Apache 2.0, backup

## Candidate dataset

- `Team-ACE/ToolACE` — Apache 2.0
- `Salesforce/xlam-function-calling-60k` — CC-BY-4.0, gated
- `glaiveai/glaive-function-calling-v2` — Apache 2.0, older/simpler

The smoke training script uses a small synthetic JSONL file so the pipeline can be tested independently of dataset conversion. Real training uses ToolACE after conversion to the project chat schema.

## Setup

```sh
cd spikes/phase0
uv sync
uv run python check_env.py
```

Install vLLM separately if it is not available in the environment:

```sh
uv pip install vllm
```

## Serve a model

```sh
MODEL=Qwen/Qwen3-1.7B PORT=8000 ./serve_model.sh
```

In a second terminal:

```sh
uv run python smoke_tool_call.py --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen3-1.7B
```

## QLoRA smoke test

```sh
uv run python train_qlora_smoke.py \
  --model Qwen/Qwen3-1.7B \
  --data data/tool_call_smoke.jsonl \
  --output-dir runs/qwen3-1.7b-lora \
  --max-steps 10
```

For Granite:

```sh
uv run python train_qlora_smoke.py \
  --model ibm-granite/granite-4.1-3b \
  --data data/tool_call_smoke.jsonl \
  --output-dir runs/granite-4.1-3b-lora \
  --max-steps 10
```

## Evaluate tool calling

With a served model:

```sh
uv run python eval_tool_call.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model Qwen/Qwen3-1.7B \
  --data data/heldout_tools.jsonl \
  --output runs/qwen3-1.7b-eval.json
```

## Record results

Copy the output into `docs/specs/spikes.md`:

- GPU and VRAM.
- Model and revision.
- Load time.
- QLoRA time and cost.
- Tokens/sec.
- p50/p95 latency.
- Valid tool-call rate.
- Failure notes.

## Safety

- Do not expose vLLM on a public port.
- Do not put Hugging Face tokens in the repo.
- Use a temporary GPU host.
- Delete the host after the spike if it contains sensitive data.
