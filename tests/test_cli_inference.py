#!/usr/bin/env python3
"""
Free Intelligence - CLI Inference Tests

Unit tests for backend/cli/fi_test.py

File: tests/test_cli_inference.py
Card: FI-CLI-FEAT-002
Created: 2025-10-29
"""

import argparse
import json
from unittest.mock import Mock, patch

import pytest

from backend.cli.fi_test import cmd_prompt
from backend.llm_adapter import LLMResponse


@pytest.fixture
def mock_args():
    """Mock CLI arguments"""
    args = argparse.Namespace()
    args.prompt = "Test prompt"
    args.model = "ollama"
    args.max_tokens = 4096
    args.dry_run = False
    args.verbose = False
    return args


@pytest.fixture
def mock_llm_response():
    """Mock LLM response"""
    return LLMResponse(
        content="Test response from LLM",
        provider="ollama",
        model="llama3.2",
        tokens_used=150,
        latency_ms=500,
        finish_reason="stop",
        metadata={},
    )


def test_cmd_prompt_basic(mock_args, mock_llm_response):
    """Test basic prompt execution"""
    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction") as mock_append:
            mock_append.return_value = "test_interaction_id"

            result = cmd_prompt(mock_args)

            assert result["prompt"] == "Test prompt"
            assert result["response"] == "Test response from LLM"
            assert result["model"] == "llama3.2"
            assert result["provider"] == "ollama"
            assert result["tokens_used"] == 150
            assert result["latency_ms"] == 500
            assert result["dry_run"] is False
            assert "interaction_id" in result
            assert "session_id" in result


def test_cmd_prompt_dry_run(mock_args, mock_llm_response):
    """Test dry-run mode (no corpus save)"""
    mock_args.dry_run = True

    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction") as mock_append:
            result = cmd_prompt(mock_args)

            # Verify append_interaction was NOT called
            mock_append.assert_not_called()
            assert result["dry_run"] is True


def test_cmd_prompt_verbose(mock_args, mock_llm_response):
    """Test verbose mode (debug output)"""
    mock_args.verbose = True

    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction") as mock_append:
            with patch("backend.cli.fi_test.logger") as mock_logger:
                result = cmd_prompt(mock_args)

                # Verify logger was called (verbose output)
                assert mock_logger.info.call_count >= 3


def test_cmd_prompt_adapter_creation_fails(mock_args):
    """Test error handling when adapter creation fails"""
    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_create.side_effect = ValueError("Unknown provider: fake")

        result = cmd_prompt(mock_args)

        assert result["error"] == "adapter_creation_failed"
        assert "Unknown provider" in result["message"]
        assert "interaction_id" in result


def test_cmd_prompt_llm_generation_fails(mock_args):
    """Test error handling when LLM generation fails"""
    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.side_effect = Exception("API timeout")
        mock_create.return_value = mock_adapter

        result = cmd_prompt(mock_args)

        assert result["error"] == "llm_generation_failed"
        assert "API timeout" in result["message"]


def test_cmd_prompt_corpus_save_fails_non_blocking(mock_args, mock_llm_response):
    """Test that corpus save failure does not block response"""
    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction") as mock_append:
            mock_append.side_effect = Exception("Corpus save failed")

            result = cmd_prompt(mock_args)

            # Should still return result despite save failure
            assert "error" not in result
            assert result["response"] == "Test response from LLM"


def test_cmd_prompt_model_selection_claude(mock_args, mock_llm_response):
    """Test Claude model selection"""
    mock_args.model = "claude"

    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction"):
            result = cmd_prompt(mock_args)

            # Verify create_adapter was called with "claude"
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["provider"] == "claude"


def test_cmd_prompt_max_tokens_custom(mock_args, mock_llm_response):
    """Test custom max_tokens parameter"""
    mock_args.max_tokens = 200

    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction"):
            result = cmd_prompt(mock_args)

            # Verify LLMRequest was created with max_tokens=200
            call_args = mock_adapter.generate.call_args[0][0]
            assert call_args.max_tokens == 200


def test_cmd_prompt_result_json_serializable(mock_args, mock_llm_response):
    """Test that result is JSON serializable"""
    with patch("backend.cli.fi_test.create_adapter") as mock_create:
        mock_adapter = Mock()
        mock_adapter.generate.return_value = mock_llm_response
        mock_create.return_value = mock_adapter

        with patch("backend.cli.fi_test.append_interaction"):
            result = cmd_prompt(mock_args)

            # Should serialize without errors
            json_str = json.dumps(result)
            assert isinstance(json_str, str)
            assert len(json_str) > 0
