# Issue Tracker Tool-Use Spike

Narrow Phase 0 target:

> A community fine-tuned Granite 4.1 3B model for GitHub-style issue-tracker tool calling.

This is a deterministic mock API. It does not connect to real GitHub, Jira, or Linear.

## Contents

- `fixtures.json` — projects, users, issues, labels.
- `schemas.py` — 14 tool schemas.
- `mock_api.py` — deterministic tracker with policy checks.
- `eval_cases.jsonl` — 60 scenarios.
- `eval_harness.py` — multi-step state-based evaluation.
- `build_eval_cases.py` — regenerates the 60 cases.
- `build_training_data.py` — generates 800 validated training examples.
- `data/issue_tracker_train_v2.jsonl` — current training set.
- `tests/` — mock API, eval consistency, and training-data tests.

## Why this target

Generic tool calling is saturated for Granite 4.1 3B. This domain adds:

- multi-step workflows;
- issue and user ID grounding;
- nested search filters;
- confirmation before close/reopen;
- closed-issue policy;
- prompt injection inside issue text;
- no-tool and clarification behavior.

## Run tests locally

```sh
cd spikes/issue_tracker
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 build_eval_cases.py
```

## Baseline on a GPU host

Use the Phase 0 environment:

```sh
cd /workspace/community-llm/spikes/phase0
uv sync
uv pip install vllm

MODEL=ibm-granite/granite-4.1-3b \
TOOL_PARSER=granite4 \
PORT=8000 \
./serve_model.sh
```

In another shell:

```sh
cd /workspace/community-llm/spikes/issue_tracker
uv run --project ../phase0 python eval_harness.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model ibm-granite/granite-4.1-3b \
  --data eval_cases.jsonl \
  --output results/granite-base-eval.json \
  --max-steps 8 \
  --max-tokens 1024
```

## Headroom gate

- **50–80%:** proceed to training data.
- **Above 90%:** narrow further.
- **Below 40%:** simplify the tool surface.

Baseline: **70% (42/60)**, so the headroom gate passed.

## Training data

Generated 800 examples with no exact eval overlap:

```sh
python3 build_training_data.py --output data/issue_tracker_train_v2.jsonl
```

## QLoRA next step

Once a GPU is available:

```sh
cd /workspace/community-llm/spikes/phase0
uv run python train_qlora_smoke.py   --model ibm-granite/granite-4.1-3b   --data ../issue_tracker/data/issue_tracker_train_v2.jsonl   --output-dir runs/granite-issue-tracker   --max-steps 50   --max-seq-length 4096   --validation-fraction 0.05   --learning-rate 0.00001
```

If 4096 OOMs on 24GB, drop to 2048 and note the truncation rate.

## Policy assumptions

- Current user is `u_alex`.
- Current user can access Atlas and Beacon, not Cinder.
- Assignees must be project members.
- Closed issues must be reopened before editing.
- Close/reopen require explicit confirmation.
- No delete tool.
- No shell, network, or real repository access.
