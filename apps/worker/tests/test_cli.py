from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from community_llm_protocol import WorkerCreated, WorkerPublic
from community_llm_worker.config import load_config
from community_llm_worker.main import app
from typer.testing import CliRunner


def test_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_doctor() -> None:
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "python:" in result.stdout
    assert "api:" in result.stdout


def test_register_saves_token(monkeypatch, tmp_path) -> None:
    created = WorkerCreated(
        worker=WorkerPublic(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            name="gpu-1",
            status="pending",
            created_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        token="wrk_test",
    )
    monkeypatch.setattr(
        "community_llm_worker.main.register_worker",
        lambda *args, **kwargs: created,
    )
    config_file = tmp_path / "worker.json"

    result = CliRunner().invoke(
        app,
        [
            "register",
            "--session-cookie",
            "session",
            "--csrf-token",
            "csrf",
            "--name",
            "gpu-1",
            "--api-url",
            "http://test",
            "--config",
            str(config_file),
        ],
    )

    assert result.exit_code == 0
    assert config_file.exists()
    assert oct(config_file.stat().st_mode & 0o777) == "0o600"
    saved = load_config(config_file)
    assert saved.worker_token == "wrk_test"
    assert saved.worker_name == "gpu-1"
