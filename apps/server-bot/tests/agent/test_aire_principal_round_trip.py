"""The durable turn principal carries the persona there and back.

`agent_facts` tools scope every read and write by the persona the server binds;
that persona travels through `aire_turn_principals`. If `bind` stops writing it or
`lookup` stops reading it, every self-facts tool silently answers "no persona bound"
(2026-09-26, cross-persona agent_facts fix).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from persona_runner.engine import aire_principal
from persona_runner.mcp_tools import shared


class _Table:
    """In-memory aire_turn_principals: honours the INSERT … ON CONFLICT and the SELECT."""

    def __init__(self):
        self.rows: dict[str, dict] = {}

    async def execute(self, sql, *args):
        if sql.lstrip().upper().startswith("INSERT INTO AIRE_TURN_PRINCIPALS"):
            casita, user_id, channel_id, agent_id = args
            self.rows[casita] = {"user_id": user_id, "channel_id": channel_id, "agent_id": agent_id}
        elif sql.lstrip().upper().startswith("DELETE FROM AIRE_TURN_PRINCIPALS"):
            self.rows.pop(args[0], None)
        return "OK"

    async def fetchrow(self, sql, casita):
        assert "agent_id" in sql
        return self.rows.get(casita)


def test_bind_then_lookup_returns_the_persona(monkeypatch):
    table = _Table()

    @asynccontextmanager
    async def acquire():
        yield table

    monkeypatch.setattr(shared, "acquire", acquire)

    async def scenario():
        assert await aire_principal.bind("vultur-c1", user_id="u1", channel_id="c1", agent_id="vultur")
        got = await aire_principal.lookup("vultur-c1")
        await aire_principal.clear("vultur-c1")
        return got, await aire_principal.lookup("vultur-c1")

    got, after_clear = asyncio.run(scenario())
    assert got == aire_principal.RemotePrincipal(user_id="u1", channel_id="c1", agent_id="vultur")
    assert after_clear is None
