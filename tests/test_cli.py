"""
Free Intelligence - CLI Tests

Tests for fi-llm CLI tool.

File: tests/test_cli.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001
"""

import json
import subprocess
from pathlib import Path

import pytest


def test_cli_help() -> None:
    """Test fi-llm --help shows usage."""
    result = subprocess.run(
        ["python3", "tools/fi_llm.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "Free Intelligence - LLM CLI" in result.stdout
    assert "--provider" in result.stdout
    assert "--model" in result.stdout


def test_cli_missing_required_args() -> None:
    """Test fi-llm fails without required arguments."""
    result = subprocess.run(
        ["python3", "tools/fi_llm.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode != 0
    assert "required" in result.stderr.lower()


def test_cli_json_output(tmp_path) -> None:
    """Test fi-llm --json returns valid JSON (requires mock or live server)."""
    # This test requires either:
    # 1. A live LLM server (port 9001) running
    # 2. Or we skip it if server unavailable
    # Since mocking subprocess is complex, we skip if server not available

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test prompt")

    result = subprocess.run(
        [
            "python3",
            "tools/fi_llm.py",
            "--provider",
            "ollama",
            "--model",
            "qwen2:7b",
            "--prompt",
            str(prompt_file),
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        timeout=5,
    )

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("CLI did not return valid JSON")

    # If server not available, skip
    if not data.get("ok") and "Connection refused" in data.get("error", ""):
        pytest.skip("LLM server (port 9001) not running - start with 'make llm-dev'")

    # If successful (server running), check JSON output
    assert "ok" in data
    if data["ok"]:
        assert "text" in data


def test_cli_text_output(tmp_path) -> None:
    """Test fi-llm returns text output (not JSON)."""
    # This test would need a mock or actual Ollama server
    # For now, we test that --json flag changes output format
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test")

    # Without --json, should return plain text (or error if server unavailable)
    result = subprocess.run(
        [
            "python3",
            "tools/fi_llm.py",
            "--provider",
            "ollama",
            "--model",
            "qwen2:7b",
            "--prompt",
            str(prompt_file),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        timeout=5,
    )

    # Should fail if Ollama not running, but should NOT output JSON
    if result.returncode != 0:
        assert "ERROR:" in result.stderr
    else:
        # If successful, should be plain text
        assert not result.stdout.strip().startswith("{")


def test_cli_reads_prompt_from_file(tmp_path) -> None:
    """Test fi-llm reads prompt from file."""
    prompt_file = tmp_path / "test_prompt.txt"
    prompt_file.write_text("Read this from file")

    # We can't test actual execution without mocking/server,
    # but we can verify the file is read correctly
    from tools.fi_llm import read_input

    content = read_input(str(prompt_file))
    assert content == "Read this from file"


def test_cli_uses_prompt_as_literal() -> None:
    """Test fi-llm uses prompt as literal string if not a file."""
    from tools.fi_llm import read_input

    content = read_input("This is not a file path")
    assert content == "This is not a file path"
