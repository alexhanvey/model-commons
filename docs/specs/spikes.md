# Phase 0 Technical Spikes

Status: GPU spikes completed — base model selected; fine-tuning not validated
Goal: de-risk the model, data, training, serving, sandbox, and artifact assumptions before building the platform.

Spike scripts live in `spikes/phase0/`.

## Environment

Local development is macOS. The spikes require a remote Linux + NVIDIA GPU host.

Candidate hosts:

- RunPod
- Lambda
- Vast.ai
- A trusted community GPU host

Minimum:

- 1x 24GB NVIDIA GPU for QLoRA smoke.
- 48GB preferred for serving.
- CUDA 12.x.
- Docker with NVIDIA runtime.
- 100GB disk.

Candidate models:

- `Qwen/Qwen3-1.7B` — Apache 2.0
- `ibm-granite/granite-4.1-3b` — Apache 2.0
- `HuggingFaceTB/SmolLM3-3B` — Apache 2.0, backup

Candidate dataset:

- `Team-ACE/ToolACE` — Apache 2.0; needs conversion to the project chat schema.
- `glaiveai/glaive-function-calling-v2` — Apache 2.0; older/simpler fallback.
- `Salesforce/xlam-function-calling-60k` — CC-BY-4.0, gated; verify terms before use.

## Spike 1 — Base model load and inference

- Load three candidate 1B–3B models.
- Verify tokenizer and chat template.
- Run a tool-calling prompt.
- Measure load time, VRAM, tokens/sec, and quality.
- Record license and revision.

Pass:

- At least one model fits 24GB and produces usable tool calls.
- License allows fine-tuning and release.

## Spike 2 — QLoRA fine-tune

- Use a small public tool-use dataset.
- Run 50–200 steps.
- Measure VRAM, time, loss, and cost.
- Save adapter.
- Load adapter and run inference.

Pass:

- Training completes without OOM.
- Adapter loads.
- Output is not obviously broken.
- Cost and time are acceptable.

## Spike 3 — vLLM serving

- Serve the base model or adapter.
- Run non-streaming and streaming requests.
- Measure time to first token, tokens/sec, p50/p95 latency.
- Test concurrency 1, 4, and 8.

Pass:

- Streaming works.
- Latency is acceptable for an agent/tool workflow.
- One 48GB GPU can serve the model at a useful rate.

## Spike 4 — Evaluation harness

- Run `lm-evaluation-harness` on the base model.
- Run a custom tool-calling eval.
- Save raw results and summary.
- Compare base vs fine-tune.

Pass:

- One command produces reproducible results.
- Results are comparable.
- Tool-calling metric is meaningful.

## Spike 5 — Worker sandbox

- Run a container as non-root.
- Disable network.
- Mount read-only inputs.
- Mount writable outputs.
- Verify no Docker socket and no host home access.
- Run a small GPU job.

Pass:

- Sandbox blocks network and host access.
- GPU access works.
- Output upload works.

## Spike 6 — Artifact storage

- Upload a small adapter and log file to S3/R2.
- Verify SHA-256.
- Download and load.
- Test presigned URL expiry.

Pass:

- Checksums match.
- Download works.
- Expired URLs fail.

## Results — 2026-11-03

Host: Vast.ai, NVIDIA RTX 5880 Ada Generation, 48GB VRAM, driver 580.159.03, CUDA 13.0.

### Smoke results

| Spike | Result | Notes |
|---|---|---|
| Qwen3-1.7B base tool call | Pass | Correct tool call and arguments; p50 666ms on easy 10-case set |
| Qwen3-1.7B QLoRA smoke | Pass | 10 steps, 14.8s, loss 5.77 → 1.69; adapter saved |
| Qwen3-1.7B adapter serve | Pass | vLLM LoRA serving works with `qwen3_json` parser |
| Granite 4.1 3B base | Pass | 48GB fit; p50 277.5ms on hard 40-case set |
| ToolACE conversion | Pass | 791 usable examples from first 1,000 rows |
| Balanced mix build | Pass | 1,067 examples: 791 ToolACE + 118 no-tool + 79 clarify + 79 multi-tool |

### Hard evaluation — 40 cases

| Model | Valid rate | p50 latency | Notes |
|---|---:|---:|---|
| Qwen3-1.7B base | 97.5% (39/40) | 735ms | Only failure was a no-tool case; thinking output consumes tokens |
| Qwen3-1.7B + ToolACE-only adapter | 65% (26/40) | 193ms | Overfit to always call a tool; lost clarification and multi-tool behavior |
| Qwen3-1.7B + balanced mix adapter | 85% (34/40) | 193ms | Improved no-tool restraint, still worse than base on clarify/multi-tool |
| Granite 4.1 3B base | 100% (40/40) | 277ms | Best overall; Apache 2.0; no thinking trace |
| Granite 4.1 3B + balanced mix adapter | 85% (34/40) | 311ms | Multi-tool and injection stayed strong; no-tool collapsed to 0/5 |

### Key findings

- The generic tool-calling eval is saturated for Granite 4.1 3B.
- Fine-tuning on generic ToolACE data degraded base-model restraint and multi-tool behavior.
- The current adapters are not release candidates.
- Granite 4.1 3B base is the best MVP base model: Apache 2.0, 48GB fit, 100% hard eval, fastest p50.
- Qwen3-1.7B is viable but slower and slightly weaker on the hard set.
- To demonstrate fine-tuning value, the next dataset/eval should target a narrower, harder domain where the base model is not already strong.

### Decision

- [x] Model chosen: `ibm-granite/granite-4.1-3b` base for the MVP.
- [x] Dataset source chosen: ToolACE (Apache 2.0) for generic experiments, plus custom issue-tracker data for the narrow target.
- [x] Training method chosen: QLoRA, single GPU.
- [x] Serving target chosen: vLLM on 48GB NVIDIA GPU.
- [x] GPU target chosen: 24–48GB NVIDIA; 48GB preferred.
- [ ] Sandbox approach validated — pending Phase 3.
- [ ] Artifact storage validated — pending Phase 3.
- [x] Proceed to Phase 1 — scaffold started while non-code Phase 0 gates remain open.

## Issue-tracker follow-up — 2026-11-04

The narrow target is GitHub-style issue-tracker tool calling with a deterministic mock API and a
60-case state-based eval. Base Granite 4.1 3B scored **70.0% (42/60)**. Two QLoRA adapters were
trained on 800 examples:

| Model | Passed | Rate | p50 |
|---|---:|---:|---:|
| Granite 4.1 3B base | 42/60 | **70.0%** | 1,075ms |
| Adapter v1 | 32/60 | 53.3% | 7,110ms |
| Adapter v2 | 41/60 | 68.3% | 1,289ms |

Neither adapter beat base. Confirmation behavior remained broken in both. The base model is the MVP
model; the adapters are research artifacts. See `spikes/issue_tracker/results/README.md`.
