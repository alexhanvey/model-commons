# MVP Specification

Status: Distribution-first MVP selected
Last updated: 2026-11-06

## One-sentence MVP

> A solo developer or small team can contribute GPU time to a community small-model lab, earn
> best-effort points, and download a small open model that the community has fine-tuned and
> evaluated for tool use, then run it locally, on a phone, or on their own server.

## Target user

**Primary user:** solo developers and small teams building local or agentic applications.

They need a cheap, open, small model that can:

- follow instructions reliably;
- call tools with structured arguments;
- run locally, on a phone, or on their own server;
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

> “As a developer building an agent, I want a small open model that can call my tools with reliable JSON arguments, so I can download it and run it on a phone, laptop, or my own server without depending on a closed provider.”

## MVP loop

1. Contributor signs in with GitHub.
2. Contributor registers a worker.
3. Worker runs a benchmark.
4. Contributor runs a verified evaluation job.
5. Contributor runs a LoRA fine-tune job.
6. Admin or automated checks verify the job.
7. Contributor earns points.
8. The community releases the model on Hugging Face with evaluation results and quantized artifacts.
9. Users download and run the model locally, on a phone, or on their own server.
10. Points provide recognition, job-queue priority, and early access until hosted inference exists.

Tuning recipes live in a community-governed repository. Contributors propose recipe changes by pull
request; merging a recipe makes it a candidate, not a released model.

## Proposed success metrics

- 3–10 registered workers.
- 20–50 contributors recruited.
- 100 model downloads across supported runtimes.
- 1 verified LoRA job.
- 1 public model release with evaluation results.
- At least one external tuning recipe merged.
- 95% job success rate.
- Points ledger exact, no negative balances.
- At least 3 runtime quickstarts (llama.cpp, Ollama, MLX or equivalent).
- On-device tool-call validity and latency recorded on at least two reference devices.
- At least 3 beta users return within one week.

## Proposed stack

- Python 3.12 + FastAPI + Pydantic v2.
- Next.js 15 + TypeScript + Tailwind + shadcn/ui.
- Postgres 16 + SQLAlchemy 2 + Alembic.
- Redis 7 + ARQ.
- S3-compatible storage (RustFS locally, Cloudflare R2 in production).
- Hugging Face model repos for distribution.
- GGUF/llama.cpp and MLX for local and mobile runtime artifacts.
- PyTorch, Transformers, PEFT, TRL, bitsandbytes for training.
- `lm-evaluation-harness` plus custom tool-use evaluations.
- Docker Compose locally; Fly.io + Vercel + Neon + Upstash + R2 in production.
- GitHub OAuth + hashed API keys for job submission.
- OpenTelemetry, Prometheus/Grafana, Sentry.
- vLLM is post-MVP, for optional hosted inference.

## Proposed points policy

- Non-contractual.
- Non-transferable.
- No cash value.
- Best effort.
- May expire.
- Earned for verified benchmark, evaluation, and LoRA jobs.
- Spent on job-queue priority, early access, and future hosted inference when available.
- Admin discretion.
- Beta-only.

## Out of scope for the MVP

- Full pretraining from scratch.
- Distributed training across home GPUs.
- Hosted inference, community inference routing, or a platform inference API.
- Paid inference or paid credits.
- Private model marketplace, paid access, or contributor payouts.
- Token, blockchain, or credit exchange.
- Enterprise, on-prem, or customer-managed keys.
- 7B+ models.
- A native mobile app; downloadable mobile models and runtime quickstarts are in scope.
- Multi-tenant organizations.
- Kubernetes.
- Frontier-model claims.

Long-term, contributors may offer privately tuned models for specific tasks and earn money from
them. That is a separate commercial track with its own legal, billing, and isolation requirements;
it is not part of the MVP. See [ADR-0005](adr/0005-private-model-commerce.md).

## Open decisions

| Decision | Proposed choice | Status |
|---|---|---|
| Target user | Solo developers / small agent teams | Locked |
| First capability | Tool use / function calling | Locked |
| Base model | `ibm-granite/granite-4.1-3b` (Apache 2.0) | Locked |
| Repository topology | Engine vs recipes split; standalone recipes repository before Phase 9 | Accepted |
| Distribution | Downloadable Hugging Face releases with GGUF/MLX artifacts; no hosted inference in the MVP | Accepted |
| Mobile tier | 0.5–1.5B 4-bit model track; base model open | Open |
| Dataset | ToolACE (Apache 2.0) + custom held-out set | Source selected |
| Evaluation | 60-case hard tool-calling set + custom schemas + on-device matrix | In progress |
| GPU target | One 24GB NVIDIA GPU for QLoRA; no serving GPU in the MVP; rent via Vast | Locked |
| Deployment | Fly.io + Vercel + Neon + Upstash + R2; Hugging Face distribution | Proposed |
| Points | Non-contractual, non-transferable, no cash | Proposed |
| Private model commerce | Post-MVP; separate fiat billing and payouts; see ADR-0005 | Direction accepted |

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
