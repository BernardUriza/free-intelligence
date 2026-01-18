"""
Unit tests for backend/providers/response_parsers.py

Tests cover:
- QwenThinkingParser: Parsing <think>...</think> blocks
- GenericParser: Generic response parsing
- LLMResponseParser ABC: Abstract base class

Following HIPAA: No PHI in test data.
"""

from __future__ import annotations

import pytest
from backend.providers.response_parsers import (
    GenericParser,
    LLMResponseParser,
    QwenThinkingParser,
)


# ==============================================================================
# Tests for QwenThinkingParser
# ==============================================================================
class TestQwenThinkingParserBasic:
    """Basic tests for QwenThinkingParser."""

    def test_empty_response(self) -> None:
        """Empty response should return (None, '')."""
        parser = QwenThinkingParser()
        result = parser.parse({"response": ""})

        assert result == (None, "")

    def test_missing_response_key(self) -> None:
        """Missing 'response' key should return (None, '')."""
        parser = QwenThinkingParser()
        result = parser.parse({})

        assert result == (None, "")

    def test_no_thinking_block(self) -> None:
        """Response without thinking block returns content only."""
        parser = QwenThinkingParser()
        result = parser.parse({"response": "Hello world"})

        thinking, content = result
        assert thinking is None
        assert content == "Hello world"

    def test_simple_thinking_block(self) -> None:
        """Simple <think>...</think> block should be extracted."""
        parser = QwenThinkingParser()
        response = {"response": "<think>Let me analyze this</think>The answer is 42."}
        result = parser.parse(response)

        thinking, content = result
        assert thinking == "Let me analyze this"
        assert content == "The answer is 42."

    def test_whitespace_stripped(self) -> None:
        """Whitespace should be stripped from thinking and content."""
        parser = QwenThinkingParser()
        response = {"response": "  <think>  reasoning  </think>  answer  "}
        result = parser.parse(response)

        thinking, content = result
        assert thinking == "reasoning"
        assert content == "answer"


class TestQwenThinkingParserNested:
    """Tests for nested thinking blocks in QwenThinkingParser."""

    def test_nested_thinking_blocks(self) -> None:
        """Nested <think> tags should be handled correctly."""
        parser = QwenThinkingParser()
        response = {"response": "<think>outer<think>inner</think>more outer</think>content"}
        result = parser.parse(response)

        thinking, content = result
        assert "outer" in thinking
        assert "inner" in thinking
        assert content == "content"

    def test_multiple_thinking_blocks(self) -> None:
        """Multiple separate thinking blocks should be joined."""
        parser = QwenThinkingParser()
        response = {
            "response": "<think>First thought</think>Part 1<think>Second thought</think>Part 2"
        }
        result = parser.parse(response)

        thinking, content = result
        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert content == "Part 1Part 2"


class TestQwenThinkingParserErrors:
    """Error handling tests for QwenThinkingParser."""

    def test_unclosed_think_tag_raises(self) -> None:
        """Unclosed <think> tag should raise ValueError."""
        parser = QwenThinkingParser()
        response = {"response": "<think>unclosed thinking"}

        with pytest.raises(ValueError) as exc_info:
            parser.parse(response)

        assert "unclosed" in str(exc_info.value).lower()

    def test_unmatched_closing_tag_raises(self) -> None:
        """Closing </think> without opening should raise ValueError."""
        parser = QwenThinkingParser()
        response = {"response": "content</think>more"}

        with pytest.raises(ValueError) as exc_info:
            parser.parse(response)

        assert "closing" in str(exc_info.value).lower()

    def test_mismatched_depth_raises(self) -> None:
        """Mismatched tag depth should raise ValueError."""
        parser = QwenThinkingParser()
        response = {"response": "<think><think>nested</think>oops"}  # One unclosed

        with pytest.raises(ValueError) as exc_info:
            parser.parse(response)

        assert "unclosed" in str(exc_info.value).lower()


