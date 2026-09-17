"""The provider-agnostic contract — what the engine consumes from ANY backend's
client, named once so a second provider can only be added, never threaded back
through the engine. Verified against the real call sites: core builds it and
enters it as a context manager, vision drives `query`, drain reads
`receive_response`, pool exits it."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AgentClient(Protocol):
    """One live agent session — a subprocess behind Anthropic's client today,
    whatever a future backend spawns tomorrow. The engine holds it in the pool
    (hot cache) and rebuilds it from the store on a miss, so nothing here owns
    memory: it owns the turn."""

    async def __aenter__(self) -> "AgentClient": ...

    async def __aexit__(self, *exc: Any) -> Any: ...

    async def query(self, payload: Any) -> None:
        """Send the turn's user message — a plain string, or the streaming-input
        async iterable an image turn needs."""
        ...

    def receive_response(self) -> AsyncIterator[Any]:
        """Yield the turn's messages as they stream, until the result closes it."""
        ...


class AgentBackend(Protocol):
    """A provider's whole surface: the client factory plus the option/tool/hook
    primitives its clients understand. Everything the repo used to import from a
    vendor SDK lives behind ONE of these."""

    Options: Any
    HookMatcher: Any
    mcp_server: Any
    tool: Any
    project_key_for_directory: Any

    def client(self, options: Any) -> AgentClient: ...
