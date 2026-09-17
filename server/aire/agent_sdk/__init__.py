"""agent_sdk — the repo's single frontier toward any agent provider's SDK.

Nothing under `aire/` imports `claude_agent_sdk` except this package and
`store.py` (the copied Anthropic SessionStore adapter, exempt to stay diffable
upstream). Everyone else imports from here, so adding a provider is a new
backend module plus one registry row — the engine never learns its name.

Today there is one backend, so the re-exported primitives (`Options`, `tool`,
`mcp_server`, `HookMatcher`, `project_key_for_directory`) are Anthropic's 1:1.
The win is not indirection for its own sake: it is that `SDKClient("gpt", …)`
becomes reachable by writing `gpt.py`, touching zero call sites."""

from __future__ import annotations

from typing import Any

from . import claude
from .base import AgentBackend, AgentClient

#: provider name → its backend module. A second provider registers here.
_BACKENDS: dict[str, AgentBackend] = {"claude": claude}

DEFAULT_PROVIDER = "claude"

# The default backend's primitives, re-exported for the call sites that build
# options / tools / hooks. When a turn's provider becomes a variable, each of
# these moves to a `backend_for(provider).<name>` lookup — the seam is already here.
Options = claude.Options
HookMatcher = claude.HookMatcher
mcp_server = claude.mcp_server
tool = claude.tool
project_key_for_directory = claude.project_key_for_directory

__all__ = ["SDKClient", "AgentClient", "Options", "HookMatcher", "mcp_server",
           "tool", "project_key_for_directory", "DEFAULT_PROVIDER"]


class UnknownProvider(Exception):
    """A provider name with no registered backend."""


def backend_for(provider: str) -> AgentBackend:
    try:
        return _BACKENDS[provider]
    except KeyError as exc:
        raise UnknownProvider(
            f"unknown provider {provider!r}; available: {sorted(_BACKENDS)}") from exc


def SDKClient(provider: str = DEFAULT_PROVIDER, *, options: Any) -> AgentClient:
    """Build a live client for `provider`. The engine calls
    `SDKClient("claude", options=options)`; the provider string is the only
    thing that changes the day a second backend lands."""
    return backend_for(provider).client(options)
