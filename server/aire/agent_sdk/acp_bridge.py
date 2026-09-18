"""The Client half of an ACP connection: the agent's notifications come in
here, and its permission questions are answered here.

Two rules make it safe to put behind AIRE's engine. Updates are only FORWARDED
while a prompt is in flight (`armed`): `session/load` replays the whole history
as the same notifications, and forwarding those would hand drain a turn nobody
asked for. And the daemon lends the agent no filesystem and no terminal of its
own — it advertises neither capability, so the agent must not ask; if one does,
the refusal is a JSON-RPC error, not a file written where nobody looked."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from acp import RequestError, schema

from .acp_messages import translate

Mirror = Callable[[str, dict[str, Any]], Awaitable[None]]


class Bridge:
    def __init__(self, agent: str, allow_tools: bool, mirror: Mirror) -> None:
        self.agent, self.allow_tools, self.mirror = agent, allow_tools, mirror
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.armed = False
        self.cost: float | None = None

    async def session_update(self, session_id: str, update: Any, **_: Any) -> None:
        if not self.armed:
            return
        kind = type(update).__name__
        await self.mirror(kind, update.model_dump(mode="json", exclude_none=True))
        if kind == "UsageUpdate" and getattr(update, "cost", None) is not None:
            self.cost = float(update.cost.amount)
        for message in translate(update, self.agent):
            await self.queue.put(message)

    async def request_permission(self, session_id: str, tool_call: Any,
                                 options: list[Any], **_: Any) -> schema.RequestPermissionResponse:
        """`agent` mode allows once, `complete` mode rejects: the modes dial
        (engine/options.py) is the caller's contract and an ACP agent honours it
        through the only gate the protocol gives — this one."""
        want = "allow_once" if self.allow_tools else "reject_once"
        pick = next((o for o in options if o.kind == want), None)
        if pick is None:
            return schema.RequestPermissionResponse(outcome=schema.DeniedOutcome(outcome="cancelled"))
        return schema.RequestPermissionResponse(
            outcome=schema.AllowedOutcome(option_id=pick.option_id, outcome="selected"))

    def on_connect(self, *_: Any, **__: Any) -> None:
        return None  # called synchronously by the connection, never awaited

    async def ext_notification(self, *_: Any, **__: Any) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        """Every other Client method (fs, terminal, elicitation, ext_method):
        not lent. Answered with the protocol's own "not supported"."""
        if name.startswith("_"):
            raise AttributeError(name)

        async def refuse(*_: Any, **__: Any) -> Any:
            raise RequestError.method_not_found(name)
        return refuse
