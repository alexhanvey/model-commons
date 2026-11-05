#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-1.7B}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
TOOL_PARSER="${TOOL_PARSER:-}"
DTYPE="${DTYPE:-auto}"

args=(
  --model "$MODEL"
  --port "$PORT"
  --max-model-len "$MAX_MODEL_LEN"
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --dtype "$DTYPE"
)

if [[ -n "$TOOL_PARSER" ]]; then
  args+=(--enable-auto-tool-choice --tool-call-parser "$TOOL_PARSER")
fi

echo "Starting vLLM for $MODEL on port $PORT"
exec vllm serve "${args[@]}"
