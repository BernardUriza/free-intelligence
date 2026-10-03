"""Automatic fact extraction — grow the user's longitudinal memory, ADD-only.

The `source='auto'` backstop behind the persona's in-band `[REMEMBER:]` marker.
Fire-and-forget after a real user turn, tracked so the loop can't GC it. Every
save is a strict SUPERSET of the live auto set — extraction can only ADD, never
prune (P0 2026-06-03: a raw `save_facts(extractor_output)` hard-deletes every
auto fact outside the extractor's narrow view, every turn, with no recovery).
"""

from __future__ import annotations

import asyncio

import structlog

from persona_core.facts import UtilityClient, extract_facts, merge_facts_additive
from persona_core.memory import MemoryStore
from shared.personas import Persona

log = structlog.get_logger()

# One lock per user, shared across every persona's FactExtractor in this process.
# `save_facts` is a DELETE+reinsert snapshot (fi-core PgMemoryStore): two personas
# extracting the same user concurrently race their snapshots into the
# `idx_pf_auto_dedup` unique index and one save dies whole (observed 2026-07-20,
# Alex's save). Serializing per user makes the read-merge-save cycle atomic
# within the gateway; the cross-process race with the consolidator job remains,
# is logged, and self-heals on the next turn.
_user_extraction_locks: dict[str, asyncio.Lock] = {}


def _extraction_lock(user_id: str) -> asyncio.Lock:
    return _user_extraction_locks.setdefault(user_id, asyncio.Lock())


class FactExtractor:
    """Background ADD-only fact backstop. No-op when no judge client is wired.

    The judge is passed in per-spawn (read LIVE off the client) rather than held —
    so toggling the client's `judge_client` to None between turns disables
    extraction on the very next turn, not just for clients built without one.
    """

    def __init__(
        self,
        persona: Persona,
        memory: MemoryStore,
        bg_tasks: set[asyncio.Task],
        *,
        model: str | None = None,
    ) -> None:
        self.persona = persona
        self.memory = memory
        # Shares the client's task set so a spawned extraction is not GC'd mid-flight.
        self._bg_tasks = bg_tasks
        # None = the judge's own default model (Haiku on the runner).
        self.model = model

    def spawn(
        self,
        judge_client: UtilityClient | None,
        user_id: str,
        user_name: str,
        recent: list[dict],
    ) -> None:
        """Fire-and-forget the fact backstop, tracked so the loop can't GC it."""
        if judge_client is None or not user_id:
            return
        task = asyncio.create_task(self._extract_and_persist(judge_client, user_id, user_name, recent))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _extract_and_persist(
        self,
        judge: UtilityClient,
        user_id: str,
        user_name: str,
        recent: list[dict],
    ) -> None:
        """Grow the user's longitudinal memory — ADD-only, best-effort.

        The extractor sees a SUBSET of what is stored, but `save_facts` REPLACES
        the whole `source='auto'` snapshot. So its output is UNIONED onto the
        COMPLETE live auto set (`get_auto_facts`) before saving: the snapshot
        written is always a SUPERSET of what was there, and extraction can only
        ADD. Everything here is best-effort: a dead judge or a failed save is
        logged and swallowed. The user already has their reply; memory growth
        must never be able to break a delivered turn.
        """
        try:
            async with _extraction_lock(user_id):
                existing = await self.memory.get_facts(user_id)
                new_facts = await extract_facts(
                    judge,
                    self.model,
                    user_name,
                    existing,
                    recent,
                )
                all_auto = await self.memory.get_auto_facts(user_id)
                merged, added = merge_facts_additive(all_auto, new_facts)
                if not added:
                    log.info(
                        "facts_extraction_nothing_new",
                        persona_id=self.persona.persona_id,
                        user_id=user_id,
                        total_auto=len(merged),
                    )
                    return
                await self.memory.save_facts(user_id, merged)
            log.info(
                "facts_extracted_additive",
                persona_id=self.persona.persona_id,
                user_id=user_id,
                added=len(added),
                total_auto=len(merged),
            )
        except Exception:
            log.exception(
                "facts_extraction_failed",
                persona_id=self.persona.persona_id,
                user_id=user_id,
            )
