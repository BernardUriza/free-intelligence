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

-- ─── MIGRATION v3.10.0: user_facts → principal_facts ───────────────────
-- One-shot idempotent rename for the fi_core.memory integration.
-- The fi-core extraction (PgMemoryStore, 0.7.0) uses generic
-- `principal_facts(principal_id, ...)` instead of Discord-specific
-- `user_facts(user_id, ...)`. We migrate to the fi-core naming so the
-- same DAL serves Insult, AURITY, and any future consumer.
--
-- Runs BEFORE the CREATE TABLE IF NOT EXISTS blocks below so that an
-- existing user_facts deployment is renamed in place; on a fresh
-- deploy the rename is a no-op (user_facts doesn't exist) and the
-- CREATE TABLE IF NOT EXISTS principal_facts block does the work.
DO $$
BEGIN
    -- Rename principal table + column, only if old exists and new doesn't.
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'user_facts')
       AND NOT EXISTS (SELECT FROM pg_tables WHERE tablename = 'principal_facts') THEN
        ALTER TABLE user_facts RENAME TO principal_facts;
        ALTER TABLE principal_facts RENAME COLUMN user_id TO principal_id;
        -- Drop old-name indexes; new ones get created by the CREATE INDEX
        -- IF NOT EXISTS block below.
        DROP INDEX IF EXISTS idx_user_facts;
        DROP INDEX IF EXISTS idx_user_facts_deleted_at;
    END IF;

    -- Rename audit log column too. The table name stays
    -- fact_consolidation_log; only the user_id column needs to be
    -- principal_id to match fi-core.
    IF EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'fact_consolidation_log'
          AND column_name = 'user_id'
    ) THEN
        ALTER TABLE fact_consolidation_log RENAME COLUMN user_id TO principal_id;
        DROP INDEX IF EXISTS idx_fcl_user_id;
    END IF;
