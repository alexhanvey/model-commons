# Phase 0 Spike Results

Raw evaluation summaries from the 48GB RTX 5880 Ada host.

Dataset: `../data/hard_heldout_tools.jsonl` — 40 cases across single-tool, no-tool, clarify, multi-tool, nested args, prompt injection, and multi-turn.

| File | Model | Result |
|---|---|---:|
| `qwen3-1.7b-base-hard-eval-final.json` | Qwen3-1.7B base | 97.5% (39/40) |
| `qwen3-1.7b-toolace-hard-eval.json` | Qwen3-1.7B + ToolACE adapter | 65% (26/40) |
| `qwen3-1.7b-mix-hard-eval.json` | Qwen3-1.7B + balanced mix adapter | 85% (34/40) |
| `granite-4.1-3b-base-hard-eval.json` | Granite 4.1 3B base | 100% (40/40) |
| `granite-4.1-3b-mix-hard-eval.json` | Granite 4.1 3B + balanced mix adapter | 85% (34/40) |

The base Granite model is the MVP selection. The current adapters are not release candidates.

The raw files include prompts and model outputs; they are not secrets.
