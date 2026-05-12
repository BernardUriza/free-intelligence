-- Postgres schema for the insult-bot memory store.
-- 1:1 translation of the SQLite schema in connection.py, with:
--   * SQLite REAL → Postgres DOUBLE PRECISION
--   * SQLite INTEGER PRIMARY KEY AUTOINCREMENT → Postgres BIGSERIAL PRIMARY KEY
--   * Idempotent `ALTER TABLE ... ADD COLUMN` becomes plain CREATE TABLE
--     (Postgres-managed migrations handle subsequent schema changes via
--     Alembic — no more idempotent column additions in connect().)
--   * sqlite-vec embedding table → pgvector with VECTOR type.
--
-- All tables use IF NOT EXISTS so this script is safe to re-run on an
-- already-initialized database — same boot-time idempotency we had with
-- SQLite, without the migration suppress() blocks.
--
-- Indexes preserved with the same names so query plans match.

CREATE EXTENSION IF NOT EXISTS vector;

-- ─── messages ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    channel_id      TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    user_name       TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    timestamp       DOUBLE PRECISION NOT NULL,
    for_user_id     TEXT,
    guild_id        TEXT,
    channel_name    TEXT,
    model_used      TEXT
);
CREATE INDEX IF NOT EXISTS idx_channel_ts ON messages(channel_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_context ON messages(channel_id, user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_for_user ON messages(channel_id, for_user_id, timestamp DESC);

-- ─── user_profiles ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id      TEXT PRIMARY KEY,
    profile_json JSONB NOT NULL,
    updated_at   DOUBLE PRECISION NOT NULL
);

-- ─── user_facts ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_facts (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL,
    fact        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    updated_at  DOUBLE PRECISION NOT NULL,
    source      TEXT NOT NULL DEFAULT 'auto',
    deleted_at  DOUBLE PRECISION DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_facts ON user_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_facts_deleted_at ON user_facts(deleted_at) WHERE deleted_at IS NOT NULL;

-- ─── world_scans ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS world_scans (
    id           BIGSERIAL PRIMARY KEY,
    topic        TEXT NOT NULL,
    findings     TEXT NOT NULL,
    commentary   TEXT NOT NULL,
    timestamp    DOUBLE PRECISION NOT NULL,
    source       TEXT NOT NULL DEFAULT 'web',
    external_id  TEXT
);
CREATE INDEX IF NOT EXISTS idx_world_scans_ts ON world_scans(timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_world_scans_source_external
    ON world_scans(source, external_id) WHERE external_id IS NOT NULL;

-- ─── channel_summaries ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS channel_summaries (
    id                BIGSERIAL PRIMARY KEY,
    guild_id          TEXT NOT NULL,
    channel_id        TEXT NOT NULL,
    channel_name      TEXT NOT NULL,
    summary           TEXT NOT NULL,
    message_count     INTEGER NOT NULL DEFAULT 0,
    last_message_ts   DOUBLE PRECISION NOT NULL,
    is_private        INTEGER NOT NULL DEFAULT 0,
    updated_at        DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_channel_summaries_guild_channel
    ON channel_summaries(guild_id, channel_id);

-- ─── reminders ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reminders (
    id                BIGSERIAL PRIMARY KEY,
    channel_id        TEXT NOT NULL,
    guild_id          TEXT,
    created_by        TEXT NOT NULL,
    description       TEXT NOT NULL,
    remind_at         DOUBLE PRECISION NOT NULL,
    mention_user_ids  TEXT NOT NULL DEFAULT '',
    recurring         TEXT NOT NULL DEFAULT 'none',
    delivered         INTEGER NOT NULL DEFAULT 0,
    created_at        DOUBLE PRECISION NOT NULL,
    snooze_msg_id     BIGINT,
    requires_ack      INTEGER NOT NULL DEFAULT 0,
    ack_msg_id        BIGINT,
    ack_received      INTEGER NOT NULL DEFAULT 0,
    ack_retry_count   INTEGER NOT NULL DEFAULT 0,
    delivered_at      DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(delivered, remind_at);
CREATE INDEX IF NOT EXISTS idx_reminders_snooze_msg ON reminders(snooze_msg_id);
CREATE INDEX IF NOT EXISTS idx_reminders_ack_pending
    ON reminders(requires_ack, ack_received, ack_retry_count, delivered_at);

-- ─── disclosure_log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS disclosure_log (
    id                BIGSERIAL PRIMARY KEY,
    channel_id        TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    category          TEXT NOT NULL,
    severity          INTEGER NOT NULL,
    signals           TEXT NOT NULL,
    message_excerpt   TEXT NOT NULL,
    timestamp         DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_disclosure_user ON disclosure_log(user_id, timestamp DESC);

-- ─── emotional_arcs ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emotional_arcs (
    id                BIGSERIAL PRIMARY KEY,
    channel_id        TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    phase             TEXT NOT NULL,
    phase_since       DOUBLE PRECISION NOT NULL,
    crisis_depth      INTEGER NOT NULL DEFAULT 0,
    recovery_signals  INTEGER NOT NULL DEFAULT 0,
    turns_in_phase   INTEGER NOT NULL DEFAULT 0,
    updated_at        DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_arc_user_channel ON emotional_arcs(channel_id, user_id);

-- ─── stance_log ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stance_log (
    id          BIGSERIAL PRIMARY KEY,
    channel_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    topic       TEXT NOT NULL,
    position    TEXT NOT NULL,
    confidence  DOUBLE PRECISION NOT NULL,
    timestamp   DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stance_channel_user ON stance_log(channel_id, user_id, timestamp DESC);

-- ─── contradiction_log ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contradiction_log (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 TEXT NOT NULL,
    prior_statement         TEXT NOT NULL,
    contradicting_statement TEXT NOT NULL,
    topic                   TEXT NOT NULL,
    called_out              INTEGER NOT NULL DEFAULT 0,
    timestamp               DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_contradiction_user ON contradiction_log(user_id, timestamp DESC);

-- ─── guild_config ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id             TEXT PRIMARY KEY,
    category_id          TEXT,
    facts_channel_id     TEXT,
    reminders_channel_id TEXT,
    setup_complete       INTEGER NOT NULL DEFAULT 0
);

-- ─── fact_consolidation_log ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_consolidation_log (
    id                BIGSERIAL PRIMARY KEY,
    run_ts            DOUBLE PRECISION NOT NULL,
    user_id           TEXT NOT NULL,
    fact_id_before    BIGINT,
    fact_id_after     BIGINT,
    op                TEXT NOT NULL CHECK(op IN ('ADD','UPDATE','DELETE','NOOP')),
    reason            TEXT,
    fact_text_before  TEXT,
    fact_text_after   TEXT
);
CREATE INDEX IF NOT EXISTS idx_fcl_run_ts ON fact_consolidation_log(run_ts);
CREATE INDEX IF NOT EXISTS idx_fcl_user_id ON fact_consolidation_log(user_id);

-- ─── dream_diary ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dream_diary (
    id                BIGSERIAL PRIMARY KEY,
    run_ts            DOUBLE PRECISION NOT NULL,
    duration_ms       INTEGER NOT NULL,
    users_total       INTEGER NOT NULL,
    users_processed   INTEGER NOT NULL,
    facts_in_total    INTEGER NOT NULL,
    facts_out_total   INTEGER NOT NULL,
    deletes_total     INTEGER NOT NULL,
    updates_total     INTEGER NOT NULL,
    status            TEXT NOT NULL CHECK(status IN ('ok','partial','failed')),
    content           TEXT NOT NULL,
    error             TEXT
);
CREATE INDEX IF NOT EXISTS idx_dream_diary_run_ts ON dream_diary(run_ts DESC);

-- ─── vectors: fact embeddings (replaces sqlite-vec) ───────────────────
-- pgvector — fixed-dim float vectors. EMBEDDING_DIM in core/vectors.py is
-- 384 because the model in use is `all-MiniLM-L6-v2`. The schema MUST match
-- the model dimension exactly or asyncpg/pgvector will reject inserts with
-- "expected N dimensions, got M".
CREATE TABLE IF NOT EXISTS fact_embeddings (
    fact_id   BIGINT PRIMARY KEY REFERENCES user_facts(id) ON DELETE CASCADE,
    embedding VECTOR(384) NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL
);
-- IVFFlat is the standard approximate-NN index. lists tuning depends on row
-- count: rule-of-thumb sqrt(N). Start with 100 — re-tune when row count
-- crosses ~10k facts per user × users.
CREATE INDEX IF NOT EXISTS idx_fact_embeddings_cos
    ON fact_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── serenityops_snapshots (v3.8.0 sync) ──────────────────────────────
-- Append-only feed of structured professional data pushed from each user's
-- local SerenityOps install. One row per /sync-insult invocation; the bot
-- reads only the latest per user at prompt-build time. JSONB so we can
-- evolve curriculum/opportunities schemas without ALTERs here.
CREATE TABLE IF NOT EXISTS serenityops_snapshots (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            TEXT NOT NULL,
    snapshot_at        DOUBLE PRECISION NOT NULL,
    curriculum_json    JSONB,
    opportunities_json JSONB,
    client_version     TEXT,
    source             TEXT NOT NULL DEFAULT 'serenityops-lite'
);
CREATE INDEX IF NOT EXISTS idx_serenityops_user_recent
    ON serenityops_snapshots(user_id, snapshot_at DESC);

-- ─── user_sync_tokens (v3.8.0 sync) ───────────────────────────────────
-- Per-user bearer tokens for the /sync/* endpoints. Stored as a hash so a
-- DB leak doesn't yield usable credentials. Plaintext is shown to the user
-- exactly once (via DM) at generation time and never persisted server-side.
-- Rotating: insert a new row + soft-delete the previous via revoked_at.
CREATE TABLE IF NOT EXISTS user_sync_tokens (
    id           BIGSERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL,
    token_hash   TEXT NOT NULL UNIQUE,
    created_at   DOUBLE PRECISION NOT NULL,
    last_used_at DOUBLE PRECISION,
    revoked_at   DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_user_sync_tokens_lookup
    ON user_sync_tokens(token_hash) WHERE revoked_at IS NULL;
