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
from .detach import Detached
from .drain import drain
from .options import DEFAULT_MODE, build_options
from .pool import Pool

WORKSPACES = Path(os.environ.get(
    "AIRE_WORKSPACES", Path(__file__).resolve().parent.parent.parent / "workspaces"))
# max_budget_usd caps the CLIENT's cumulative spend, not one turn (measured; a
# poisoned client is retired, backlog #23). AIRE_MAX_SPEND_USD is this engine's
# own process-lifetime backstop — turns refused BEFORE the API. Resets on restart.
MAX_SPEND_USD = float(os.environ["AIRE_MAX_SPEND_USD"]) if os.environ.get("AIRE_MAX_SPEND_USD") else None
# The same ceiling given to the SDK, kept to RECOGNISE a cut turn (#23).
TURN_CAP_USD = float(os.environ["AIRE_MAX_BUDGET_USD"]) if os.environ.get("AIRE_MAX_BUDGET_USD") else None


def turn_cost(event: dict[str, Any]) -> float:
    usage = getattr(event.get("result"), "usage", None) or {}
    cost = usage.get("total_cost_usd") if isinstance(usage, dict) else None
    return float(cost) if cost else 0.0


class Engine:
    def __init__(self, session_store: Any) -> None:
        self.session_store = session_store
        self.pool = Pool()
        self._spend_usd = 0.0  # cumulative, process lifetime — the global backstop
        self._seen_cost: dict[str, float] = {}  # per-client last acc cost, for the delta
        self.detached = Detached()  # fire-and-forget background turns (#22a)

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
                await self.pool.make_space()  # close LRU idle so we stay <= POOL_MAX
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
        """One turn, live (transcript mirrors to Postgres). The RAM slot
        (backpressure) is held for the whole turn: a 3rd device queues."""
        if MAX_SPEND_USD is not None and self._spend_usd >= MAX_SPEND_USD:
            raise BudgetExceeded(
                f"cumulative spend ${self._spend_usd:.2f} >= ceiling ${MAX_SPEND_USD:.2f}")
        async with self.pool.slot():
            async for event in self._turn(project, session, prompt, mode):
                yield event

    async def _turn(self, project: str, session: str, prompt: str,
                    mode: str) -> AsyncIterator[dict[str, Any]]:
        key = f"{project}/{session}"
        client, lock = await self._client_for(project, session, mode)
        spent = False
        try:
            async with lock:  # serializes turns on the same client (not concurrency-safe)
                await client.query(prompt)
                async for event in drain(client):
                    if event.get("type") == "result":
                        spent = self._account(key, turn_cost(event))
                    yield event
                if spent:
                    yield {"type": "error", "error": "budget_exhausted",
                           "detail": f"the turn reached the ${TURN_CAP_USD:.2f} ceiling and was "
                                     "CUT — its work may be incomplete. The spent client is "
                                     "retired; send the turn again to continue."}
        finally:
            if spent:
                await self._retire(project, session)

    def _account(self, key: str, cost: float) -> bool:
        """Bank this turn's spend and report whether the client hit the ceiling.
        `total_cost_usd` is the CLIENT's cumulative spend (measured 2026-07-20),
        so the backstop adds the DELTA — else N turns N-count the same dollars."""
        self._spend_usd += max(0.0, cost - self._seen_cost.get(key, 0.0))
        self._seen_cost[key] = cost
        return TURN_CAP_USD is not None and cost >= TURN_CAP_USD

    def launch_detached(self, project: str, session: str, prompt: str, mode: str) -> None:
        """Run the turn fire-and-forget (#22a): decoupled from the request, it
        finishes even if the caller hangs up. Raises if one already runs here."""
        self.detached.launch(
            f"{project}/{session}",
            lambda: self._drain_detached(project, session, prompt, mode))

    async def _drain_detached(self, project: str, session: str, prompt: str, mode: str) -> None:
        try:
            async for ev in self.run_stream(project, session, prompt, mode):
                # No client listens in background — surface an error (a budget cut).
                if ev.get("type") == "error":
                    print(f"DETACHED {project}/{session} {ev.get('error')}: {ev.get('detail', '')}")
        except Exception as exc:  # noqa: BLE001 — no client to tell; log for the operator
            print(f"DETACHED {project}/{session} failed: {type(exc).__name__}: {exc}")

    async def _retire(self, project: str, session: str) -> None:
        """A client that reached max_budget_usd is POISONED: the SDK refuses every
        later turn on it with an empty result and no error. Dropping it is the
        cure — the pool is a cache, so the next turn rebuilds from the store with
        `resume=` and the memory is untouched ([[log-is-the-truth]])."""
        key = f"{project}/{session}"
        self._seen_cost.pop(key, None)  # its spend is banked; the reborn client starts at 0
        async with self.pool.guard:
            await self.pool.close_one(key)

    async def load_transcript(self, project: str, session: str) -> list[dict[str, Any]]:
        """What the agent remembers — lives in Postgres, not the HTTP connection."""
        return await self.session_store.load(self.session_key(project, session)) or []

    async def aclose(self) -> None:
        async with self.pool.guard:
            await self.pool.close_all()
