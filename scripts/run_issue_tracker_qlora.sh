#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PHASE0="$ROOT/spikes/phase0"
TRACKER="$ROOT/spikes/issue_tracker"
RESULT="$TRACKER/results/granite-issue-tracker-v2-adapter-eval.json"
RUN_DIR="$PHASE0/runs/granite-issue-tracker"

echo "== Installing environment =="
cd "$PHASE0"
uv sync --extra vllm

echo "== Measuring token lengths =="
cd "$TRACKER"
mkdir -p results
uv run --project "$PHASE0" python - <<'PY' | tee results/token_lengths.txt
import json
import statistics
from transformers import AutoTokenizer

path = "data/issue_tracker_train_v2.jsonl"
tok = AutoTokenizer.from_pretrained("ibm-granite/granite-4.1-3b")
lengths = []
for line in open(path):
    row = json.loads(line)
    text = tok.apply_chat_template(
        row["messages"],
        tools=row["tools"],
        tokenize=False,
        add_generation_prompt=False,
    )
    lengths.append(len(tok(text)["input_ids"]))
print("count", len(lengths))
print("min", min(lengths))
print("p50", statistics.median(lengths))
print("p95", sorted(lengths)[int(len(lengths) * 0.95)])
print("max", max(lengths))
print("over_2048", sum(1 for value in lengths if value > 2048))
print("over_4096", sum(1 for value in lengths if value > 4096))
PY

echo "== Training QLoRA =="
cd "$PHASE0"
uv run python train_qlora_smoke.py \
  --model ibm-granite/granite-4.1-3b \
  --data "$TRACKER/data/issue_tracker_train_v2.jsonl" \
  --output-dir "$RUN_DIR" \
  --max-steps 50 \
  --max-seq-length 4096 \
  --validation-fraction 0.05 \
  --learning-rate 0.00001

echo "== Starting vLLM with adapter =="
source .venv/bin/activate
tmux kill-session -t vllm 2>/dev/null || true
tmux new-session -d -s vllm \
  "cd '$PHASE0' && source .venv/bin/activate && vllm serve ibm-granite/granite-4.1-3b --host 127.0.0.1 --port 8000 --max-model-len 4096 --gpu-memory-utilization 0.85 --enable-auto-tool-choice --tool-call-parser granite4 --enable-lora --max-lora-rank 16 --lora-modules issue-tracker='$RUN_DIR' > /workspace/vllm.log 2>&1"

for _ in $(seq 1 300); do
  if curl -sf --max-time 2 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

if ! curl -sf --max-time 3 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo "vLLM did not become ready"
  tail -80 /workspace/vllm.log || true
  tmux kill-session -t vllm 2>/dev/null || true
  exit 1
fi

echo "== Evaluating adapter =="
cd "$TRACKER"
uv run --project "$PHASE0" python eval_harness.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model issue-tracker \
  --data eval_cases.jsonl \
  --output "$RESULT" \
  --max-steps 8 \
  --max-tokens 1024

tmux kill-session -t vllm 2>/dev/null || true

echo "== Done =="
echo "Result: $RESULT"
echo "Metrics: $RUN_DIR/metrics.json"
