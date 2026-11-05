#!/usr/bin/env python3
"""Config-driven LoRA training entry point.

Phase 1 only validates and summarizes the config. The real training runner
arrives in Phase 4.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED = {"version", "base_model", "dataset", "training", "lora", "output"}


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("training config must be a mapping")
    missing = REQUIRED - config.keys()
    if missing:
        raise ValueError(f"missing config keys: {sorted(missing)}")
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/lora-smoke"))
    args = parser.parse_args()

    config = load_config(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "config": str(args.config),
        "run_name": config.get("run_name"),
        "method": config["training"].get("method"),
        "max_steps": config["training"].get("max_steps"),
        "max_seq_length": config["training"].get("max_seq_length"),
        "output_dir": str(args.output_dir),
    }
    (args.output_dir / "config_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
