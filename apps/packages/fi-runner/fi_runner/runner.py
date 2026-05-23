"""Runner — composes a backend + persona + fi-core capabilities.

The runner is backend-agnostic: it resolves its declared capabilities to MCP
server specs and hands them, the persona (system prompt) and the tool policy to
whatever :class:`~fi_runner.backend.AgentBackend` it was given. Swap the backend
(Claude Code ↔ Codex ↔ raw API) without touching the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import capabilities as _capabilities
from .backend import AgentBackend, MCPServerSpec, ToolPolicy, TurnResult


@dataclass
class Runner:
    """A configured runner: a backend + a persona + fi-core capabilities."""

    backend: AgentBackend
    persona: str  # the system prompt
    capabilities: list[str] = field(default_factory=list)  # fi-core, e.g. ["cognitive", "persona"]
    # Runner-specific MCP servers not in fi-core (e.g. insult's insult_db, playwright).
    extra_mcp_servers: list[MCPServerSpec] = field(default_factory=list)
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    model: str | None = None

    async def run(self, user_message: str, *, session_id: str | None = None) -> TurnResult:
        """Run one turn: fi-core capabilities + extra MCP servers, through the backend.

        Pass ``session_id`` (e.g. a Discord channel id) for conversation
        continuity on backends that support stateful sessions.
        """
        mcp_servers = _capabilities.resolve(self.capabilities) + list(self.extra_mcp_servers)
        return await self.backend.run_turn(
            system_prompt=self.persona,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=self.tool_policy,
            model=self.model,
            session_id=session_id,
        )

    async def aclose(self) -> None:
        """Release backend resources (pooled sessions, etc.), if any."""
        close = getattr(self.backend, "aclose", None)
        if close is not None:
            await close()
