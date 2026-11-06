# ADR-0006: Distribution-First Model Releases

Status: Accepted
Date: 2026-11-06

## Context

The platform's useful output is a small fine-tuned model that people can run themselves. Hosting
models would require persistent GPU capacity, budget, abuse controls, rate limiting, tenant
isolation, billing, uptime, and a privacy and logging policy. Those costs and risks dominate the
MVP and are difficult to justify before the community has released a model worth using.

At the same time, users can run 1B–3B 4-bit models on laptops, desktops, and high-end phones, or
serve them from their own hardware. A downloadable release removes the platform from the inference
path and lets users keep prompts and data local.

## Decision

Make **downloadable model releases** the first-class output of the platform.

- Publish each release as a Hugging Face model repository containing:
  - the PEFT adapter for reproducibility;
  - merged weights where the base-model and dataset licenses allow;
  - GGUF quantizations for llama.cpp, Ollama, and LM Studio;
  - MLX 4-bit artifacts for Apple devices where practical;
  - model card, dataset card, evaluation results, license, manifest, and checksums.
- Do not host inference in the MVP. `apps/inference` remains future code and is not an MVP gate.
  There is no platform-owned GPU serving host in the initial deployment.
- Keep the release gate. A community fine-tune is not released until it beats the base model on the
  primary metric without an unacceptable category regression. Negative results are published as
  research results, not model releases.
- Treat mobile as a separate model tier:
  - mobile: 0.5–1.5B parameters, 4-bit;
  - laptop: 1–3B, 4-bit;
  - server: 3B+.
  The recipe schema and tuning tree support multiple base models. Granite 4.1 3B is the first
  laptop/server target; a smaller mobile base model is a follow-up.
- In the distribution-first phase, Community Points are recognition, priority, and early access.
  They are not inference credits until hosted inference exists.
- Private model commerce starts with licensed downloads and private artifacts. Hosted private
  endpoints remain a later step under ADR-0005.

## Consequences

- The MVP avoids GPU hosting cost, abuse handling, prompt logging, billing, and uptime obligations.
- Users get local, private inference and can run models offline.
- The platform still needs packaging, quantization, artifact signing, checksums, runtime
  quickstarts, and on-device evaluation.
- Downloads cannot be revoked, so licenses, attribution, model cards, and acceptable-use terms
  matter.
- Points need a new sink. Reputation, job-queue priority, and future hosted credits replace
  inference spending for now.
- Support shifts to device and runtime compatibility. Provide known-good configurations rather than
  a hosted service.
- Model releases can be evaluated on real phones, not just server GPUs.

## Rejected alternatives

### Hosted inference first

- Requires persistent GPU budget and on-call operations before the first useful model exists.
- Adds abuse, privacy, rate-limit, billing, and tenant-isolation work to the MVP.
- Makes the community dependent on the platform to use its own model.

### API-only release

- Contradicts the goal of local, mobile, and private use.
- Creates a single point of failure and ongoing hosting cost.

### Mobile-only first release

- A 3B model is not viable on many mid-range phones.
- Laptop and desktop users can use the current model immediately.
- A smaller mobile tier is better added once the release pipeline works.

### Publish every adapter

- Lowers the quality bar and confuses users.
- Negative results are valuable as research records, not as model releases.

## Open questions

- Which 0.5–1.5B Apache-2.0 model becomes the first mobile track?
- Which runtime is primary: GGUF/llama.cpp, MLX, or both?
- Which reference devices define the mobile evaluation matrix?
- What points sink is compelling before hosted inference exists?
- Do we publish merged weights, adapters, or both for each release?
- Which channels beyond Hugging Face: Ollama library, LM Studio, MLX community?
