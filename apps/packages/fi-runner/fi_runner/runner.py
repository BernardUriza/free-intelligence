"""Runner — composes a backend + persona + fi-core capabilities.

The runner is backend-agnostic: it resolves its declared capabilities to MCP
server specs and hands them, the persona (system prompt) and the tool policy to
whatever :class:`~fi_runner.backend.AgentBackend` it was given. Swap the backend
(Claude Code ↔ Codex ↔ raw API) without touching the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import capabilities as _capabilities
from .backend import AgentBackend, ToolPolicy, TurnResult


@dataclass
class Runner:
    """A configured runner: a backend + a persona + fi-core capabilities."""

    backend: AgentBackend
    persona: str  # the system prompt
    capabilities: list[str] = field(default_factory=list)  # e.g. ["cognitive", "persona"]
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    model: str | None = None

    async def run(self, user_message: str) -> TurnResult:
        """Run one turn through the backend with the resolved capabilities."""
        mcp_servers = _capabilities.resolve(self.capabilities)
        return await self.backend.run_turn(
            system_prompt=self.persona,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=self.tool_policy,
            model=self.model,
        )
