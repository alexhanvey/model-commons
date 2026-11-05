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
