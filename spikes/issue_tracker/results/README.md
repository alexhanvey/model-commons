# Issue Tracker Spike Results

## Granite 4.1 3B base — 60-case headroom eval

Run on a 24GB RTX 4090 with vLLM 0.33.0 and the `granite4` tool parser.

| Metric | Result |
|---|---:|
| Total | 60 |
| Passed | 42 |
| Rate | **70.0%** |
| p50 latency | 1075ms |

### Categories

| Category | Passed | Rate |
|---|---:|---:|
| single_tool | 15/15 | 100% |
| multi_tool | 9/15 | 60% |
| clarify | 9/10 | 90% |
| no_tool | 1/5 | 20% |
| nested_search | 3/5 | 60% |
| confirmation | 0/5 | 0% |
| prompt_injection | 5/5 | 100% |

## Adapter v1 — 800 examples, 150 steps

- Train loss: 0.2066
- Eval loss: 0.0770
- Eval: **53.3% (32/60)**
- p50: 7110ms
- Not a release candidate.

## Adapter v2 — rebalanced 800 examples, 50 steps, LR 1e-5

- Train loss: 0.8742
- Eval loss: 0.7330
- Training time: 140.5s
- Eval: **68.3% (41/60)**
- p50: 1289ms
- Still below base.

### v2 categories

| Category | Passed | Rate |
|---|---:|---:|
| single_tool | 12/15 | 80% |
| multi_tool | 10/15 | 67% |
| clarify | 8/10 | 80% |
| no_tool | 2/5 | 40% |
| nested_search | 4/5 | 80% |
| confirmation | 0/5 | 0% |
| prompt_injection | 5/5 | 100% |

## Token lengths

V2 data, Granite tokenizer, full tool schemas:

- min: 1706
- p50: 1897
- p95: 2351
- max: 2526
- over 2048: 150
- over 4096: 0

## Conclusion

Neither adapter beat the base model.

- v1: 53.3%
- v2: 68.3%
- base: **70.0%**

The v2 run improved over v1 and matched base on prompt injection, but still failed all confirmation cases and only passed 2/5 no-tool cases.

The current fine-tuning approach is **not validated**. The base Granite model remains the MVP selection.

Raw files:

- `granite-base-eval-v2.json`
- `granite-issue-tracker-adapter-eval.json` (v1)
- `granite-issue-tracker-v2-adapter-eval-summary.json` (v2 summary; raw cases were not downloaded due a path mismatch)
- `token_lengths.txt`
- `token_lengths_v2.txt`
