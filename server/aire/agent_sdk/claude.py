"""The Anthropic backend — the ONE place the repo imports `claude_agent_sdk`
(store.py excepted: it IS Anthropic's copied SessionStore adapter, kept diffable
upstream). Every symbol the engine used to reach for directly is re-exposed here
under a provider-neutral name, so a second backend is a sibling file, not a
thread pulled through nine call sites."""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    create_sdk_mcp_server,
    project_key_for_directory,
    tool,
)

Options = ClaudeAgentOptions
mcp_server = create_sdk_mcp_server

__all__ = ["Options", "HookMatcher", "mcp_server", "tool",
           "project_key_for_directory", "client"]


def client(options: Any) -> ClaudeSDKClient:
    """A live client for one session. The engine enters it as a context manager
    (the subprocess spawns on `__aenter__`) — construction alone spawns nothing."""
    return ClaudeSDKClient(options=options)
