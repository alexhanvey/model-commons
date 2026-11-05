#!/usr/bin/env python3
"""Dataset preparation entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [line for line in args.input.read_text().splitlines() if line.strip()]
    with args.output.open("w") as handle:
        for line in lines:
            json.loads(line)
            handle.write(line + "\n")

    report = {
        "input": str(args.input),
        "output": str(args.output),
        "examples": len(lines),
        "sha256": sha256(args.output),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
