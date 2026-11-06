# Model Release and Distribution

Status: Phase 5 planning

This runbook publishes a released model for local, mobile, and server use. There is no hosted
inference in the MVP.

## Prerequisites

- The recipe is in `tuning/recipes/` at a pinned commit.
- `just validate-tuning` passes.
- The model version passed the release gate and is `released`.
- Base model, dataset, and adapter licenses allow redistribution and the intended commercial or
  non-commercial use.
- The model card and dataset card are complete.

Negative results remain in `tuning/.../results/`; do not publish them as a model release.

## Hugging Face repository

```text
model-commons/<model-name>-<version>/
  README.md              # model card, usage, limits
  LICENSE
  adapter/               # PEFT adapter (reproducibility)
  merged/                # merged weights where the license allows
  gguf/                  # Q4_K_M, Q5_K_M
  mlx/                   # Apple 4-bit artifacts where practical
  eval/
    results.json
    summary.json
    safety.json
  manifest.json          # checksums, recipe ref, base revision, licenses
  SHA256SUMS
```

## Build artifacts

Adapter: produced by the training runner.

Merged weights, where allowed:

```sh
uv run python -m peft.merge_adapter --base ibm-granite/granite-4.1-3b \
  --adapter runs/vast-lora-v3/adapter --output merged
```

GGUF:

```sh
python llama.cpp/convert_hf_to_gguf.py merged --outfile model-f16.gguf
llama-quantize model-f16.gguf gguf/model-Q4_K_M.gguf Q4_K_M
llama-quantize model-f16.gguf gguf/model-Q5_K_M.gguf Q5_K_M
```

MLX, where practical:

```sh
mlx_lm.convert --hf-path merged --mlx-path mlx/4bit -q
```

Pin the tool versions used for quantization and record them in `manifest.json`.

## Manifest and checksums

`manifest.json` records:

- recipe repository, commit, path, and manifest SHA-256;
- base model and pinned revision;
- adapter, merged, GGUF, and MLX artifact checksums and sizes;
- dataset and eval checksums;
- licenses;
- quantization tool versions;
- release tag and publication timestamp.

Generate `SHA256SUMS` over every published artifact and verify it before upload. Sign the manifest
or checksums where practical.

## Publish

```sh
huggingface-cli upload model-commons/<model-name>-<version> ./release --repo-type model
```

The model card must include:

- what the model is and is not for;
- supported runtimes and quantizations;
- evaluation results and known failures;
- memory, latency, and device notes;
- license and attribution;
- the recipe and manifest hash.

## Runtime quickstarts

llama.cpp:

```sh
llama-cli -m model-Q4_K_M.gguf -p "List the open issues in Atlas." --jinja
```

Ollama: provide a `Modelfile` and usage instructions.

LM Studio: document the model directory and recommended context length.

MLX: provide the `mlx_lm.generate` command and memory guidance.

## Mobile evaluation

Record for each reference device:

- device and OS;
- runtime and version;
- quantized install size;
- peak RAM;
- tokens/sec;
- first-token latency;
- tool-call validity on the eval set;
- thermal throttling and battery notes.

At minimum, test one high-end and one mid-range device. Do not claim mobile support from desktop
benchmarks alone.

## Release checklist

- [ ] Release gate passed.
- [ ] Adapter and merged checksums recorded.
- [ ] GGUF Q4_K_M/Q5_K_M load and run.
- [ ] MLX artifacts load where practical.
- [ ] Model card, dataset card, license, and eval results included.
- [ ] `SHA256SUMS` verifies.
- [ ] Runtime quickstarts tested.
- [ ] Mobile reference matrix recorded for the mobile tier.
- [ ] No hosted inference deployed.
