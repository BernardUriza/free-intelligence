"""agent_sdk — the repo's single frontier toward any agent provider's SDK.

Nothing under `aire/` imports `claude_agent_sdk` except this package and
`store.py` (the copied Anthropic SessionStore adapter, exempt to stay diffable
upstream). Everyone else imports from here, so adding a provider is a new
backend module plus one registry row — the engine never learns its name.

Two backends live here. `claude` is the native one, Anthropic's SDK with its
own `session_store`. `acp` is ONE adapter for every agent that speaks the Agent
Client Protocol (#49) — which agents, by name, is the operator's `AIRE_ACP_AGENTS`
roster, never the wire's choice. A turn's `provider` is `"claude"` or a roster
name; `backend_for` resolves it and the engine calls the same two methods."""

from __future__ import annotations

from typing import Any

from . import acp, claude
from .acp_roster import roster
from .base import AgentBackend, AgentClient, Birth

DEFAULT_PROVIDER = "claude"

# The default backend's primitives, re-exported for the call sites that build
# options / tools / hooks. They are Anthropic's 1:1 — the modes dial and the
# registry servers are the native path's; an ACP agent brings its own.
Options = claude.Options
HookMatcher = claude.HookMatcher
mcp_server = claude.mcp_server
tool = claude.tool
project_key_for_directory = claude.project_key_for_directory

__all__ = ["SDKClient", "AgentClient", "Birth", "Options", "HookMatcher", "mcp_server",
           "tool", "project_key_for_directory", "DEFAULT_PROVIDER", "backend_for", "build_options",
           "providers", "UnknownProvider"]


class UnknownProvider(Exception):
    """A provider name with no registered backend."""


def providers() -> tuple[str, ...]:
    """Every name a turn may carry: the native backend, then the ACP roster."""
    return (DEFAULT_PROVIDER, *sorted(roster()))


def backend_for(provider: str) -> AgentBackend:
    if provider == DEFAULT_PROVIDER:
        return claude
    if provider in roster():
        return acp
    raise UnknownProvider(f"unknown provider {provider!r}; available: {list(providers())}")


def build_options(birth: Birth) -> Any:
    """The options a client is born with, built by the backend `birth.spec`
    names — the second half of the seam `SDKClient` is the first half of."""
    return backend_for(birth.spec.provider).build_options(birth)


def SDKClient(provider: str = DEFAULT_PROVIDER, *, options: Any) -> AgentClient:
    """Build a live client for `provider`. The engine passes the turn's own
    `spec.provider`; the provider string is the only thing that changes."""
    return backend_for(provider).client(options)