END
$$;

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
    model_used      TEXT,
    discord_message_id TEXT
);
-- MIGRATION v4.21.116: dedupe key for multi-writer stores. Both the Insult
-- plumbing (canonical storage gateway) and each persona_gateway sibling
-- receive the same Discord message on their own gateway connections and
-- persist it — without this key every sibling-addressed turn lands twice
-- (observed 7ms apart in prod, 2026-07-05). The unique partial index +
-- ON CONFLICT DO NOTHING in MessagesRepository.store makes the write
-- idempotent per Discord message regardless of writer topology. NULL ids
-- (bot replies, proactive turns) never conflict by design.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS discord_message_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_discord_id
    ON messages(discord_message_id) WHERE discord_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_channel_ts ON messages(channel_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_context ON messages(channel_id, user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_for_user ON messages(channel_id, for_user_id, timestamp DESC);

-- ─── user_profiles ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id      TEXT PRIMARY KEY,
    profile_json JSONB NOT NULL,
    updated_at   DOUBLE PRECISION NOT NULL
);

-- ─── principal_facts (formerly user_facts) ────────────────────────────
-- Renamed in v3.10.0 to align with fi_core.memory.PgMemoryStore.
-- Discord-bot keeps using string user IDs as principal_id values — the
-- column name change is cosmetic at the data level, semantic at the
-- abstraction layer (any tenant key works now, not just Discord users).
CREATE TABLE IF NOT EXISTS principal_facts (
    id            BIGSERIAL PRIMARY KEY,
    principal_id  TEXT NOT NULL,
    fact          TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'general',
    updated_at    DOUBLE PRECISION NOT NULL,
    source        TEXT NOT NULL DEFAULT 'auto',
    deleted_at    DOUBLE PRECISION DEFAULT NULL,
    embedding     vector
);
-- MIGRATION v4.1.0: inline embedding column for fi_core.memory.PgMemoryStore.
-- The `embedding` column above only lands on FRESH databases (CREATE TABLE IF
-- NOT EXISTS skips existing tables). Prod's principal_facts predates the
-- column — it was carried by the standalone `fact_embeddings` table before.
-- The fi-core hot path (semantic_search + inline write) reads/writes THIS
-- column, so existing deployments must gain it via ALTER. Idempotent: a no-op
-- where the column already exists (fresh DBs, re-runs). connect() applies this
-- on every boot, so the column exists before the first facts turn.
ALTER TABLE principal_facts ADD COLUMN IF NOT EXISTS embedding vector;
CREATE INDEX IF NOT EXISTS idx_pf_principal ON principal_facts(principal_id);
CREATE INDEX IF NOT EXISTS idx_pf_deleted_at ON principal_facts(deleted_at) WHERE deleted_at IS NOT NULL;

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

-- ─── siesta_state ──────────────────────────────────────────────────────
-- Cross-process Siesta coordination (v3.9.46, POST-DEPLOY-1). Replaces
-- the old `memory.db` blob metadata hijack. Singleton row keyed by a
-- constant ('current') — the consolidator job and the bot replica both
-- read/write this same row. UPSERT on phase change; the bot poller
-- reads it every 30s. Default empty/AWAKE when the row is absent.
CREATE TABLE IF NOT EXISTS siesta_state (
    singleton         TEXT PRIMARY KEY CHECK (singleton = 'current'),
    phase             TEXT NOT NULL,
    started_at        TIMESTAMPTZ,
    total_users       INTEGER NOT NULL DEFAULT 0,
    processed_users   INTEGER NOT NULL DEFAULT 0,
    current_user_id   TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── deep_memory_chunks ────────────────────────────────────────────────
-- Vector-searchable per-user memory chunks (v3.9.60, RAG sibling).
-- Replaces the on-prem Free Intelligence / AURITY RAG dependency for
-- Insult's "deep memory" needs — Insult's audience is conversational, not
-- clinical PHI, so HIPAA on-prem isolation doesn't apply.
--
-- Population: an ingest pipeline (siesta consolidator hook + manual
-- backfill script) chunks messages and disclosure_log rows into
-- ~500-token windows, embeds via Azure OpenAI ada-002 (1536 dims), and
-- inserts here. The MCP tool `mcp__insult_db__deep_memory(user_id, query,
-- top_k)` embeds the query and runs `embedding <=> $1` cosine search
-- filtered by user_id.
--
-- `source_type` + `source_ref` lets the agent cite where a recalled chunk
-- came from ("from your message on 2026-04-12" beats a context-free quote).
CREATE TABLE IF NOT EXISTS deep_memory_chunks (
    id              BIGSERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK (source_type IN ('message', 'disclosure', 'fact', 'manual')),
    source_ref      TEXT NOT NULL,
    chunk_text      TEXT NOT NULL,
    embedding       vector(1536) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Idempotent ingest guard: same source_ref + chunk_text combo never inserts twice.
CREATE UNIQUE INDEX IF NOT EXISTS idx_deep_memory_dedupe ON deep_memory_chunks(user_id, source_ref, md5(chunk_text));
-- User filter + recency ordering for "what does X look like lately".
CREATE INDEX IF NOT EXISTS idx_deep_memory_user_created ON deep_memory_chunks(user_id, created_at DESC);
-- Vector search index. ivfflat with lists=100 is the standard pgvector
-- starting point for tables <1M rows; revisit if we cross that. The
-- ANALYZE that follows the first big insert determines the planner's
-- statistics for the cosine operator.
CREATE INDEX IF NOT EXISTS idx_deep_memory_embedding ON deep_memory_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── html_artifacts ────────────────────────────────────────────────────
-- HTML artifacts the agent publishes via `publish_html_artifact`. Served
-- by `discord-bot`'s public GET /a/{id} endpoint — no auth, anyone with
-- the short id can view. v3.9.57 (HTML artifacts feature).
-- `id` is a short URL-safe slug (12 chars from secrets.token_urlsafe);
-- collision is statistically irrelevant for this volume.
CREATE TABLE IF NOT EXISTS html_artifacts (
    id                   TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    html_content         TEXT NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_user_id   TEXT,
    view_count           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_html_artifacts_created_at ON html_artifacts(created_at DESC);

-- ─── fact_consolidation_log ────────────────────────────────────────────
-- principal_id column renamed in v3.10.0 (was user_id).
CREATE TABLE IF NOT EXISTS fact_consolidation_log (
    id                BIGSERIAL PRIMARY KEY,
    run_ts            DOUBLE PRECISION NOT NULL,
    principal_id      TEXT NOT NULL,
    fact_id_before    BIGINT,
    fact_id_after     BIGINT,
    op                TEXT NOT NULL CHECK(op IN ('ADD','UPDATE','DELETE','NOOP')),
    reason            TEXT,
    fact_text_before  TEXT,
    fact_text_after   TEXT
);
CREATE INDEX IF NOT EXISTS idx_fcl_run_ts ON fact_consolidation_log(run_ts);
CREATE INDEX IF NOT EXISTS idx_fcl_principal ON fact_consolidation_log(principal_id);

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
    fact_id   BIGINT PRIMARY KEY REFERENCES principal_facts(id) ON DELETE CASCADE,
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

-- ─── agents + agent_facts (v4.20.14 — PR-1: bot self-knowledge) ────────
-- The bots learn facts about THEMSELVES, not just about users. Insult and
-- ALICE are rows in `agents`; their self-knowledge lives in `agent_facts`,
-- a mirror of `principal_facts` with two differences the brief mandated:
--   1. the owner is an AGENT (`agent_id` FK), not a user `principal_id`.
--   2. `provenance` is a FIRST-CLASS column (not buried like `source`):
--      who declared this fact about the bot — the bot itself, a user, the
--      system prompt, or a consolidation pass. principal_facts.source can't
--      express that distinction, so agent_facts gets its own enum.
-- Scope (PR-1): storage + read/write/update MCP tools ONLY. NO auto-write
-- of facts from the message pipeline, NO touching user_facts consolidation —
-- those are PR-2. The `embedding` column mirrors principal_facts for forward
-- compatibility but is NOT populated in PR-1.
CREATE TABLE IF NOT EXISTS agents (
    name        TEXT PRIMARY KEY,
    created_at  DOUBLE PRECISION NOT NULL
);
-- Seed the two live agents. Idempotent: re-running connect() never duplicates.
INSERT INTO agents (name, created_at)
VALUES ('insult', extract(epoch from now())),
       ('alice',  extract(epoch from now()))
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS agent_facts (
    id          BIGSERIAL PRIMARY KEY,
    agent_id    TEXT NOT NULL REFERENCES agents(name),
    fact        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    provenance  TEXT NOT NULL
                CHECK (provenance IN ('self_declared', 'user_attributed', 'system_prompt', 'consolidation')),
    updated_at  DOUBLE PRECISION NOT NULL,
    deleted_at  DOUBLE PRECISION DEFAULT NULL,
    embedding   vector
);
CREATE INDEX IF NOT EXISTS idx_af_agent ON agent_facts(agent_id);
CREATE INDEX IF NOT EXISTS idx_af_deleted_at ON agent_facts(deleted_at) WHERE deleted_at IS NOT NULL;
