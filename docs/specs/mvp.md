# MVP Specification

Status: Target user, capability, base model, and dataset source selected
Last updated: 2026-11-03

## One-sentence MVP

> A solo developer or small team can contribute GPU time to a community small-model lab, earn best-effort points, and use those points to run inference against a small open model that the community has fine-tuned and evaluated for tool use.

## Target user

**Primary user:** solo developers and small teams building local or agentic applications.

They need a cheap, open, OpenAI-compatible small model that can:

- follow instructions reliably;
- call tools with structured arguments;
- run locally or through a hosted API;
- be fine-tuned by the community without a large cloud contract.

**Not the first user:** large enterprises, regulated industries, AAA game studios, or frontier-model researchers.

## First capability

**Tool use / function calling for agent workflows.**

The first narrow domain target is **GitHub-style issue-tracker tool calling**: issue triage, assignment, labels, comments, linking, and confirmation-sensitive close/reopen workflows.

Why:

- It is concrete and testable.
- It is useful to agent developers.
- It can be evaluated with public and custom held-out tool schemas.
- Small models can be competitive at narrow tool-calling tasks.
- It fits an OpenAI-compatible chat-completions API.

Non-goals for the first capability:

- General frontier chat.
- Long-context reasoning.
- Multimodal input.
- Autonomous computer use.
- Coding agent benchmarks.

## Proposed user story

> “As a developer building an agent, I want a small open model that can call my tools with reliable JSON arguments, so I can run it locally or through a cheap API without depending on a closed provider.”

## MVP loop

1. Contributor signs in with GitHub.
2. Contributor registers a worker.
3. Worker runs a benchmark.
4. Contributor runs a verified evaluation job.
5. Contributor runs a LoRA fine-tune job.
6. Admin or automated checks verify the job.
7. Contributor earns points.
8. A released community model is served through an OpenAI-compatible API.
9. Contributor spends points on inference.
10. The community releases the model with evaluation results.

## Proposed success metrics

- 3–10 registered workers.
- 20–50 contributors recruited.
- 10 external users with API keys.
- 1M tokens served.
- 1 verified LoRA job.
- 1 public model release with evaluation results.
- 95% job success rate.
- Points ledger exact, no negative balances.
- p95 inference latency acceptable for the chosen model.
- At least 3 beta users return within one week.

## Proposed stack

- Python 3.12 + FastAPI + Pydantic v2.
- Next.js 15 + TypeScript + Tailwind + shadcn/ui.
- Postgres 16 + SQLAlchemy 2 + Alembic.
- Redis 7 + ARQ.
- S3-compatible storage (RustFS locally, Cloudflare R2 in production).
- vLLM for inference.
- PyTorch, Transformers, PEFT, TRL, bitsandbytes for training.
- `lm-evaluation-harness` plus custom tool-use evaluations.
- Docker Compose locally; Fly.io + Vercel + Neon + Upstash + R2 in production.
- GitHub OAuth + hashed API keys.
- OpenTelemetry, Prometheus/Grafana, Sentry.

## Proposed points policy

- Non-contractual.
- Non-transferable.
- No cash value.
- Best effort.
- May expire.
- Earned for verified benchmark, evaluation, and LoRA jobs.
- Spent on inference.
- Admin discretion.
- Beta-only.

## Out of scope for the MVP

- Full pretraining from scratch.
- Distributed training across home GPUs.
- Community inference routing.
- Paid inference or paid credits.
- Token, blockchain, or credit exchange.
- Enterprise, on-prem, or customer-managed keys.
- 7B+ models.
- Mobile app.
- Multi-tenant organizations.
- Kubernetes.
- Frontier-model claims.

## Open decisions

| Decision | Proposed choice | Status |
|---|---|---|
| Target user | Solo developers / small agent teams | Locked |
| First capability | Tool use / function calling | Locked |
| Base model | `ibm-granite/granite-4.1-3b` (Apache 2.0) | Locked |
| Dataset | ToolACE (Apache 2.0) + custom held-out set | Source selected |
| Evaluation | 40-case hard tool-calling set + custom schemas | Implemented |
| GPU target | One 24GB NVIDIA GPU for QLoRA; 48GB preferred for serving; rent via RunPod/Lambda | Locked |
| Deployment | Fly.io + Vercel + Neon + Upstash + R2; GPU on RunPod/Lambda | Proposed |
| Points | Non-contractual, non-transferable, no cash | Proposed |

## Phase 0 exit criteria

- One target user chosen.
- One capability chosen.
- One base model chosen and license reviewed.
- One dataset chosen and license reviewed.
- One evaluation suite with thresholds.
- Points policy drafted.
- Legal checklist drafted.
- Architecture decisions recorded.
- 10 contributor interviews completed.
- 10 user interviews completed.
- At least 3 beta commitments.
- QLoRA spike passed.
- vLLM spike passed.
- Worker sandbox spike passed.
