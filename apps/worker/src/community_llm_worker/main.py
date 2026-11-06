from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from community_llm_protocol import JobKind

from community_llm_worker.client import WorkerClient, create_job, register_worker
from community_llm_worker.config import WorkerConfig, load_config, save_config
from community_llm_worker.executor import FakeGpuExecutor
from community_llm_worker.runner import run_loop

app = typer.Typer(no_args_is_help=True, help="Community LLM GPU worker")


@app.command()
def version() -> None:
    """Print the worker version."""
    typer.echo("community-llm-worker 0.1.0")


@app.command()
def doctor() -> None:
    """Check the local worker environment."""
    config = load_config()
    typer.echo(f"python: {platform.python_version()}")
    typer.echo(f"platform: {platform.platform()}")
    typer.echo(f"api: {config.api_url}")
    typer.echo(f"worker token: {'set' if config.worker_token else 'missing'}")

    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        typer.echo("nvidia-smi: missing (use --fake-gpu for local smoke jobs)")
        return

    result = subprocess.run(
        [nvidia_smi, "-L"],
        capture_output=True,
        text=True,
        check=False,
    )
    typer.echo(f"nvidia-smi: {'ok' if result.returncode == 0 else 'error'}")
    if result.stdout.strip():
        typer.echo(result.stdout.strip())


@app.command()
def register(
    session_cookie: Annotated[
        str,
        typer.Option(
            "--session-cookie",
            envvar="COMMUNITY_LLM_SESSION_COOKIE",
            prompt=True,
            hide_input=True,
        ),
    ],
    csrf_token: Annotated[
        str,
        typer.Option(
            "--csrf-token",
            envvar="COMMUNITY_LLM_CSRF_TOKEN",
            prompt=True,
            hide_input=True,
        ),
    ],
    name: Annotated[str, typer.Option("--name", help="Human-readable worker name.")] = "worker",
    api_url: Annotated[
        str,
        typer.Option("--api-url", envvar="COMMUNITY_LLM_API_URL"),
    ] = "http://localhost:8000",
    config_path: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Register a worker and save its token."""
    created = register_worker(api_url, name, session_cookie, csrf_token)
    config = WorkerConfig(
        api_url=api_url,
        worker_token=created.token,
        worker_id=str(created.worker.id),
        worker_name=name,
    )
    saved = save_config(config, config_path)
    typer.echo(f"Registered worker {created.worker.id} ({created.worker.status}).")
    typer.echo(f"Worker token saved to {saved}.")
    if created.worker.status != "approved":
        typer.echo("An admin must approve this worker before it can poll jobs.")


@app.command()
def status(
    config_path: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Show the configured worker and API status."""
    config = load_config(config_path)
    if not config.worker_token:
        typer.echo("No worker token. Run `community-llm-worker register` first.", err=True)
        raise typer.Exit(1)

    with WorkerClient(config.api_url, config.worker_token) as client:
        worker = client.heartbeat()

    typer.echo(f"worker: {worker.id} ({worker.name})")
    typer.echo(f"status: {worker.status}")
    typer.echo(f"last_heartbeat_at: {worker.last_heartbeat_at}")


@app.command()
def run(
    once: Annotated[bool, typer.Option("--once", help="Poll once and exit.")] = False,
    fake_gpu: Annotated[
        bool,
        typer.Option("--fake-gpu", help="Use the fake-GPU executor."),
    ] = False,
    poll_interval: Annotated[float, typer.Option("--poll-interval")] = 5.0,
    heartbeat_interval: Annotated[float, typer.Option("--heartbeat-interval")] = 30.0,
    config_path: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Poll for a job, execute it, and report the result."""
    config = load_config(config_path)
    if not config.worker_token:
        typer.echo("No worker token. Run `community-llm-worker register` first.", err=True)
        raise typer.Exit(1)
    if not fake_gpu:
        typer.echo(
            "Only --fake-gpu execution is implemented; real GPU runners arrive in Phase 4.",
            err=True,
        )
        raise typer.Exit(2)

    with WorkerClient(config.api_url, config.worker_token) as client:
        run_loop(
            client,
            FakeGpuExecutor(),
            once=once,
            poll_interval=poll_interval,
            heartbeat_interval=heartbeat_interval,
        )


@app.command()
def benchmark(
    session_cookie: Annotated[
        str,
        typer.Option(
            "--session-cookie",
            envvar="COMMUNITY_LLM_SESSION_COOKIE",
            prompt=True,
            hide_input=True,
        ),
    ],
    csrf_token: Annotated[
        str,
        typer.Option(
            "--csrf-token",
            envvar="COMMUNITY_LLM_CSRF_TOKEN",
            prompt=True,
            hide_input=True,
        ),
    ],
    suite: Annotated[str, typer.Option("--suite")] = "smoke",
    api_url: Annotated[
        str,
        typer.Option("--api-url", envvar="COMMUNITY_LLM_API_URL"),
    ] = "http://localhost:8000",
) -> None:
    """Create a benchmark job."""
    job = create_job(
        api_url,
        JobKind.BENCHMARK,
        {"suite": suite},
        session_cookie,
        csrf_token,
    )
    typer.echo(f"Created benchmark job {job.id} ({job.status.value}).")
    typer.echo("Run `community-llm-worker run --once --fake-gpu` on an approved worker.")


@app.command()
def logs(
    attempt_id: str,
    config_path: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Print a job attempt's redacted logs and metrics."""
    config = load_config(config_path)
    if not config.worker_token:
        typer.echo("No worker token. Run `community-llm-worker register` first.", err=True)
        raise typer.Exit(1)

    with WorkerClient(config.api_url, config.worker_token) as client:
        result = client.result(attempt_id)

    if result.logs:
        typer.echo(result.logs)
    if result.metrics is not None:
        typer.echo(json.dumps(result.metrics, indent=2, sort_keys=True))
    if result.error:
        typer.echo(f"error: {result.error}", err=True)


if __name__ == "__main__":
    app()
