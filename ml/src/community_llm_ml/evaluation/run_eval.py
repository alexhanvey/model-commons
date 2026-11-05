#!/usr/bin/env python3
"""Evaluation entry point.

Phase 1 only validates an eval config. The real harness arrives in Phase 4.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED = {"model", "dataset", "tasks"}


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("eval config must be a mapping")
    missing = REQUIRED - config.keys()
    if missing:
        raise ValueError(f"missing config keys: {sorted(missing)}")
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/eval"))
    args = parser.parse_args()

    config = load_config(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"config": str(args.config), "tasks": config["tasks"]}
    (args.output_dir / "eval_config.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
