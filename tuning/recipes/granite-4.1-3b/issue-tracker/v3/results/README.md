# Results

Training and evaluation outputs are added here by a run. Each result must include:

- run id and timestamp;
- recipe commit and manifest SHA-256;
- base model revision;
- dataset and eval checksums;
- raw `results.json`, `summary.json`, and safety output;
- GPU type and runtime;
- known failures and sample sizes.

Do not commit generated adapters. Store them in object storage by checksum.
