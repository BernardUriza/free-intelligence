from __future__ import annotations

from fi_devtools.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_fi_help_lists_groups() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    output = result.output.lower()
    assert "free intelligence devtools" in output

    # Group commands
    assert "lint" in output
    assert "migrate" in output
    assert "analyze" in output
    assert "recover" in output
    assert "ci" in output


def test_fi_lint_help() -> None:
    result = runner.invoke(app, ["lint", "--help"])
    assert result.exit_code == 0

    output = result.output.lower()
    assert "lint fixers" in output
    assert "type-ignores" in output
