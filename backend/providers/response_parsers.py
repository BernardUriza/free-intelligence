"""Response parsers for different LLM providers.

Handles provider-specific response format parsing, including separation of
thinking/reasoning from actual content.

Architecture:
- Abstract base class: LLMResponseParser
- Implementations: QwenThinkingParser, GenericParser
- Used by: OllamaProvider

Philosophy:
- Single Responsibility: Each provider has its own parser
- Testable: Parsers can be unit-tested independently
- Reusable: Parsers can be shared across provider instances
"""

from abc import ABC, abstractmethod


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

        thinking_text, content = self.parse_thinking_blocks(raw_text)
        return thinking_text, content

    @staticmethod
    def parse_thinking_blocks(text: str, strict: bool = True) -> tuple[str | None, str]:
        """Parse <think>...</think> blocks using state machine.

        Handles nested tags safely without regex limitations.

        Args:
            text: Full response text (may include thinking blocks)
            strict: If True, raises ValueError on malformed tags.
                    If False, silently discards malformed content (for sanitization).

        Returns:
            (thinking, content) tuple

        Raises:
            ValueError: If strict=True and tags are malformed (unclosed/mismatched)
        """
        if not text:
            return None, ""

        thinking_parts = []
        content_parts = []
        depth = 0
        current_think: list[str] = []
        i = 0
        text_lower = text.lower()

        while i < len(text):
            # Check for opening tag (case-insensitive, with optional spaces)
            if text_lower[i : i + 7] == "<think>" or (
                text_lower[i : i + 6] == "<think" and i + 6 < len(text) and text[i + 6] in " >"
            ):
                # Find the end of the opening tag
                end = text.find(">", i)
                if end == -1:
                    if strict:
                        raise ValueError("Malformed Qwen response: unclosed opening tag")
                    # Non-strict: skip the malformed tag start
                    content_parts.append(text[i])
                    i += 1
                    continue
                depth += 1
                i = end + 1
                continue

            # Check for closing tag (case-insensitive, with optional spaces)
            if text_lower[i : i + 8] == "</think>" or (
                text_lower[i : i + 7] == "</think" and i + 7 < len(text) and text[i + 7] in " >"
            ):
                # Find the end of the closing tag
                end = text.find(">", i)
                if end == -1:
                    if strict:
                        raise ValueError("Malformed Qwen response: unclosed closing tag")
                    content_parts.append(text[i])
                    i += 1
                    continue

                if depth == 0:
                    if strict:
                        raise ValueError(
                            "Malformed Qwen response: closing </think> without opening <think>"
                        )
                    # Non-strict: skip the orphan closing tag
                    i = end + 1
                    continue

                depth -= 1
                if depth == 0:
                    # End of this thinking block
                    thinking_parts.append("".join(current_think).strip())
                    current_think = []
                i = end + 1
                continue

            # Accumulate character
            if depth > 0:
                current_think.append(text[i])
            else:
                content_parts.append(text[i])

            i += 1

        # Handle unclosed thinking block
        if depth > 0:
            if strict:
                raise ValueError(f"Malformed Qwen response: unclosed <think> tag (depth={depth})")
            # Non-strict: discard unclosed thinking content (don't leak it)

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
    - Ollama chat with think=False (defensive sanitization)
    """

    def parse(self, response: dict) -> tuple[str | None, str]:
        """Parse generic provider response.

        Args:
            response: Dict with response content

        Returns:
            (None, content) - Generic parser doesn't extract thinking

        Note:
            Defensive sanitization: Qwen3 models may leak <think> tags even with
            think=False. Uses the same state machine as QwenThinkingParser but in
            non-strict mode to silently discard leaked tags without raising errors.
        """
        content = ""

        # For chat endpoint format
        if "message" in response and isinstance(response["message"], dict):
            content = response["message"].get("content", "").strip()
        # For simple response format
        elif "response" in response:
            content = str(response.get("response", "")).strip()

        # Defensive sanitization: use state machine (not regex) for robustness
        # Handles: nested tags, case variations, spaces in tags, malformed tags
        if content and ("think>" in content.lower() or "<think" in content.lower()):
            # Use QwenThinkingParser's state machine in non-strict mode
            # This discards thinking content without raising errors
            _, content = QwenThinkingParser.parse_thinking_blocks(content, strict=False)

        return None, content
