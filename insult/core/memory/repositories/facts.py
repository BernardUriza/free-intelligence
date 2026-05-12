"""User facts — structured long-term memory about each user.

Two provenance tiers coexist in the same table, distinguished by `source`:
- `'auto'`: produced by the LLM fact-extraction background task. Wiped on
  every re-extraction (the extractor sees the last N messages and outputs
  a full refreshed list).
- `'manual'`: curated by a human operator or cross-user injection. NEVER
  wiped. This distinction exists because before the `source` column was
  introduced, every re-extraction nuked manual injections — the bot would
  forget anything a teammate contributed within one turn.

Migrated to asyncpg on 2026-05-12 PG migration. `cursor.lastrowid` →
`RETURNING id` + `_fetchval`. Vector path now hits pgvector through
the rewritten `core/vectors` module — same signature, pool-based.
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from insult.core.memory.base import BaseRepository

log = structlog.get_logger()


class FactsRepository(BaseRepository):
    """Owns the `user_facts` table. Semantic search integrates `core/vectors`."""

    async def get_facts(self, user_id: str) -> list[dict]:
        """All live facts for a user, newest-updated first.

        Soft-deleted rows (`deleted_at IS NOT NULL`) are excluded — the
        Mem0-style consolidator marks rows for delayed purge instead of
        DELETE, so live SELECTs must filter them out.
        """
        rows = await self._fetch(
            "SELECT id, fact, category, updated_at FROM user_facts "
            "WHERE user_id = $1 AND deleted_at IS NULL "
            "ORDER BY updated_at DESC",
            user_id,
        )
        return [
            {"id": r["id"], "fact": r["fact"], "category": r["category"], "updated_at": r["updated_at"]} for r in rows
        ]

    async def get_all_facts(self) -> list[dict]:
        """Every live fact for every user — used by cross-user prompt injection."""
        rows = await self._fetch(
            "SELECT user_id, id, fact, category, updated_at FROM user_facts "
            "WHERE deleted_at IS NULL "
            "ORDER BY user_id, updated_at DESC",
        )
        return [
            {
                "user_id": r["user_id"],
                "id": r["id"],
                "fact": r["fact"],
                "category": r["category"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    async def save_facts(self, user_id: str, facts: list[dict]) -> None:
        """Replace AUTO-extracted facts for a user with a new snapshot.

        Rows with source='manual' are PRESERVED. This is the critical
        invariant: before it existed, any curated fact died on the next
        conversation turn because the LLM extractor only sees ~10 messages
        and routinely omits older facts from its output. The DELETE below
        is scoped to source='auto' precisely to protect manual entries.

        Wrapped in a single transaction so partial INSERTs don't leave the
        DB in a half-wiped state if the connection drops mid-loop."""
        now = time.time()
        try:
            async with self._tx() as conn:
                await conn.execute(
                    "DELETE FROM user_facts WHERE user_id = $1 AND source = 'auto'",
                    user_id,
                )
                if facts:
                    await conn.executemany(
                        "INSERT INTO user_facts (user_id, fact, category, updated_at, source) "
                        "VALUES ($1, $2, $3, $4, 'auto')",
                        [(user_id, f["fact"], f.get("category", "general"), now) for f in facts],
                    )
            log.info("facts_saved", user_id=user_id, count=len(facts))

            # Update vector embeddings if available. Swallow per-call errors —
            # a failed vector upsert must not break the primary SQL commit.
            if self.vectors_available:
                try:
                    from insult.core.vectors import upsert_fact_vectors

                    await upsert_fact_vectors(self._pool, user_id, facts)
                except Exception as ve:
                    log.warning("facts_vector_upsert_failed", user_id=user_id, error=str(ve))
        except asyncpg.PostgresError as e:
            log.error("facts_save_failed", user_id=user_id, error=str(e))

    async def add_manual_fact(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
    ) -> int:
        """Insert a curated fact marked source='manual' so extract_facts can't wipe it.

        Returns the inserted row id. This is an append, not an upsert —
        callers that care about dedup must do their own check."""
        now = time.time()
        row_id = await self._fetchval(
            "INSERT INTO user_facts (user_id, fact, category, updated_at, source) "
            "VALUES ($1, $2, $3, $4, 'manual') RETURNING id",
            user_id,
            fact,
            category,
            now,
        )
        row_id = int(row_id or 0)
        log.info("manual_fact_added", user_id=user_id, fact_id=row_id, category=category)
        return row_id

    # -- Consolidator-facing primitives --
    # These methods are used by `core/memory_consolidator` to apply a
    # judge-produced plan over user_facts. Kept in the repo so SQL stays
    # owned by the table-owner; the consolidator orchestrates the plan but
    # never writes raw SQL.

    async def count_live(self, user_id: str) -> int:
        """Live (non-soft-deleted) facts for a user. O(n) but only used at
        end-of-consolidation for one report metric."""
        return int(
            await self._fetchval(
                "SELECT COUNT(*) FROM user_facts WHERE user_id = $1 AND deleted_at IS NULL",
                user_id,
            )
            or 0
        )

    async def purge_soft_deleted(self, cutoff: float) -> int:
        """Hard-delete rows whose soft-delete is older than `cutoff`.

        Returns the number of rows removed. Called once per consolidation
        run; rows that survive the retention window are gone forever."""
        tag = await self._execute(
            "DELETE FROM user_facts WHERE deleted_at IS NOT NULL AND deleted_at < $1",
            cutoff,
        )
        try:
            return int(tag.rsplit(" ", 1)[-1])
        except (ValueError, AttributeError):
            return 0

    async def apply_consolidation_plan(
        self,
        user_id: str,
        by_id: dict[int, dict],
        plan: list[dict],
        run_ts: float,
        op_factory,
    ) -> list:
        """Translate the judge's plan into SQL operations + audit log rows.

        Wrapped in a single transaction so a crash mid-plan leaves
        user_facts in a coherent state (no soft-delete without its replacement,
        no audit row without its op). `op_factory` builds the caller's
        FactOperation dataclass so this repo doesn't import the consolidator
        symbol — avoids a circular dep between two packages that already
        depend on each other through MemoryStore.

        Returns the list of applied operations (op_factory return values),
        in plan order.
        """
        applied: list = []
        async with self._tx() as conn:
            for op in plan:
                kind = op["op"]
                reason = op.get("reason", "")[:500]

                if kind == "NOOP":
                    fid = op["id"]
                    applied.append(
                        op_factory(
                            "NOOP",
                            fid,
                            fid,
                            by_id[fid]["fact"],
                            by_id[fid]["fact"],
                            reason,
                        )
                    )
                    continue

                if kind == "DELETE":
                    fid = op["id"]
                    await conn.execute(
                        "UPDATE user_facts SET deleted_at = $1 WHERE id = $2",
                        run_ts,
                        fid,
                    )
                    applied.append(op_factory("DELETE", fid, None, by_id[fid]["fact"], None, reason))
                    continue

                if kind == "UPDATE":
                    ids = op["merge_ids"]
                    new_text = op["new_fact"]
                    category = op.get("category", "general")
                    for fid in ids:
                        await conn.execute(
                            "UPDATE user_facts SET deleted_at = $1 WHERE id = $2",
                            run_ts,
                            fid,
                        )
                    new_id = await conn.fetchval(
                        "INSERT INTO user_facts (user_id, fact, category, updated_at, source) "
                        "VALUES ($1, $2, $3, $4, 'auto') RETURNING id",
                        user_id,
                        new_text,
                        category,
                        run_ts,
                    )
                    new_id = int(new_id or 0)
                    for fid in ids:
                        applied.append(
                            op_factory(
                                "UPDATE",
                                fid,
                                new_id,
                                by_id[fid]["fact"],
                                new_text,
                                reason,
                            )
                        )

            # Audit log rows — one per applied op. Written inside the same
            # transaction so the audit table and user_facts can never disagree.
            for o in applied:
                await conn.execute(
                    "INSERT INTO fact_consolidation_log "
                    "(run_ts, user_id, fact_id_before, fact_id_after, op, reason, "
                    "fact_text_before, fact_text_after) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    run_ts,
                    user_id,
                    o.fact_id_before,
                    o.fact_id_after,
                    o.op,
                    o.reason,
                    o.fact_text_before,
                    o.fact_text_after,
                )
        return applied

    async def search_facts_semantic(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        """Hybrid vector + fallback-keyword search for relevance-ranked facts.

        Falls back to `get_facts()` (unranked) when vectors are unavailable
        OR when the vector search returns zero hits so callers can treat
        this as a single entry point regardless of pgvector initialization
        state."""
        if not self.vectors_available:
            return await self.get_facts(user_id)

        try:
            from insult.core.vectors import search_facts_hybrid

            results = await search_facts_hybrid(self._pool, user_id, query, limit=limit)
            if results:
                log.info(
                    "facts_semantic_search",
                    user_id=user_id,
                    query=query[:50],
                    results=len(results),
                )
                return results
            return await self.get_facts(user_id)
        except Exception as e:
            log.warning("facts_semantic_search_failed", user_id=user_id, error=str(e))
            return await self.get_facts(user_id)
