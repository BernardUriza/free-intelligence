"""The provider-agnostic contract — what the engine consumes from ANY backend's
client, named once so a second provider can only be added, never threaded back
through the engine. Verified against the real call sites: core builds it and
enters it as a context manager, vision drives `query`, drain reads
`receive_response`, pool exits it."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Birth:
    """Everything a backend needs to build the options a client is BORN with —
    the engine hands this over and never learns what the backend makes of it.
    `spec` is the turn's `TurnSpec`; `resuming` says the memory already holds
    this session; `credential_env` is the rotor's active slot (#31)."""

    session_store: Any
    project: str
    cwd: str
    session_uuid: str
    spec: Any
    resuming: bool
    credential_env: dict[str, str] | None = None
    metered: bool = True


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
    """A provider's whole surface: the client factory, the options it is born
    with, plus the option/tool/hook primitives its clients understand.
    Everything the repo used to import from a vendor SDK lives behind ONE of
    these."""

    def client(self, options: Any) -> AgentClient: ...

    def build_options(self, birth: Birth) -> Any: ...
