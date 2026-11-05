# ADR-0002: Base Model Selection

Status: Accepted
Date: 2026-11-03

## Context

The MVP needs a permissively licensed 1B–3B model that can be fine-tuned for tool use / function calling, served on a 24–48GB GPU, and released as open weights.

## Decision

Use **`ibm-granite/granite-4.1-3b`** as the MVP base model.

Reasons:

- Apache 2.0 license.
- Fits comfortably on a 48GB GPU.
- Fast serving: p50 ~277ms on the 40-case hard tool-calling set.
- 100% valid tool-call rate on the Phase 0 hard set.
- Strong no-tool, clarification, multi-tool, nested-argument, and prompt-injection behavior out of the box.
- No long thinking trace, unlike Qwen3-1.7B.

## Rejected alternatives

### Qwen3-1.7B

- Apache 2.0.
- Viable, but slower (p50 ~735ms) and scored 97.5% on the hard set.
- Thinking output consumes tokens and complicates latency.
- Fine-tuning with the current data degraded restraint and multi-tool behavior.

### SmolLM3-3B

- Apache 2.0 and fully open.
- Not evaluated because Granite met the bar first.
- Keep as a backup or future comparison.

### xLAM / Hammer

- Strong tool-calling models.
- Non-commercial licenses; excluded from the MVP.

## Consequences

- The first MVP model is Granite 4.1 3B base, not a community fine-tune.
- The community fine-tune must target a narrower, harder capability where the base model is not saturated.
- Generic tool-calling is a regression guard, not an improvement benchmark.
- QLoRA training and adapter serving work, but the current adapters are not release candidates.

## Evaluation evidence

| Model | Hard eval | p50 | Notes |
|---|---:|---:|---|
| Granite 4.1 3B base | 100% (40/40) | 277ms | Selected |
| Qwen3-1.7B base | 97.5% (39/40) | 735ms | Rejected for MVP; thinking latency |
| Qwen3-1.7B + ToolACE adapter | 65% (26/40) | 193ms | Overfit; not release candidate |
| Qwen3-1.7B + mix adapter | 85% (34/40) | 193ms | Better restraint, still below base |
| Granite 4.1 3B + mix adapter | 85% (34/40) | 311ms | No-tool collapse; not release candidate |
