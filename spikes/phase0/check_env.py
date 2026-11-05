#!/usr/bin/env python3
"""Check the Phase 0 GPU environment."""

from __future__ import annotations

import importlib.metadata
import shutil
import sys
from pathlib import Path


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def main() -> int:
    print(f"python: {sys.version.split()[0]}")
    for pkg in ("torch", "transformers", "peft", "datasets", "bitsandbytes", "accelerate", "vllm"):
        print(f"{pkg}: {package_version(pkg)}")

    try:
        import torch
    except ImportError:
        print("torch: import failed")
        return 1

    print(f"cuda available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("No CUDA GPU detected. Use a remote NVIDIA host for the spikes.")
        return 2

    count = torch.cuda.device_count()
    print(f"cuda device count: {count}")
    for index in range(count):
        props = torch.cuda.get_device_properties(index)
        print(
            f"gpu[{index}]: {props.name} | "
            f"vram={props.total_memory / 1024**3:.1f} GiB | "
            f"compute={props.major}.{props.minor}"
        )

    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        driver = pynvml.nvmlSystemGetDriverVersion()
        print(f"nvidia driver: {driver}")
        print(f"gpu name: {pynvml.nvmlDeviceGetName(handle)}")
        pynvml.nvmlShutdown()
    except Exception as exc:  # noqa: BLE001
        print(f"nvidia-smi details unavailable: {exc}")

    disk = shutil.disk_usage(Path.cwd())
    print(f"disk free: {disk.free / 1024**3:.1f} GiB")
    print(f"workspace: {Path.cwd()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
