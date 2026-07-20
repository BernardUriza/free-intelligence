"""The Engine facade: owner of the SDK, the modes and the memory. One live
`ClaudeSDKClient` per session (pool = hot cache); a miss is rebuilt from the
store with `resume=`, which is what makes the memory survive a restart."""

import asyncio
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, project_key_for_directory

from ..keys import sdk_session_uuid
from .contract import BudgetExceeded
from .drain import drain
from .options import DEFAULT_MODE, build_options
from .pool import Pool

WORKSPACES = Path(__file__).resolve().parent.parent.parent / "workspaces"
# The SDK's max_budget_usd caps ONE turn. AIRE_MAX_SPEND_USD is a cumulative
# backstop over the process lifetime — when crossed, turns are refused BEFORE
# they reach the API. Unset → no ceiling (dev). Resets on restart.
MAX_SPEND_USD = float(os.environ["AIRE_MAX_SPEND_USD"]) if os.environ.get("AIRE_MAX_SPEND_USD") else None


class Engine:
    def __init__(self, session_store: Any) -> None:
        self.session_store = session_store
        self.pool = Pool()
        self._spend_usd = 0.0  # cumulative, process lifetime — the global backstop

    def _cwd(self, project: str) -> Path:
        ws = WORKSPACES / project
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def session_key(self, project: str, session: str) -> dict[str, str]:
        """The store key. `project_key` is NOT invented: the SDK derives it from
        the cwd when it WRITES, so the reader must derive it the same way."""
        return {"project_key": project_key_for_directory(str(self._cwd(project))),
                "session_id": sdk_session_uuid(session)}

    async def has_session(self, project: str, session: str) -> bool:
        return bool(await self.session_store.load(self.session_key(project, session)))

    async def _client_for(self, project: str, session: str, mode: str) -> tuple[Any, asyncio.Lock]:
        key = f"{project}/{session}"
        async with self.pool.guard:
            now = time.monotonic()
            await self.pool.evict(now)
            client = self.pool.clients.get(key)
            if client is None:
                resuming = await self.has_session(project, session)
                options = build_options(self.session_store, project,
                                        str(self._cwd(project)),
                                        sdk_session_uuid(session), mode, resuming)
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self.pool.clients[key] = client
            self.pool.used[key] = now
            lock = self.pool.locks.setdefault(key, asyncio.Lock())
        return client, lock

    async def run_stream(self, project: str, session: str, prompt: str,
                         mode: str = DEFAULT_MODE) -> AsyncIterator[dict[str, Any]]:
        """One turn, live. The transcript mirrors itself to Postgres — the
        agent's memory AND the page's memory are THE SAME transcript."""
        if MAX_SPEND_USD is not None and self._spend_usd >= MAX_SPEND_USD:
            raise BudgetExceeded(
                f"cumulative spend ${self._spend_usd:.2f} >= ceiling ${MAX_SPEND_USD:.2f}")
        client, lock = await self._client_for(project, session, mode)
        async with lock:  # serializes turns on the same client (not concurrency-safe)
            await client.query(prompt)
            async for event in drain(client):
                if event.get("type") == "result":
                    usage = getattr(event.get("result"), "usage", None) or {}
                    cost = usage.get("total_cost_usd") if isinstance(usage, dict) else None
                    if cost:
                        self._spend_usd += float(cost)
                yield event

    async def load_transcript(self, project: str, session: str) -> list[dict[str, Any]]:
        """What the agent remembers — lives in Postgres, not the HTTP connection."""
        return await self.session_store.load(self.session_key(project, session)) or []

    async def aclose(self) -> None:
        async with self.pool.guard:
            await self.pool.close_all()
