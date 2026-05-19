"""``MemoryStore`` Protocol — atomic-fact long-term memory.

Sibling of ``fi_core.rag.protocols.DocumentChunkStore``. Shares the
async-first design language, namespace-style isolation
(``principal_id`` here, ``namespace`` there) and asyncpg+pgvector as
the reference pg implementation. But the primitive is different — a
fact is an atomic unit, not a chunk of a larger document — so they
live in sibling packages rather than one inheriting the other.

The Protocol is intentionally narrow. Five capability clusters:

1. **CRUD** — get_facts, save_facts (auto refresh), add_fact (single
   insert with source label).
2. **Soft-delete** — soft_delete_fact (mark deleted_at), purge_soft_deleted
   (hard-delete rows past the retention window).
3. **Search** — semantic_search (hybrid vector + fallback for the
   pgvector impl; pure SQL list for impls without vectors).
4. **Consolidation** — apply_consolidation_plan (transactional apply of
   a Mem0-style judge plan produced via
   ``fi_core.persona.mcp_server.parse_consolidation_result``).
5. **Lifecycle** — init_schema, close (asyncpg pool teardown for
   the pg impl; no-ops for in-memory impls).

What this Protocol does NOT cover (intentional):

- Embedding generation. The store accepts pre-computed embeddings or
  delegates to a caller-injected ``Embedder``; it does not embed text
  itself. Keeps the store embedding-method-agnostic.
- Fact extraction from raw conversation. Out of scope (see package
  docstring).
- Profile shapes or aggregate user state. Just facts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fi_core.memory.types import ConsolidationOp, Fact, FactSource


@runtime_checkable
class MemoryStore(Protocol):
    """Long-term, principal-scoped atomic-fact storage.

    ``principal_id`` is the tenant key — a user id, patient id, account
    id, whatever the consumer scopes by. Every method except
    ``purge_soft_deleted`` and lifecycle methods operates within a
    single principal's scope; cross-principal queries are out of scope
    (do them at the SQL layer if you need them).
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get_facts(
        self,
        principal_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Fact]:
        """All facts for a principal, newest-updated first.

        Soft-deleted rows excluded by default. Pass
        ``include_deleted=True`` to see them (useful for undo / audit
        flows). ``deleted_at`` on returned Facts is None for live rows.
        """
        ...

    async def save_facts(
        self,
        principal_id: str,
        facts: list[Fact],
    ) -> None:
        """Replace AUTO-extracted facts with a fresh snapshot.

        MANUAL and AGENT source facts are PRESERVED. This is the
        critical invariant from discord-bot's production schema: before
        the source column existed, every re-extraction nuked manually
        curated facts because the LLM extractor only sees ~10 messages
        and routinely omits older facts from its output.

        Wraps the DELETE + INSERT in a single transaction so partial
        failures leave the principal's fact set in a coherent state.
        """
        ...

    async def add_fact(
        self,
        principal_id: str,
        fact: str,
        *,
        category: str = "general",
        source: FactSource | None = None,
    ) -> int:
        """Insert a single fact with the given source label. Returns the new id.

        Append-only — callers that care about dedup must check first.
        ``source`` defaults to the impl's choice (typically MANUAL).
        """
        ...

    # ------------------------------------------------------------------
    # Soft-delete + retention
    # ------------------------------------------------------------------

    async def soft_delete_fact(self, fact_id: int, *, deleted_at: float) -> bool:
        """Mark a single row as soft-deleted. Returns False if the id is unknown.

        The row stays in the table until ``purge_soft_deleted`` sweeps
        it; live SELECTs filter by ``deleted_at IS NULL``.
        """
        ...

    async def purge_soft_deleted(self, cutoff: float) -> int:
        """Hard-delete rows whose ``deleted_at`` is older than ``cutoff``.

        Returns the number of rows removed. Callers compute ``cutoff``
        via their :class:`RetentionPolicy`. Idempotent: re-running with
        the same cutoff is a no-op.
        """
        ...

    async def count_live(self, principal_id: str) -> int:
        """Count of non-soft-deleted facts for a principal."""
        ...

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def semantic_search(
        self,
        principal_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> list[Fact]:
        """Hybrid vector + fallback-keyword search.

        Impls with vector support (e.g. ``PgMemoryStore`` with pgvector
        initialized) do a real embedding-similarity ranked search.
        Impls without — or when vectors fall through with zero hits —
        fall back to ``get_facts``. Callers should treat this as a
        single entry point regardless of vector init state.
        """
        ...

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    async def apply_consolidation_plan(
        self,
        principal_id: str,
        plan: list[dict[str, Any]],
        *,
        run_ts: float,
    ) -> list[ConsolidationOp]:
        """Apply a Mem0-style judge plan transactionally.

        The plan is produced by
        ``fi_core.persona.mcp_server.parse_consolidation_result`` (or a
        compatible source). Each op is NOOP / DELETE / UPDATE; the
        store translates them into soft-deletes + inserts and emits
        :class:`ConsolidationOp` rows for the audit trail.

        Wrapped in a single transaction so a crash mid-plan leaves the
        store in a coherent state — no orphan soft-deletes without
        their replacement, no audit rows pointing at non-existent facts.
        """
        ...

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_schema(self) -> None:
        """Idempotently create the backing schema.

        For ``PgMemoryStore`` this issues CREATE TABLE IF NOT EXISTS +
        CREATE INDEX. For in-memory impls this is a no-op. Versioned
        migrations across time are the consumer's responsibility.
        """
        ...

    async def close(self) -> None:
        """Tear down any resources (e.g. asyncpg pool)."""
        ...
