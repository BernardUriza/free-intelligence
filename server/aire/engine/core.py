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
from .contract import CostSink, TurnSpec
from .credentials import Rotor, is_metered
from .detach import Detached, drain_detached
from .ledger import Ledger
from .options import build_options
from .pool import Pool
from .turn import run_turn

WORKSPACES = Path(os.environ.get(
    "AIRE_WORKSPACES", Path(__file__).resolve().parent.parent.parent / "workspaces"))


class Engine:
    def __init__(self, session_store: Any) -> None:
        self.session_store = session_store
        self.pool = Pool()
        self.ledger = Ledger()  # the two spend ceilings and their bookkeeping
        self.detached = Detached()  # fire-and-forget background turns (#22a)
        self.rotor = Rotor()  # the credential chain (#31)
        self.slot_of: dict[str, str] = {}  # key → the slot each pooled client was born with
        self.spec_of: dict[str, TurnSpec] = {}  # key → the shape its client was born with (#38)

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

    async def _client_for(self, project: str, session: str, spec: TurnSpec,
                          slot: Any = None) -> tuple[Any, asyncio.Lock]:
        key = f"{project}/{session}"
        async with self.pool.guard:
            now = time.monotonic()
            await self.pool.evict(now)
            client = self.pool.clients.get(key)
            if client is None:
                await self.pool.make_space()  # close LRU idle so we stay <= POOL_MAX
                self.ledger.adopt(key)  # its predecessor's total counts for nothing
                resuming = await self.has_session(project, session)
                options = build_options(self.session_store, project, str(self._cwd(project)),
                                        sdk_session_uuid(session), spec, resuming,
                                        credential_env=slot.env if slot else None,
                                        metered=slot is None or is_metered(slot.name))
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self.pool.clients[key] = client
                self.spec_of[key] = spec  # the shape it was born with (#38)
                if slot is not None:
                    self.slot_of[key] = slot.name
            self.pool.used[key] = now
            lock = self.pool.locks.setdefault(key, asyncio.Lock())
        return client, lock

    async def run_stream(self, project: str, session: str, prompt: str, spec: TurnSpec,
                         images: tuple[dict[str, str], ...] = ()) -> AsyncIterator[dict[str, Any]]:
        """One turn, live (transcript mirrors to Postgres). The RAM slot
        (backpressure) is held for the whole turn: a 3rd device queues.

        The spend-ceiling gate lives in ``run_turn``, not here: whether the
        ceiling applies depends on which credential SLOT the turn rides, and
        the slot is chosen there."""
        async with self.pool.slot():
            # The turn lifecycle (attempts, budget cut, credential failover)
            # lives in turn.py — the #23/#31 detections share the result seam.
            async for event in run_turn(self, project, session, prompt, spec, images):
                yield event

    def launch_detached(self, project: str, session: str, prompt: str, spec: TurnSpec,
                        images: tuple[dict[str, str], ...] = (),
                        on_cost: CostSink | None = None) -> None:
        """Run the turn fire-and-forget (#22a): decoupled from the request, it
        finishes even if the caller hangs up. Raises if one already runs here.

        The draining (and the `on_cost` billing a detached turn still owes) lives
        in detach.py, with the rest of the fire-and-forget concept."""
        key = f"{project}/{session}"
        self.detached.launch(key, lambda: drain_detached(
            self.run_stream(project, session, prompt, spec, images), key, on_cost))

    async def _retire(self, project: str, session: str) -> None:
        """A client that reached max_budget_usd is POISONED: the SDK refuses every
        later turn on it with an empty result and no error. Dropping it is the
        cure — the pool is a cache, so the next turn rebuilds from the store with
        `resume=` and the memory is untouched ([[log-is-the-truth]])."""
        self.ledger.forget(f"{project}/{session}")
        await self._drop(f"{project}/{session}")

    async def _drop(self, key: str) -> None:
        """Let go of a pooled client deliberately — a retire (#23) or a rebind
        (#38). It is NOT the only exit, and claiming it was is what hid a ledger
        bug for a month: `evict`/`make_space` call `close_one` directly, on the
        common path. So every exit is repaired at the next BIRTH instead
        (`_client_for`: slot_of, spec_of, and the ledger's `adopt`)."""
        self.slot_of.pop(key, None)
        self.spec_of.pop(key, None)
        async with self.pool.guard:
            await self.pool.close_one(key)

    async def _rebind(self, project: str, session: str, spec: TurnSpec) -> None:
        """Drop the pooled client when THIS turn asks for a different shape (#38).

        The SDK takes mode/tools/model at CONSTRUCTION, so a pooled client keeps
        the shape it was born with for its whole idle life (~55 min). Before this,
        a turn that named another model was answered by the old one — silently,
        with no error: the #23/#31 lying-green family at the options seam.
        Rebuilding costs one cache-creation and loses NOTHING (the transcript is
        in Postgres; the next `_client_for` resumes it).

        Never closes a client under someone else's turn: an in-flight turn holds
        the key's lock, so we WAIT for it and drop afterwards. A turn that starts
        in that window keeps the old shape and is corrected by the next one — the
        divergence is bounded to one turn instead of an hour.
        """
        key = f"{project}/{session}"
        async with self.pool.guard:
            born = self.spec_of.get(key)
            if key not in self.pool.clients or born is None or born == spec:
                return
            lock = self.pool.locks.get(key)
        print(f"REBIND {key} {born} -> {spec}")
        if lock is not None:
            async with lock:
                pass
        await self._drop(key)

    async def aclose(self) -> None:
        async with self.pool.guard:
            await self.pool.close_all()
