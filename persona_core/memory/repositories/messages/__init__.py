"""Messages table — conversational store, context retrieval, keyword search.

This is the hot path: every user turn reads recent + relevant, and every
bot reply writes a new row. Also sources the channel-awareness helpers
(participants, activity) because they query the same table. The messages
table is append-only except for explicit pruning via `delete_before`.

Split by responsibility (2026-07-20): `writes` (idempotent append + prune),
`history` (context reads + ILIKE search), `aggregates` (stats/participants/
activity), `stopwords` (the search-term filter). `MessagesRepository`
composes the three query mixins over the shared `BaseRepository`.

Migrated to asyncpg on 2026-05-12 PG migration. Placeholders `?` → `$N`,
`aiosqlite.Error` → `asyncpg.PostgresError`. The connection pool removes
the SQLite single-writer bottleneck — recent + search + participants can
run concurrently on different conns.
"""

from persona_core.memory.repositories.messages.aggregates import MessagesAggregates
from persona_core.memory.repositories.messages.history import MessagesHistory
from persona_core.memory.repositories.messages.stopwords import search_terms
from persona_core.memory.repositories.messages.writes import MessagesWrites


class MessagesRepository(MessagesWrites, MessagesHistory, MessagesAggregates):
    """Owns the `messages` table plus every read of it (participants, activity)."""


__all__ = ["MessagesRepository", "search_terms"]
