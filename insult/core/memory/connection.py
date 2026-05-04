"""Owns the aiosqlite connection, schema creation, and migrations.

Single process-wide connection, shared out to all repositories via
BaseRepository. See `base.py` for the rationale (SQLite single-writer +
WAL interaction). Schema lives here because all tables must exist before
any repository performs its first query — and because the migrations
(`ALTER TABLE ... ADD COLUMN`) are point-in-time decisions, not per-repo.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import aiosqlite
import structlog

log = structlog.get_logger()


class ConnectionManager:
    """Lifecycle manager for the shared aiosqlite connection.

    Callers use `get_connection()` to receive the live handle and
    `close()` to drain the WAL and disconnect. Schema initialization runs
    once inside `connect()` — migrations are idempotent (`IF NOT EXISTS`
    + `ALTER TABLE ... ADD COLUMN` wrapped in `suppress`) so boot order
    is safe across redeploys even when the schema evolves.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._vectors_available: bool = False

    @property
    def vectors_available(self) -> bool:
        return self._vectors_available

    @property
    def raw_db(self) -> aiosqlite.Connection | None:
        """Escape hatch for code that needs the raw handle (vectors helpers)."""
        return self._db

    async def connect(self) -> None:
        """Open the connection and initialize the full schema.

        Idempotent: safe to call on boot of an existing DB. Columns added
        post-initial-design are wrapped in `suppress(OperationalError)`
        so a second call (column already exists) doesn't crash.
        """
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("PRAGMA journal_mode=WAL")

        await self._create_messages_table()
        await self._create_user_profiles_table()
        await self._create_user_facts_table()
        await self._create_world_scans_table()
        await self._create_channel_summaries_table()
        await self._create_reminders_table()
        await self._create_phase1_tables()
        await self._create_guild_config_table()
        await self._create_consolidation_log_table()
        await self._create_dream_diary_table()

        await self._db.commit()

        await self._init_vectors()

        log.info("memory_connected", db_path=str(self.db_path))

    async def get_connection(self) -> aiosqlite.Connection:
        """Return the live connection, reconnecting if it was dropped."""
        if self._db is None:
            log.warning("memory_reconnecting")
            await self.connect()
        assert self._db is not None
        return self._db

    async def close(self) -> None:
        """Checkpoint WAL and close. Critical for Azure Blob backup to be consistent."""
        if self._db is None:
            return

        # Checkpoint WAL to merge journal into main DB file before closing.
        # Critical for Azure backup: upload_db reads the main file only.
        try:
            await self._db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            log.warning("wal_checkpoint_failed_retrying_passive")
            try:
                await self._db.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except Exception:
                log.warning("wal_checkpoint_passive_also_failed")

        await self._db.close()
        self._db = None
        log.info("memory_closed")

    # -- Schema creation (split into one method per logical group) --

    async def _create_messages_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                for_user_id TEXT
            )
        """)
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE messages ADD COLUMN for_user_id TEXT")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE messages ADD COLUMN guild_id TEXT")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE messages ADD COLUMN channel_name TEXT")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE messages ADD COLUMN model_used TEXT")

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_ts
            ON messages(channel_id, timestamp DESC)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_context
            ON messages(channel_id, user_id, timestamp DESC)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_for_user
            ON messages(channel_id, for_user_id, timestamp DESC)
        """)

    async def _create_user_profiles_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

    async def _create_user_facts_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fact TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                updated_at REAL NOT NULL
            )
        """)
        # Idempotent migration: add 'source' column so we can distinguish
        # facts written by extract_facts (auto) from curated injections
        # (manual). save_facts only wipes the auto ones; manual survives
        # forever. Prior to this column, any manual fact died on the next
        # conversation turn because save_facts DELETE'd all user_facts rows.
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE user_facts ADD COLUMN source TEXT NOT NULL DEFAULT 'auto'")
        # Soft-delete column for the Mem0-style consolidator. NULL = live row;
        # any non-NULL value is the unix timestamp at which the consolidator
        # marked the row deleted. The 90-day hard-purge in
        # memory_consolidator.py runs DELETE WHERE deleted_at < now()-90d so
        # operators can still recover within the retention window.
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE user_facts ADD COLUMN deleted_at REAL DEFAULT NULL")
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_facts
            ON user_facts(user_id)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_facts_deleted_at
            ON user_facts(deleted_at)
            WHERE deleted_at IS NOT NULL
        """)

    async def _create_world_scans_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS world_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                findings TEXT NOT NULL,
                commentary TEXT NOT NULL,
                timestamp REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'web',
                external_id TEXT
            )
        """)
        # v3.7.12 migration: source + external_id let world_scans store
        # digests from outside platforms (Moltbook today, others later)
        # alongside web_search results, deduped via UNIQUE(source, external_id).
        # See .claude/plans/elegant-foraging-knuth.md Phase 0.
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE world_scans ADD COLUMN source TEXT NOT NULL DEFAULT 'web'")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE world_scans ADD COLUMN external_id TEXT")
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_world_scans_ts
            ON world_scans(timestamp DESC)
        """)
        # Partial unique index: only enforce uniqueness when external_id is set
        # so existing web_search rows (external_id=NULL) are unaffected.
        await self._db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_world_scans_source_external
            ON world_scans(source, external_id)
            WHERE external_id IS NOT NULL
        """)

    async def _create_channel_summaries_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS channel_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                summary TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                last_message_ts REAL NOT NULL,
                is_private INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_summaries_guild_channel
            ON channel_summaries(guild_id, channel_id)
        """)

    async def _create_reminders_table(self) -> None:
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                guild_id TEXT,
                created_by TEXT NOT NULL,
                description TEXT NOT NULL,
                remind_at REAL NOT NULL,
                mention_user_ids TEXT NOT NULL DEFAULT '',
                recurring TEXT NOT NULL DEFAULT 'none',
                delivered INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                snooze_msg_id INTEGER,
                requires_ack INTEGER NOT NULL DEFAULT 0,
                ack_msg_id INTEGER,
                ack_received INTEGER NOT NULL DEFAULT 0,
                ack_retry_count INTEGER NOT NULL DEFAULT 0,
                delivered_at REAL
            )
        """)
        # v3.7.7 migration: snooze_msg_id stores the Discord message id of the
        # delivered reminder so on_raw_reaction_add can map a reaction back to
        # the reminder (used to schedule a re-fire on ⏰/⏭️/📅).
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN snooze_msg_id INTEGER")
        # v3.7.8 migration: ack columns for reminders that demand confirmation.
        # When requires_ack=1 the bot re-fires once after a timeout if the
        # user did not react with ✅. Used for medication / critical tasks.
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN requires_ack INTEGER NOT NULL DEFAULT 0")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN ack_msg_id INTEGER")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN ack_received INTEGER NOT NULL DEFAULT 0")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN ack_retry_count INTEGER NOT NULL DEFAULT 0")
        with contextlib.suppress(aiosqlite.OperationalError):
            await self._db.execute("ALTER TABLE reminders ADD COLUMN delivered_at REAL")
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_pending
            ON reminders(delivered, remind_at)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_snooze_msg
            ON reminders(snooze_msg_id)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reminders_ack_pending
            ON reminders(requires_ack, ack_received, ack_retry_count, delivered_at)
        """)

    async def _create_phase1_tables(self) -> None:
        """Phase 1 (v3.0.0): disclosure, emotional arcs, stance, contradictions."""
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS disclosure_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                severity INTEGER NOT NULL,
                signals TEXT NOT NULL,
                message_excerpt TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_disclosure_user
            ON disclosure_log(user_id, timestamp DESC)
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS emotional_arcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                phase_since REAL NOT NULL,
                crisis_depth INTEGER NOT NULL DEFAULT 0,
                recovery_signals INTEGER NOT NULL DEFAULT 0,
                turns_in_phase INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_arc_user_channel
            ON emotional_arcs(channel_id, user_id)
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS stance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                position TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stance_channel_user
            ON stance_log(channel_id, user_id, timestamp DESC)
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS contradiction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                prior_statement TEXT NOT NULL,
                contradicting_statement TEXT NOT NULL,
                topic TEXT NOT NULL,
                called_out INTEGER NOT NULL DEFAULT 0,
                timestamp REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_contradiction_user
            ON contradiction_log(user_id, timestamp DESC)
        """)

    async def _create_guild_config_table(self) -> None:
        """v3.3.0: system channels for facts/reminders."""
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT PRIMARY KEY,
                category_id TEXT,
                facts_channel_id TEXT,
                reminders_channel_id TEXT,
                setup_complete INTEGER NOT NULL DEFAULT 0
            )
        """)

    async def _create_consolidation_log_table(self) -> None:
        """v3.6.0: audit trail for the Mem0-style fact consolidator.

        Every ADD/UPDATE/DELETE/NOOP decision the consolidator makes lands
        here so a future operator can answer "why did this fact disappear"
        without re-running an LLM. Recovery within the 90-day soft-delete
        window uses fact_id_before to look up the still-soft-deleted row.
        """
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS fact_consolidation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_ts REAL NOT NULL,
                user_id TEXT NOT NULL,
                fact_id_before INTEGER,
                fact_id_after INTEGER,
                op TEXT NOT NULL CHECK(op IN ('ADD','UPDATE','DELETE','NOOP')),
                reason TEXT,
                fact_text_before TEXT,
                fact_text_after TEXT
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_fcl_run_ts
            ON fact_consolidation_log(run_ts)
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_fcl_user_id
            ON fact_consolidation_log(user_id)
        """)

    async def _create_dream_diary_table(self) -> None:
        """In-character narrative log of consolidator runs.

        One row per run, written by the consolidator job at the end of
        each scheduled invocation. Surfaced to operators via the
        ``!siesta`` chat command and the ``/debug/dreams`` HTTP endpoint.
        Entries are intentionally short and read like Insult wrote them
        — they are NOT structured data; the structured per-user counts
        live in ``fact_consolidation_log``.
        """
        assert self._db is not None
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS dream_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_ts REAL NOT NULL,
                duration_ms INTEGER NOT NULL,
                users_total INTEGER NOT NULL,
                users_processed INTEGER NOT NULL,
                facts_in_total INTEGER NOT NULL,
                facts_out_total INTEGER NOT NULL,
                deletes_total INTEGER NOT NULL,
                updates_total INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ok','partial','failed')),
                content TEXT NOT NULL,
                error TEXT
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_dream_diary_run_ts
            ON dream_diary(run_ts DESC)
        """)

    async def _init_vectors(self) -> None:
        """Initialize sqlite-vec + FTS5 for semantic search. Best-effort."""
        assert self._db is not None
        try:
            import sqlite_vec

            self._db._conn.enable_load_extension(True)
            sqlite_vec.load(self._db._conn)

            from insult.core.vectors import init_vector_tables

            await init_vector_tables(self._db)
            self._vectors_available = True
            log.info("vectors_initialized")
        except Exception as e:
            log.warning("vectors_not_available", reason=str(e))
            self._vectors_available = False
