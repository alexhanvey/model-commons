# Phase 0 Status

Date: 2026-11-04
Status: GPU spikes complete; base model selected; fine-tuning not validated

## Locked

- Target user: solo developers and small teams building local/agentic applications.
- First capability: tool use / function calling.
- Base model: `ibm-granite/granite-4.1-3b` (Apache 2.0).
- Dataset source: `Team-ACE/ToolACE` (Apache 2.0), converted.
- Training method: QLoRA, single GPU.
- Serving: vLLM on a 48GB NVIDIA GPU.
- GPU target: 24–48GB NVIDIA; 48GB preferred.
- Points: non-contractual, non-transferable, no cash value.
- Stack: FastAPI + Next.js + Postgres + Redis + S3-compatible storage.

## Completed

- Initialized the repo and Phase 0 documents.
- Ran Qwen3-1.7B and Granite 4.1 3B on a 48GB Vast.ai GPU.
- Ran QLoRA smoke tests.
- Converted ToolACE to the project chat schema.
- Built a balanced training mix with no-tool, clarify, and multi-tool examples.
- Built and ran a 40-case hard tool-calling eval.
- Added unit tests for eval scoring.
- Selected Granite 4.1 3B as the base model.

## Results

| Model | Hard eval | p50 | Decision |
|---|---:|---:|---|
| Granite 4.1 3B base | 100% (40/40) | 277ms | Selected |
| Qwen3-1.7B base | 97.5% (39/40) | 735ms | Rejected for MVP |
| Qwen3-1.7B + ToolACE adapter | 65% (26/40) | 193ms | Not release candidate |
| Qwen3-1.7B + mix adapter | 85% (34/40) | 193ms | Not better than base |
| Granite 4.1 3B + mix adapter | 85% (34/40) | 311ms | No-tool collapse; not release candidate |

## Key findings

The generic tool-calling eval is saturated for Granite 4.1 3B. Fine-tuning on generic ToolACE data degraded restraint and multi-tool behavior. The current adapters are not release candidates.

The issue-tracker headroom eval scores **70%** zero-shot. This is in the target 50–80% range: enough headroom to justify a domain fine-tune, but not so weak that the task is hopeless.

The MVP can use Granite 4.1 3B base. To demonstrate community fine-tuning value, the next target must be a narrower, harder domain where the base model has headroom.

## Remaining Phase 0 work

- [x] Choose the narrower fine-tune target: GitHub-style issue-tracker tool calling.
- [x] Build the 60-case issue-tracker eval and mock API.
- [x] Run Granite 4.1 3B baseline on the 60-case issue-tracker eval: 70% (42/60).
- [x] Generate 800 issue-tracker training examples (no eval overlap, validated).
- [x] Run QLoRA and compare base vs adapter on the 60-case eval.
- [x] Measure token lengths: p50 1904, p95 2385, max 2639; 4096 is safe.
- [x] Conservative v2 adapter: 68.3% vs 70% base. Still not better. Keep base; fine-tuning approach not validated.
- [x] Build a domain-specific held-out set where base has headroom.
- [x] Collect or curate training data for that target.
- [x] Run a conservative QLoRA experiment with the new data.
- [ ] Verify no generic regression on the new adapters.
- [ ] Complete 10 contributor and 10 user interviews, or reduce the target.
- [ ] Decide open-weight release terms.
- [ ] Complete legal checklist.
- [x] Proceed to Phase 1 (scaffold started; Phase 0 interviews and legal review remain open).

## Notes

- Local development is macOS without an NVIDIA GPU.
- `/workspace` on the Vast.ai instance is not persistent. Sync results before destroying the instance.
- The vLLM server is currently stopped after the Granite adapter evaluation.
