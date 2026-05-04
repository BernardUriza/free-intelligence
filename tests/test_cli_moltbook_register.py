"""Tests for the `moltbook-register` Typer subcommand.

Mocks MoltbookSource.register_agent so the test doesn't hit the network.
The subcommand is the operator's bootstrap path — it runs ONCE per
deployment to obtain an API key, so its UX matters a lot."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from insult.__main__ import app
from insult.core.sources.base import SourceError, SourceRateLimitError


@pytest.fixture
def runner():
    return CliRunner()


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_happy_path_prints_credentials_and_instructions(mock_register, runner):
    mock_register.return_value = {
        "api_key": "moltbook_sk_live_xyz123",
        "claim_url": "https://www.moltbook.com/claim/abc",
        "verification_code": "reef-X4B2",
    }
    result = runner.invoke(app, ["moltbook-register"])
    assert result.exit_code == 0
    out = result.stdout
    assert "moltbook_sk_live_xyz123" in out  # api key SHOULD print (operator needs it)
    assert "reef-X4B2" in out  # verification code SHOULD print
    assert "https://www.moltbook.com/claim/abc" in out  # claim url SHOULD print
    assert "SAVE THIS NOW" in out or "save" in out.lower()  # warning present
    assert "moltbook-api-key" in out  # Azure secret command shown
    assert "MOLTBOOK_API_KEY" in out  # .env hint shown


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_passes_default_name_and_description(mock_register, runner):
    mock_register.return_value = {
        "api_key": "moltbook_x",
        "claim_url": "https://x",
        "verification_code": "y",
    }
    runner.invoke(app, ["moltbook-register"])
    args = mock_register.call_args.args
    assert args[0] == "Insult"
    assert "Discord" in args[1]


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_overrides_name_and_description_via_flags(mock_register, runner):
    mock_register.return_value = {
        "api_key": "moltbook_x",
        "claim_url": "https://x",
        "verification_code": "y",
    }
    runner.invoke(
        app,
        ["moltbook-register", "--name", "TestBot", "--description", "test agent"],
    )
    args = mock_register.call_args.args
    assert args[0] == "TestBot"
    assert args[1] == "test agent"


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_source_error_exits_nonzero(mock_register, runner):
    mock_register.side_effect = SourceError("name already taken")
    result = runner.invoke(app, ["moltbook-register"])
    assert result.exit_code == 1
    assert "name already taken" in result.stderr or "name already taken" in result.stdout


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_rate_limit_error_exits_nonzero(mock_register, runner):
    """SourceRateLimitError is a SourceError — handled by the same branch.
    Exit code stays 1 (not 2) so monitoring can distinguish 'caller bug'
    from 'Moltbook said no'."""
    mock_register.side_effect = SourceRateLimitError("slow down", retry_after_seconds=60)
    result = runner.invoke(app, ["moltbook-register"])
    assert result.exit_code == 1


@patch("insult.core.sources.moltbook.MoltbookSource.register_agent", new_callable=AsyncMock)
def test_value_error_exits_with_code_2(mock_register, runner):
    """ValueError comes from input validation in register_agent (blank
    name/description). Exit code 2 separates 'bad operator input' from
    'Moltbook rejected'."""
    mock_register.side_effect = ValueError("name cannot be blank")
    result = runner.invoke(app, ["moltbook-register"])
    assert result.exit_code == 2


def test_help_text_mentions_agent(runner):
    """Help should not invoke register_agent at all — Typer short-circuits
    on --help. No need for the patch fixture."""
    result = runner.invoke(app, ["moltbook-register", "--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "agent" in out or "moltbook" in out
