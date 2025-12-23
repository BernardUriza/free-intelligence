"""
Unit tests for Qwen3 thinking block parser.

Tests the parse_qwen_thinking_and_response() function from backend/providers/llm.py
to ensure proper separation of reasoning blocks from response content.
"""

import pytest
from backend.providers.llm import parse_qwen_thinking_and_response


class TestQwenThinkingParser:
    """Test suite for Qwen3 thinking block parsing."""

    # ========================================================================
    # BASIC CASES - Standard Qwen3 output format
    # ========================================================================

    def test_basic_thinking_and_response(self):
        """Standard case: thinking block followed by response content."""
        input_text = "<think>Let me think about this problem</think>The answer is 42"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == "Let me think about this problem"
        assert content == "The answer is 42"

    def test_multiline_thinking(self):
        """Thinking block with multiple lines of reasoning."""
        input_text = (
            "<think>Step 1: Analyze the problem\n"
            "Step 2: Consider options\n"
            "Step 3: Choose best approach</think>"
            "Here's my recommendation"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "Step 1: Analyze" in thinking
        assert "Step 3: Choose" in thinking
        assert content == "Here's my recommendation"

    def test_thinking_with_xml_like_content(self):
        """Thinking block may contain angle brackets that aren't tags."""
        input_text = (
            "<think>Compare A > B and C < D</think>"
            "A is greater than B"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "A > B" in thinking
        assert "C < D" in thinking
        assert content == "A is greater than B"

    # ========================================================================
    # MULTIPLE THINKING BLOCKS
    # ========================================================================

    def test_multiple_thinking_blocks(self):
        """Response with multiple separate thinking sections."""
        input_text = (
            "<think>First thought</think>"
            "Intermediate text "
            "<think>Second thought</think>"
            "Final response"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert thinking == "First thought\nSecond thought"
        assert content == "Intermediate text Final response"

    def test_multiple_blocks_with_complex_content(self):
        """Multiple thinking blocks with complex reasoning between them."""
        input_text = (
            "<think>Analyze the problem</think>\n"
            "First step: X\n"
            "<think>Verify intermediate result</think>\n"
            "Second step: Y\n"
            "<think>Draw conclusion</think>\n"
            "Final answer: Z"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        # All thinking blocks concatenated
        assert "Analyze the problem" in thinking
        assert "Verify intermediate" in thinking
        assert "Draw conclusion" in thinking

        # All content blocks preserved
        assert "First step: X" in content
        assert "Second step: Y" in content
        assert "Final answer: Z" in content

    # ========================================================================
    # EDGE CASES - Whitespace and empty blocks
    # ========================================================================

    def test_empty_thinking_block(self):
        """Empty thinking block should return None for thinking."""
        input_text = "<think></think>Just the response"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking is None
        assert content == "Just the response"

    def test_whitespace_only_thinking(self):
        """Thinking block with only whitespace should be treated as empty."""
        input_text = "<think>   \n\n   </think>Response content"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking is None
        assert content == "Response content"

    def test_whitespace_around_content(self):
        """Proper trimming of whitespace around thinking and content."""
        input_text = (
            "  <think>  Reasoning with padding  </think>  "
            "  Content with padding  "
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        # Inner whitespace preserved, outer trimmed
        assert thinking == "Reasoning with padding"
        assert content == "Content with padding"

    def test_newlines_preserved_in_thinking(self):
        """Newlines within thinking blocks should be preserved."""
        input_text = (
            "<think>Line 1\n"
            "Line 2\n"
            "Line 3</think>"
            "Final response"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "Line 1\nLine 2\nLine 3" in thinking
        assert content == "Final response"

    # ========================================================================
    # NO THINKING BLOCKS
    # ========================================================================

    def test_no_thinking_block(self):
        """Response with no thinking tags."""
        input_text = "This is just a plain response without any thinking"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking is None
        assert content == "This is just a plain response without any thinking"

    def test_response_only_at_start(self):
        """Content before any thinking tag (malformed input)."""
        input_text = "Some content <think>thinking</think>More content"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == "thinking"
        assert content == "Some content More content"

    def test_thinking_at_end(self):
        """Thinking block at the very end of response."""
        input_text = "Response content<think>trailing thinking</think>"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == "trailing thinking"
        assert content == "Response content"

    # ========================================================================
    # EMPTY AND NULL INPUTS
    # ========================================================================

    def test_empty_string(self):
        """Empty input should return None thinking and empty content."""
        thinking, content = parse_qwen_thinking_and_response("")

        assert thinking is None
        assert content == ""

    def test_none_handling(self):
        """Function should not crash on None input (defensive)."""
        # Note: Current implementation expects string, but test defensive handling
        thinking, content = parse_qwen_thinking_and_response("")
        assert thinking is None
        assert content == ""

    # ========================================================================
    # REAL-WORLD EXAMPLES FROM OLLAMA/QWEN3
    # ========================================================================

    def test_arithmetic_problem(self):
        """Real-world example: Qwen3 solving arithmetic."""
        input_text = (
            "<think>I need to calculate 2 + 2.\n"
            "2 + 2 = 4\n"
            "This is a basic arithmetic operation.</think>\n"
            "The answer to 2 + 2 is 4."
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "calculate 2 + 2" in thinking
        assert content == "The answer to 2 + 2 is 4."

    def test_code_explanation(self):
        """Real-world example: Code review with thinking."""
        input_text = (
            "<think>The user is asking me to review Python code.\n"
            "Looking at the function, it appears to be a simple loop.\n"
            "The logic seems correct for iteration.</think>\n"
            "```python\ndef example():\n    for i in range(10):\n        print(i)\n```\n"
            "This code correctly iterates from 0 to 9."
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "asking me to review" in thinking
        assert "```python" in content
        assert "iterates from 0 to 9" in content

    def test_long_reasoning(self):
        """Real-world example: Complex reasoning with long thinking."""
        reasoning = "\n".join(
            [
                "Step 1: Understand the requirements",
                "Step 2: Identify edge cases",
                "Step 3: Plan the solution",
                "Step 4: Write pseudocode",
                "Step 5: Implement in Python",
            ]
        )
        input_text = f"<think>{reasoning}</think>\nHere is my solution..."
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "Step 1" in thinking
        assert "Step 5" in thinking
        assert content == "Here is my solution..."

    # ========================================================================
    # BOUNDARY CONDITIONS
    # ========================================================================

    def test_thinking_tag_in_content(self):
        """Edge case: content mentions 'think' as a word."""
        input_text = (
            "<think>Reasoning</think>"
            "Let me think about this some more."
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == "Reasoning"
        # The word "think" in content is preserved
        assert "think about this" in content

    def test_html_entities_in_thinking(self):
        """Thinking block may contain HTML entities."""
        input_text = (
            "<think>Consider A &amp; B, also X &lt; Y</think>"
            "Response with entities: A &amp; B"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert "&amp;" in thinking
        assert "&lt;" in thinking
        assert content == "Response with entities: A &amp; B"

    def test_very_long_thinking(self):
        """Performance test: very long thinking block."""
        long_thinking = "x" * 10000  # 10K character thinking
        input_text = f"<think>{long_thinking}</think>Short response"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert len(thinking) == 10000
        assert content == "Short response"

    def test_very_long_response(self):
        """Performance test: very long response content."""
        thinking_text = "thinking"
        long_response = "y" * 10000  # 10K character response
        input_text = f"<think>{thinking_text}</think>{long_response}"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == thinking_text
        assert len(content) == 10000

    # ========================================================================
    # ERROR CASES / MALFORMED INPUT
    # ========================================================================

    def test_unclosed_thinking_tag(self):
        """Unclosed <think> tag - should still parse remaining content."""
        input_text = "<think>Unclosed thinking blockResponse text"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        # Regex won't match - entire thing is content
        assert thinking is None
        assert content == "<think>Unclosed thinking blockResponse text"

    def test_unopened_closing_tag(self):
        """Closing tag without opening - should be treated as text."""
        input_text = "Response text</think>"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking is None
        assert content == "Response text</think>"

    def test_mismatched_case(self):
        """Tags with different case (<Think> instead of <think>)."""
        input_text = "<Think>Different case</Think>Response"
        thinking, content = parse_qwen_thinking_and_response(input_text)

        # Case-sensitive regex won't match
        assert thinking is None
        assert content == "<Think>Different case</Think>Response"

    def test_html_comment_like_content(self):
        """Content that looks like HTML comments but isn't."""
        input_text = (
            "<think>Thinking</think>"
            "<!-- This is not a comment in the parsing logic -->"
        )
        thinking, content = parse_qwen_thinking_and_response(input_text)

        assert thinking == "Thinking"
        assert "<!-- This is not a comment" in content


# ============================================================================
# PARAMETRIZED TESTS - Testing multiple cases systematically
# ============================================================================


@pytest.mark.parametrize(
    "input_text,expected_thinking,expected_content",
    [
        # (input, thinking, content)
        ("<think>A</think>B", "A", "B"),
        ("<think>A</think>", "A", ""),
        ("<think></think>B", None, "B"),
        ("B", None, "B"),
        ("<think>A</think><think>B</think>C", "A\nB", "C"),
        ("<think>  \n  </think>Response", None, "Response"),
        ("Text<think>Thought</think>More", "Thought", "TextMore"),
    ],
)
def test_parametrized_parsing(input_text, expected_thinking, expected_content):
    """Systematic test of common parsing patterns."""
    thinking, content = parse_qwen_thinking_and_response(input_text)
    assert thinking == expected_thinking
    assert content == expected_content


# ============================================================================
# INTEGRATION-LIKE TESTS - Simulating Ollama response structures
# ============================================================================


class TestOllamaResponseIntegration:
    """Tests simulating actual Ollama /generate endpoint responses."""

    def test_ollama_generate_response_structure(self):
        """Simulate Ollama /generate API response with thinking."""
        # This is what llm_provider.py receives from Ollama
        raw_response_text = (
            "<think>The user is asking for the capital of France.\n"
            "I know that Paris is the capital of France.</think>\n"
            "The capital of France is Paris."
        )

        thinking, content = parse_qwen_thinking_and_response(raw_response_text)

        assert "capital of France" in thinking
        assert content == "The capital of France is Paris."

    def test_ollama_streaming_chunk(self):
        """Simulate receiving chunks from Ollama streaming."""
        # In streaming, we get complete response at once
        full_response = (
            "<think>Processing user question...</think>"
            "Here is the answer in chunks"
        )
        thinking, content = parse_qwen_thinking_and_response(full_response)

        assert thinking == "Processing user question..."
        assert content == "Here is the answer in chunks"

    def test_qwen3_model_specific_output(self):
        """Qwen3-specific reasoning format."""
        qwen_output = (
            "<think>\n"
            "分析问题:\n"  # Chinese characters in thinking
            "1. 理解需求\n"
            "2. 规划方案\n"
            "</think>\n"
            "解决方案如下:\n"  # Response in Chinese
            "..."
        )
        thinking, content = parse_qwen_thinking_and_response(qwen_output)

        assert "理解需求" in thinking
        assert "解决方案" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
