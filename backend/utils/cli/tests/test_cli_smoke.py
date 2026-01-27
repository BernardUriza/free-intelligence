from __future__ import annotations

from backend.utils.cli.cli import app
from typer.testing import CliRunner


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_cli_dev_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "--help"])
    assert result.exit_code == 0


def test_cli_dev_stop_noop() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["dev", "stop"])
    assert result.exit_code == 0


def test_cli_ops_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["ops", "--help"])
    assert result.exit_code == 0
