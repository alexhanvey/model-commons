from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "community-llm" / "worker.json"


class WorkerConfig(BaseModel):
    api_url: str = "http://localhost:8000"
    worker_token: str = ""
    worker_id: str | None = None
    worker_name: str = "worker"
    poll_interval: float = 5.0
    heartbeat_interval: float = 30.0


def config_path() -> Path:
    return Path(
        os.environ.get("COMMUNITY_LLM_WORKER_CONFIG", str(DEFAULT_CONFIG_PATH))
    ).expanduser()


def load_config(path: Path | None = None) -> WorkerConfig:
    target = path or config_path()
    config = (
        WorkerConfig.model_validate_json(target.read_text()) if target.exists() else WorkerConfig()
    )
    if api_url := os.environ.get("COMMUNITY_LLM_API_URL"):
        config.api_url = api_url
    if token := os.environ.get("COMMUNITY_LLM_WORKER_TOKEN"):
        config.worker_token = token
    return config


def save_config(config: WorkerConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(config.model_dump_json(indent=2))
    target.chmod(0o600)
    return target