class TestQwenThinkingParserEdgeCases:
    """Edge case tests for QwenThinkingParser."""

    def test_empty_thinking_block(self) -> None:
        """Empty thinking block should return None for thinking."""
        parser = QwenThinkingParser()
        response = {"response": "<think></think>actual content"}
        result = parser.parse(response)

        thinking, content = result
        assert thinking is None
        assert content == "actual content"

    def test_thinking_only_no_content(self) -> None:
        """Response with only thinking, no content."""
        parser = QwenThinkingParser()
        response = {"response": "<think>Only thoughts here</think>"}
        result = parser.parse(response)

        thinking, content = result
        assert thinking == "Only thoughts here"
        assert content == ""

    def test_partial_tag_not_matched(self) -> None:
        """Partial tags like '<thin' should not be matched."""
        parser = QwenThinkingParser()
        response = {"response": "<thin>not a tag</thin>"}
        result = parser.parse(response)

        thinking, content = result
        assert thinking is None
        assert content == "<thin>not a tag</thin>"

    def test_special_characters_in_content(self) -> None:
        """Special characters should be preserved."""
        parser = QwenThinkingParser()
        response = {"response": "<think>思考中</think>日本語テスト"}
        result = parser.parse(response)

        thinking, content = result
        assert thinking == "思考中"
        assert content == "日本語テスト"


# ==============================================================================
# Tests for GenericParser
# ==============================================================================
class TestGenericParserMessageFormat:
    """Tests for GenericParser with message dict format."""

    def test_message_format_response(self) -> None:
        """Response with message.content format."""
        parser = GenericParser()
        response = {"message": {"content": "Hello from message"}}
        result = parser.parse(response)

        thinking, content = result
        assert thinking is None
        assert content == "Hello from message"

    def test_message_format_whitespace_stripped(self) -> None:
        """Whitespace should be stripped from message content."""
        parser = GenericParser()
        response = {"message": {"content": "  padded content  "}}
        result = parser.parse(response)

        thinking, content = result
        assert content == "padded content"

    def test_message_format_empty_content(self) -> None:
        """Empty message content."""
        parser = GenericParser()
        response = {"message": {"content": ""}}
        result = parser.parse(response)

        thinking, content = result
        assert thinking is None
        assert content == ""


class TestGenericParserSimpleFormat:
    """Tests for GenericParser with simple response format."""

    def test_simple_response_format(self) -> None:
        """Response with 'response' field."""
        parser = GenericParser()
        response = {"response": "Simple response"}
        result = parser.parse(response)

        thinking, content = result
        assert thinking is None
        assert content == "Simple response"

    def test_simple_response_whitespace_stripped(self) -> None:
        """Whitespace should be stripped."""
        parser = GenericParser()
        response = {"response": "  trimmed  "}
        result = parser.parse(response)

        thinking, content = result
        assert content == "trimmed"


class TestGenericParserFallback:
    """Tests for GenericParser fallback behavior."""

    def test_empty_dict_returns_empty(self) -> None:
        """Empty dict should return (None, '')."""
        parser = GenericParser()
        result = parser.parse({})

        assert result == (None, "")

    def test_unknown_format_returns_empty(self) -> None:
        """Unknown response format should return (None, '')."""
        parser = GenericParser()
        response = {"data": "something else", "other_field": 123}
        result = parser.parse(response)

        assert result == (None, "")

    def test_message_not_dict_fallback(self) -> None:
        """Non-dict 'message' field should try 'response' fallback."""
        parser = GenericParser()
        response = {"message": "not a dict", "response": "fallback value"}
        result = parser.parse(response)

        thinking, content = result
        assert content == "fallback value"


# ==============================================================================
# Tests for LLMResponseParser ABC
# ==============================================================================
class TestLLMResponseParserABC:
    """Tests for the LLMResponseParser abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """LLMResponseParser should not be instantiable directly."""
        with pytest.raises(TypeError) as exc_info:
            LLMResponseParser()  # type: ignore[abstract]

        assert "abstract" in str(exc_info.value).lower()

    def test_has_abstract_parse_method(self) -> None:
        """LLMResponseParser should have abstract parse method."""
        from abc import ABC

        assert issubclass(LLMResponseParser, ABC)
        assert hasattr(LLMResponseParser, "parse")

    def test_qwen_parser_is_subclass(self) -> None:
        """QwenThinkingParser should be a subclass of LLMResponseParser."""
        assert issubclass(QwenThinkingParser, LLMResponseParser)

    def test_generic_parser_is_subclass(self) -> None:
        """GenericParser should be a subclass of LLMResponseParser."""
        assert issubclass(GenericParser, LLMResponseParser)
