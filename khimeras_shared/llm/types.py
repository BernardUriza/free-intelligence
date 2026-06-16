"""Persona-neutral LLM response contract — the shared shape of a model turn.

Extracted from `personas/insult/core/{actions,llm.parsing}` (Etapa 3 demux
físico PR-1b, 2026-06-15). These types are pure data with zero behavior and zero
persona/host knowledge, so they can be the common vocabulary the runner transport
(`khimeras_shared.runner.agent_client`), the Insult parsing layer, and the audit
code all speak — without any consumer importing another's internals.

Design rule (per the coagent): shared defines SHAPE, not identity or behavior.
The cache-boundary policy, persona-specific parsing and tool execution stay in
the persona/host; only the response shape lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A tool_use block from the Claude API response."""

    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    """Structured response from the LLM — text + optional tool calls."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model_used: str = ""  # populated by chat() — reflects the model that actually produced the text
    stop_reason: str = ""  # raw API stop_reason; "max_tokens" / "end_turn" / "tool_use" / "pause_turn"
