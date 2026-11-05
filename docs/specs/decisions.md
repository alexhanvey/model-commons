# Phase 0 Decision Log

Status: Proposed — decisions are not locked until reviewed and checked.

| Decision | Options considered | Proposed choice | Why | Owner | Status |
|---|---|---|---|---|---|
| Target user | Agent developers, researchers, local-app builders, small teams | Solo developers and small teams building local/agentic apps | Concrete workflow; API-compatible; likely to test early | Alex | Accepted |
| First capability | Instruction following, tool use, summarization, multilingual, domain Q&A | Tool use / function calling | Testable; useful to agents; narrow enough for a small model | Alex | Accepted |
| Base model | 1B–3B permissive instruct models | `ibm-granite/granite-4.1-3b` | Apache 2.0; 100% hard eval; 277ms p50; 48GB fit | Alex | Accepted |
| Dataset | Public tool-use data, curated synthetic data, community data | ToolACE (Apache 2.0) converted + synthetic restraint mix for experiments; custom held-out set for eval | License clarity; generic tool calling is saturated, so fine-tune target must be narrowed | Alex | Accepted for experiments |
| Evaluation | Public benchmark, custom held-out, human review | 40-case hard tool-calling set + custom schemas + safety | Measures restraint, multi-tool, nested args, injection, multi-turn | Alex | Accepted |
| GPU target | 24GB, 48GB, 80GB | 24GB for QLoRA smoke; 48GB preferred for serving; rent via RunPod/Lambda | Feasible for 1B–3B; local machine has no NVIDIA GPU | Alex | Accepted |
| Deployment | Fly/Vercel/Neon/Upstash/R2, AWS, self-hosted | Fly.io + Vercel + Neon + Upstash + R2; GPU on RunPod/Lambda | Managed services reduce MVP ops | Alex | Proposed |
| Local object storage | MinIO, RustFS, Garage, SeaweedFS | RustFS 1.0.4 | MinIO images removed in 2026; RustFS is S3-compatible and maintained | Alex | Accepted (ADR-0003) |
| Points | Non-contractual points, paid credits, token | Non-contractual, non-transferable, no cash value | Avoids financial/regulatory complexity | Alex | Proposed |
| Model release | Open weights, API-only, delayed open | Open weights after evaluation and license review | Aligns with community ownership | Alex | Proposed |
| License | Apache-2.0, MIT, OpenRAIL | Code Apache-2.0; model/data licenses depend on base/data | Need legal review | Alex | Open |

## Decision review checklist

Before marking a decision accepted:

- [ ] The choice is written as a single sentence.
- [ ] The alternatives and why they were rejected are recorded.
- [ ] The license implications are checked.
- [ ] The cost implication is understood.
- [ ] The decision is reversible or the reversal cost is documented.
- [ ] The decision is linked from `docs/specs/mvp.md` if it changes scope.

## Open questions

1. ~~Which base model has the best current license, tool-calling quality, and 24GB fine-tuning story?~~ Answered: `ibm-granite/granite-4.1-3b` (ADR-0002).
2. ~~Which public tool-use dataset is both useful and clearly licensed?~~ Answered for experiments: ToolACE converted plus a custom held-out set; see `docs/data-policy.md`.
3. ~~Do we have access to a 24GB or 48GB NVIDIA GPU for the Phase 0 spikes?~~ Answered: on-demand Vast.ai GPU runs.
4. Are 10 user interviews realistic in the next two weeks, or should the target be 5?
5. Is the first release open-weight, API-only, or both?
