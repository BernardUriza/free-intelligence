"""CodexBackend — wraps OpenAI Codex (codex exec / openai_codex SDK). SKELETON (v2).

Codex runs headless via ``codex exec --json`` (emits JSONL events) or the Python
``openai_codex`` SDK. Like Claude Code it brings file-edit + shell (sandboxed)
+ MCP. To implement: spawn ``codex exec --json`` (or use the SDK), pass the
system prompt + user message, parse the JSONL stream for the final assistant
text, and map :class:`ToolPolicy` to Codex's sandbox / approval flags.

Requires the ``codex`` extra::

    pip install 'fi-runner[codex]'
"""

from __future__ import annotations

from ..backend import MCPServerSpec, ToolPolicy, TurnResult


class CodexBackend:
    """Agent backend backed by OpenAI Codex (headless exec / SDK). Not yet implemented."""

    def __init__(self, default_model: str | None = None) -> None:
        self.default_model = default_model

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
    ) -> TurnResult:
        raise NotImplementedError(
            "CodexBackend is a v2 skeleton. Implement via `codex exec --json` "
            "or the openai_codex SDK (pip install 'fi-runner[codex]'). The port "
            "contract is identical to ClaudeCodeBackend."
        )
