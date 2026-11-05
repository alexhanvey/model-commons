from __future__ import annotations

import platform
import shutil
import subprocess

import typer

app = typer.Typer(no_args_is_help=True, help="Community LLM GPU worker")


@app.command()
def version() -> None:
    """Print the worker version."""
    typer.echo("community-llm-worker 0.1.0")


@app.command()
def doctor() -> None:
    """Check the local worker environment."""
    typer.echo(f"python: {platform.python_version()}")
    typer.echo(f"platform: {platform.platform()}")

    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        typer.echo("nvidia-smi: missing (GPU jobs will not run)")
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


if __name__ == "__main__":
    app()
