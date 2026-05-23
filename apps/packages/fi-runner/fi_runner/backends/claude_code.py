"""ClaudeCodeBackend — wraps the Claude Agent SDK (a.k.a. Claude Code).

Runs on a Claude Pro/Max subscription via OAuth (or an API key), brings the
full Claude Code toolset (Bash/Read/Write/Edit/…) gated by the ToolPolicy, and
has the deepest MCP integration. The turn loop mirrors the proven pattern in
the insult runner (``type(message).__name__`` checks for resilience across SDK
versions).

Requires the ``claude`` extra::

    pip install 'fi-runner[claude]'
"""

from __future__ import annotations

import os

from ..backend import MCPServerSpec, ToolPolicy, TurnResult


class ClaudeCodeBackend:
    """Agent backend backed by the Claude Agent SDK (Claude Code)."""

    def __init__(self, default_model: str | None = None) -> None:
        self.default_model = default_model

    def _allowlist(self, mcp_servers: list[MCPServerSpec], tool_policy: ToolPolicy) -> list[str]:
        allowed = list(tool_policy.builtin_allowed)
        for spec in mcp_servers:
            if spec.tools:
                allowed.extend(f"mcp__{spec.name}__{tool}" for tool in spec.tools)
            else:
                allowed.append(f"mcp__{spec.name}")
        return allowed

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
    ) -> TurnResult:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ClaudeCodeBackend requires the Claude Agent SDK. "
                "Install via: pip install 'fi-runner[claude]'"
            ) from exc

        mcp = {
            spec.name: {
                "command": spec.command,
                "args": spec.args,
                **({"env": dict(os.environ)} if spec.env_passthrough else {}),
            }
            for spec in mcp_servers
        }

        chosen_model = model or self.default_model
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            mcp_servers=mcp,
            allowed_tools=self._allowlist(mcp_servers, tool_policy),
            disallowed_tools=list(tool_policy.builtin_disallowed),
            permission_mode=tool_policy.permission_mode.value,
            **({"model": chosen_model} if chosen_model else {}),
        )

        parts: list[str] = []
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_message)
            async for message in client.receive_response():
                if type(message).__name__ == "AssistantMessage":
                    for block in getattr(message, "content", []) or []:
                        if type(block).__name__ == "TextBlock":
                            parts.append(getattr(block, "text", ""))
        return TurnResult(text="".join(parts))
