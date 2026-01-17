"""Response parsers for different LLM providers.

Handles provider-specific response format parsing, including separation of
thinking/reasoning from actual content.

Architecture:
- Abstract base class: LLMResponseParser
- Implementations: QwenThinkingParser, GenericParser
- Used by: OllamaProvider, ClaudeProvider, etc.

Philosophy:
- Single Responsibility: Each provider has its own parser
- Testable: Parsers can be unit-tested independently
- Reusable: Parsers can be shared across provider instances
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMResponseParser(ABC):
    """Abstract base class for parsing LLM provider responses."""

    @abstractmethod
    def parse(self, response: dict) -> tuple[str | None, str]:
        """Parse provider response into (thinking, content) tuple.

        Args:
            response: Raw response dict from LLM provider

        Returns:
            (thinking, content) where:
            - thinking: str | None - Reasoning/thought process (if available)
            - content: str - Actual response content

        Raises:
            ValueError: If response is malformed
        """
        pass


class QwenThinkingParser(LLMResponseParser):
    """Parser for Qwen3 models that output <think>...</think> blocks.

    Qwen3 models output their reasoning in XML-like tags:
        <think>reasoning here</think>actual response here

    This parser separates thinking from content using a simple state machine
    that handles nested tags safely.
    """

    def parse(self, response: dict) -> tuple[str | None, str]:
        """Parse Qwen3 response with <think>...</think> blocks.

        Args:
            response: Dict with "response" field containing full text

        Returns:
            (thinking, content) tuple

        Raises:
            ValueError: If response contains unclosed or mismatched tags
        """
        raw_text = str(response.get("response", "")).strip()

        if not raw_text:
            return None, ""

        thinking_text, content = self._parse_thinking_blocks(raw_text)
        return thinking_text, content

    @staticmethod
    def _parse_thinking_blocks(text: str) -> tuple[str | None, str]:
        """Parse <think>...</think> blocks using state machine.

        Handles nested tags safely without regex limitations.

        Args:
            text: Full response text (may include thinking blocks)

        Returns:
            (thinking, content) tuple

        Raises:
            ValueError: If tags are malformed (unclosed/mismatched)
        """
        if not text:
            return None, ""

        thinking_parts = []
        content_parts = []
        depth = 0
        current_think: list[str] = []
        i = 0

        while i < len(text):
            # Check for opening tag
            if text[i : i + 7] == "<think>":
                depth += 1
                i += 7
                continue

            # Check for closing tag
            elif text[i : i + 8] == "</think>":
                if depth == 0:
                    raise ValueError(
                        "Malformed Qwen response: closing </think> without opening <think>"
                    )
                depth -= 1
                if depth == 0:
                    # End of this thinking block
                    thinking_parts.append("".join(current_think).strip())
                    current_think = []
                i += 8
                continue

            # Accumulate character
            if depth > 0:
                current_think.append(text[i])
            else:
                content_parts.append(text[i])

            i += 1

        # Check for unclosed thinking block
        if depth > 0:
            raise ValueError(f"Malformed Qwen response: unclosed <think> tag (depth={depth})")

        # Combine thinking parts and filter empty ones
        thinking_text = None
        if thinking_parts:
            filtered_thinking = [t for t in thinking_parts if t]
            if filtered_thinking:
                thinking_text = "\n".join(filtered_thinking)

        # Get clean content
        content = "".join(content_parts).strip()

        return thinking_text, content


class GenericParser(LLMResponseParser):
    """Generic parser for providers without special thinking handling.

    Used for:
    - Claude (native thinking handled separately)
    - OpenAI (no thinking output)
    - Azure (uses OpenAI format)
    """

    def parse(self, response: dict) -> tuple[str | None, str]:
        """Parse generic provider response.

        Args:
            response: Dict with response content

        Returns:
            (None, content) - Generic parser doesn't extract thinking
        """
        # For chat endpoint format
        if "message" in response and isinstance(response["message"], dict):
            content = response["message"].get("content", "").strip()
            return None, content

        # For simple response format
        if "response" in response:
            content = str(response.get("response", "")).strip()
            return None, content

        # Fallback
        return None, ""
