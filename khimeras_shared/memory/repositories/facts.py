"""User facts — structured long-term memory about each user.

Two provenance tiers coexist in the same table, distinguished by `source`:
- `'auto'`: produced by the LLM fact-extraction background task. As of the
  2026-06-03 P0 fix the extractor's output is UNIONED onto the full live auto
  set (`facts.merge_facts_additive` + `get_auto_facts`), so re-extraction can
  only ADD. Before the fix it saved only the prompt's semantic top-N subset
  into a snapshot-replace, hard-deleting every auto fact outside the top-N on
  every turn. `save_facts` still does the scoped snapshot replace, but it now
  always receives a superset of what was stored.
- `'manual'`: curated by a human operator or cross-user injection. NEVER
  wiped. This distinction exists because before the `source` column was
  introduced, every re-extraction nuked manual injections — the bot would
  forget anything a teammate contributed within one turn.
- `'agent'`: produced in-band by the persona's `[REMEMBER:]` marker.
  Survives `save_facts` (which only wipes `'auto'`) but stays distinct
  from operator-curated `'manual'` rows.

## fi-core migration (2026-05-22)

The hot path (get / save / add / count / purge / semantic_search) now
delegates to `fi_core.memory.PgMemoryStore` — the production-validated
store fi-core extracted FROM this very repo, now shared with AURITY.
Embeddings moved from the standalone `fact_embeddings` table to the inline
`principal_facts.embedding` column that `PgMemoryStore` self-manages; the
embedder is the local MiniLM model (`MiniLMEmbedder`, 384d) wired in only
when pgvector loaded at boot.

`PgMemoryStore` normally owns its own asyncpg pool, but the bot already
runs ONE shared pool (with the pgvector codec registered per-connection in
`connection.py`) and owns the schema. `_SharedPoolMemoryStore` injects that
pool and bypasses `init_schema()` so there is no second pool and no extra
lifecycle to manage.

Two methods stay on hand-rolled SQL on purpose:
- `get_all_facts()` — a cross-principal query that `MemoryStore` explicitly
  leaves out of scope (do cross-tenant reads at the SQL layer).
- `apply_consolidation_plan()` — keeps the bot's `op_factory` / `by_id`
  contract so the consolidator stays untouched; it now also writes the
  inline embedding for merged facts so semantic search stays consistent
  with the `PgMemoryStore` write path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import asyncpg
import structlog

from khimeras_shared.memory.base import BaseRepository
from khimeras_shared.memory.minilm_embedder import MiniLMEmbedder

if TYPE_CHECKING:
    from fi_core.memory.types import Fact

    from khimeras_shared.memory.connection import ConnectionManager

log = structlog.get_logger()


def _fact_to_dict(f: Fact) -> dict:
    """Translate a fi-core ``Fact`` back into the legacy dict shape the
    bot's ~30 fact consumers expect (``{id, fact, category, updated_at}``).

    The `source` / `deleted_at` fields the dataclass also carries are
    intentionally dropped — no caller reads them off the dict, and adding
    them would silently change the shape every consumer pattern-matches."""
    return {"id": f.id, "fact": f.fact, "category": f.category, "updated_at": f.updated_at}


def _build_shared_pool_store(manager: ConnectionManager, embedder: MiniLMEmbedder | None):
    """Construct a ``PgMemoryStore`` bound to the bot's shared pool.

    Subclassing and overriding ``_p`` lets every inherited method
    (`get_facts`, `save_facts`, `add_fact`, `semantic_search`, …) run
    against the bot's `ConnectionManager` pool — which already registers the
    pgvector codec per connection, so the `Vector(...)` parameters the
    parent passes work without a second `register_vector` setup. We never
    call `init_schema()` (the bot owns the schema) or `close()` (the bot
    owns the pool lifecycle).

    Done as a factory so importing this module never hard-requires fi-core
    at import time — the fi-core import happens on first facts use."""
    from fi_core.memory.stores.pgvector_memory import PgMemoryStore

    class _Bound(PgMemoryStore):
        def __init__(self) -> None:
            self._manager = manager
            self._embedder = embedder

        @property
        def _p(self) -> asyncpg.Pool:
            pool = self._manager.pool
            if pool is None:
                raise RuntimeError("ConnectionManager is not connected — call connect() first")
            return pool

    return _Bound()


class FactsRepository(BaseRepository):
    """Owns the `principal_facts` table. Hot path delegates to fi-core's
    `PgMemoryStore`; cross-user + consolidation SQL stays local."""

    def __init__(self, manager: ConnectionManager):
        super().__init__(manager)
        self._store: Any = None  # lazy PgMemoryStore over the shared pool

    def _get_store(self) -> Any:
        """Lazily build the shared-pool PgMemoryStore.

        The embedder is wired only when pgvector loaded at boot — matching
        the pre-migration behavior where `vectors_available=False` meant
        save_facts skipped the vector upsert and search fell back to
        unranked `get_facts`. With no embedder, `PgMemoryStore` writes a
        NULL embedding and `semantic_search` returns `get_facts`."""
        if self._store is None:
            embedder = MiniLMEmbedder() if self.vectors_available else None
            self._store = _build_shared_pool_store(self._manager, embedder)
        return self._store

    # ------------------------------------------------------------------
    # Hot path — delegated to fi_core.memory.PgMemoryStore
    # ------------------------------------------------------------------

    async def get_facts(self, user_id: str) -> list[dict]:
        """All live facts for a user, newest-updated first."""
        facts = await self._get_store().get_facts(user_id)
        return [_fact_to_dict(f) for f in facts]

    async def get_auto_facts(self, user_id: str) -> list[dict]:
        """Every LIVE auto-extracted fact for a user — the COMPLETE set, not
        the semantic top-N injected into the prompt.

        The extraction backstop needs this because `save_facts` REPLACES the
        whole auto snapshot (`DELETE … WHERE source='auto'`). Feeding the
        extractor only the injected top-N subset and then saving its output
        hard-deletes every auto fact OUTSIDE that subset — every turn, no
        recovery. That mismatch (subset in, full-snapshot replace out) is the
        reason a user's auto-facts could never grow past ~10. The merge in
        `tasks.extract_user_facts` unions onto this full set so extraction is
        ADD-only. (P0, 2026-06-03.)"""
        rows = await self._fetch(
            "SELECT id, fact, category, updated_at "
            "FROM principal_facts "
            "WHERE principal_id = $1 AND source = 'auto' AND deleted_at IS NULL "
            "ORDER BY updated_at DESC",
            user_id,
        )
        return [
            {"id": r["id"], "fact": r["fact"], "category": r["category"], "updated_at": r["updated_at"]} for r in rows
        ]

    async def get_facts_for_injection(self, user_id: str, auto_limit: int = 10) -> list[dict]:
        """Facts to inject when ANOTHER user asks about this person — curated
        first, then the most recent auto facts.

        The "Other People in This Channel" block used `get_facts()[:N]` (pure
        recency), so a burst of recent auto-extractions (e.g. a pet-sitting
        mishap) would push the CURATED, load-bearing facts (a person's plans,
        origins, diagnoses — all `manual`/`agent`) out of the top-N. The bot then
        knew Alex's dog drama but not her trainer-cert plan or that her family is
        from Tantoyuca. Fix (2026-06-03): ALWAYS include every curated fact, then
        top up with the freshest `auto` facts. Curated memory is finite and is
        exactly what someone asking ABOUT a third party needs."""
        rows = await self._fetch(
            "SELECT id, fact, category, updated_at, source "
            "FROM principal_facts "
            "WHERE principal_id = $1 AND deleted_at IS NULL "
            "ORDER BY CASE WHEN source IN ('manual', 'agent') THEN 0 ELSE 1 END, updated_at DESC",
            user_id,
        )
        curated = [r for r in rows if r["source"] in ("manual", "agent")]
        auto = [r for r in rows if r["source"] == "auto"]
        chosen = [*curated, *auto[:auto_limit]]
        return [
            {"id": r["id"], "fact": r["fact"], "category": r["category"], "updated_at": r["updated_at"]} for r in chosen
        ]

    async def save_facts(self, user_id: str, facts: list[dict]) -> None:
        """Replace AUTO-extracted facts for a user with a new snapshot.

        Rows with source='manual' / 'agent' are PRESERVED (the store's
        DELETE is scoped to source='auto'). Embeddings are written inline
        by the store using the MiniLM embedder — no separate
        `fact_embeddings` upsert anymore. A failed embed degrades a single
        row to a NULL embedding; it never rolls back the SQL."""
        from fi_core.memory.types import Fact

        fact_objs = [Fact(fact=f["fact"], principal_id=user_id, category=f.get("category", "general")) for f in facts]
        try:
            await self._get_store().save_facts(user_id, fact_objs)
            log.info("facts_saved", user_id=user_id, count=len(fact_objs))
        except asyncpg.PostgresError as e:
            log.error("facts_save_failed", user_id=user_id, error=str(e))

    async def add_manual_fact(self, user_id: str, fact: str, category: str = "general") -> int:
        """Insert a curated fact marked source='manual' so extract_facts can't wipe it."""
        from fi_core.memory.types import FactSource

        row_id = await self._get_store().add_fact(user_id, fact, category=category, source=FactSource.MANUAL)
        log.info("manual_fact_added", user_id=user_id, fact_id=row_id, category=category)
        return row_id

    async def add_remember_fact(self, user_id: str, fact: str, category: str = "general") -> int:
        """Insert a fact produced in-band by the agent's `[REMEMBER:]` marker (source='agent')."""
        from fi_core.memory.types import FactSource

        row_id = await self._get_store().add_fact(user_id, fact, category=category, source=FactSource.AGENT)
        log.info("remember_fact_added", user_id=user_id, fact_id=row_id, category=category)
        return row_id

    async def count_live(self, user_id: str) -> int:
        """Live (non-soft-deleted) facts for a user."""
        return await self._get_store().count_live(user_id)

    async def purge_soft_deleted(self, cutoff: float) -> int:
        """Hard-delete rows whose soft-delete is older than `cutoff`."""
        return await self._get_store().purge_soft_deleted(cutoff)

    async def search_facts_semantic(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        """Relevance-ranked facts via inline-embedding cosine search.

        `PgMemoryStore.semantic_search` already falls back to unranked
        `get_facts` when no embedder is wired, the query can't embed, or
        the user has zero embedded rows — so this stays a single safe
        entry point regardless of pgvector state.

        `limit` is enforced HERE, on every path, because those fallbacks
        IGNORE it: on 2026-07-23 a voice note whose embedding failed came back
        with all 4115 of Bernard's facts, inflating the runner payload to
        376,300 chars, and the turn died on a 422 (`user_text` > 256000
        characters). A fallback that leaves the bot mute is worse than no
        fallback."""
        try:
            facts = await self._get_store().semantic_search(user_id, query, limit=limit)
            log.info(
                "facts_semantic_search",
                user_id=user_id,
                query=query[:50],
                results=len(facts),
                capped=len(facts) > limit,
            )
            return [_fact_to_dict(f) for f in facts[:limit]]
        except Exception as e:
            log.warning("facts_semantic_search_failed", user_id=user_id, error=str(e))
            return (await self.get_facts(user_id))[:limit]

    # ------------------------------------------------------------------
    # Local SQL — out of MemoryStore scope (cross-user) or consolidator-owned
    # ------------------------------------------------------------------

    async def get_all_facts(self) -> list[dict]:
        """Every live fact for every user — used by cross-user prompt injection.

        Cross-principal by design; `MemoryStore` deliberately scopes every
        method to one principal, so this stays raw SQL on the shared pool.
        Aliases `principal_id` → `user_id` for caller-dict compat (~25
        callsites in bot.py + memory_consolidator expect the key)."""
        rows = await self._fetch(
            "SELECT principal_id AS user_id, id, fact, category, updated_at "
            "FROM principal_facts "
            "WHERE deleted_at IS NULL "
            "ORDER BY principal_id, updated_at DESC",
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

    async def apply_consolidation_plan(
        self,
        user_id: str,
        by_id: dict[int, dict],
        plan: list[dict],
        run_ts: float,
        op_factory,
    ) -> list:
        """Translate the judge's plan into SQL operations + audit log rows.

        Kept on local SQL so the consolidator's `by_id` / `op_factory`
        contract is untouched. Single transaction so a crash mid-plan
        leaves principal_facts coherent (no soft-delete without its
        replacement, no audit row without its op).

        Merged (UPDATE) facts are inserted WITH an inline embedding when
        pgvector is available, so consolidation output stays searchable —
        matching `PgMemoryStore`'s write path. Embed failure degrades to a
        NULL embedding, never aborts the transaction."""
        embedder = MiniLMEmbedder() if self.vectors_available else None
        applied: list = []
        async with self._tx() as conn:
            for op in plan:
                kind = op["op"]
                reason = op.get("reason", "")[:500]

                if kind == "NOOP":
                    fid = op["id"]
                    applied.append(op_factory("NOOP", fid, fid, by_id[fid]["fact"], by_id[fid]["fact"], reason))
                    continue

                if kind == "DELETE":
                    fid = op["id"]
                    await conn.execute(
                        "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
                        run_ts,
                        fid,
                    )
                    applied.append(op_factory("DELETE", fid, None, by_id[fid]["fact"], None, reason))
                    continue

                if kind == "UPDATE":
                    ids = op["merge_ids"]
                    new_text = op["new_fact"]
                    category = op.get("category", "general")

                    embedding_vec = None
                    if embedder is not None:
                        try:
                            from pgvector import Vector

                            embedding_vec = Vector(await embedder.embed(new_text))
                        except Exception:
                            embedding_vec = None

                    for fid in ids:
                        await conn.execute(
                            "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
                            run_ts,
                            fid,
                        )
                    new_id = await conn.fetchval(
                        "INSERT INTO principal_facts "
                        "(principal_id, fact, category, updated_at, source, embedding) "
                        "VALUES ($1, $2, $3, $4, 'auto', $5) RETURNING id",
                        user_id,
                        new_text,
                        category,
                        run_ts,
                        embedding_vec,
                    )
                    new_id = int(new_id or 0)
                    for fid in ids:
                        applied.append(op_factory("UPDATE", fid, new_id, by_id[fid]["fact"], new_text, reason))

            # Audit log rows — one per applied op, same transaction so the
            # audit table and principal_facts can never disagree.
            for o in applied:
                await conn.execute(
                    "INSERT INTO fact_consolidation_log "
                    "(run_ts, principal_id, fact_id_before, fact_id_after, op, reason, "
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
