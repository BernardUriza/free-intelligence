"""Contract tests for runner-era LLM plumbing shapes.

The direct-Anthropic client (web_search server tool, _parse_response_content,
CACHE_BOUNDARY system-block splitting) died with the agent-runner cutover —
its tests died with it. What remains locks in the contract the runner path
still depends on:

- LLMResponse.stop_reason default (khimeras_shared.llm.types, re-exported
  through personas.insult.core.llm)
"""

from __future__ import annotations

from personas.insult.core.llm import LLMResponse


class TestLLMResponseStopReason:
    def test_default_stop_reason_is_empty_string(self):
        """Callers should be able to read .stop_reason without it being
        unset / None — the runner clients populate it. The default ""
        makes truncation checks like
        `if response.stop_reason == 'max_tokens'` safe to write without
        a None guard."""
        r = LLMResponse(text="hello")
        assert r.stop_reason == ""

    def test_stop_reason_field_is_settable(self):
        """LLMResponse is a dataclass — stop_reason must be assignable
        post-construction (that's how the runner clients populate it)."""
        r = LLMResponse(text="x")
        r.stop_reason = "max_tokens"
        assert r.stop_reason == "max_tokens"
