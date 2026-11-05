# Vast.ai Ephemeral GPU Runner

Create a GPU instance on demand, run a command, and destroy it automatically.

This is intentionally **not** a persistent cluster manager. It is a cost-control wrapper for short Phase 0/1 runs.

## Requirements

- A Vast.ai API key with instance-management permission.
- An SSH key already registered with Vast.ai.
- `ssh` and `rsync` locally.

The runner loads `VAST_API_KEY` from the repo `.env` automatically:

```sh
# .env
VAST_API_KEY=your-key-here
```

You can also export it in the shell. Existing environment variables are not overridden.

## Search offers

```sh
python3 scripts/vast_ephemeral.py search \
  --gpu-name "RTX 4090" \
  --min-vram 24000 \
  --disk 48 \
  --max-hourly 2.00
```

`--min-vram` is in MB. Use `48000` for a 48GB GPU.

## Run a command and destroy

```sh
python3 scripts/vast_ephemeral.py run \
  --gpu-name "RTX 4090" \
  --min-vram 48000 \
  --disk 48 \
  --max-hourly 2.00 \
  --sync /Users/alex/community-llm \
  --remote-dir /workspace/community-llm \
  --remote-command "cd /workspace/community-llm/spikes/phase0 && uv sync --extra vllm && uv run python check_env.py"
```

The instance is destroyed when the command finishes, even if the command fails. Use `--keep-on-failure` to keep it for debugging.

## Create manually

```sh
python3 scripts/vast_ephemeral.py create \
  --gpu-name "RTX 4090" \
  --min-vram 48000 \
  --disk 48
```

This prints the instance ID, SSH host, and SSH port, and leaves the instance running. Destroy it explicitly when done:

```sh
python3 scripts/vast_ephemeral.py destroy --instance-id 12345678
```

## List instances

```sh
python3 scripts/vast_ephemeral.py list
```

## Safety rules

- The script refuses to create without `VAST_API_KEY`.
- It filters for verified, rentable, on-demand offers.
- It caps the hourly price with `--max-hourly`.
- It destroys the instance after `run`, including on command failure.
- It requires the SSH key to exist before creation.
- It never prints the API key.
- It does not stop instances automatically; `destroy` removes them and their disk.

## Cost note

The script prints the offer rate and estimated GPU cost after the run. It does not include storage, egress, or idle time if you use `create` and leave it running.

For the issue-tracker QLoRA run, expected GPU time is 15–30 minutes once the environment is installed.
