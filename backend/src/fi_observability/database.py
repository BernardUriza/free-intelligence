# fi_observability/database.py
# SQLite database for LLM call persistence

import logging
import sqlite3
from contextlib import contextmanager
from typing import Generator

import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database location
DEFAULT_DB_PATH = Path(os.getenv("FI_OBSERVABILITY_DB", "/tmp/fi_observability.db"))

# For Windows compatibility
if os.name == "nt":
    DEFAULT_DB_PATH = Path(
        os.getenv(
            "FI_OBSERVABILITY_DB",
            os.path.join(os.environ.get("TEMP", "C:/Temp"), "fi_observability.db"),
        )
    )


SCHEMA = """
-- LLM Calls table
CREATE TABLE IF NOT EXISTS llm_calls (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Model info
    model TEXT NOT NULL,
    provider TEXT NOT NULL,

    -- Tokens
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,

    -- Timing
    latency_ms INTEGER DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'success',
    error_message TEXT,

    -- Content previews
    prompt_preview TEXT,
    response_preview TEXT,

    -- Context
    client_id TEXT,
    session_id TEXT,
    persona TEXT,

    -- Hashes
    prompt_hash TEXT,
    response_hash TEXT,

    -- Extra
    metadata TEXT DEFAULT '{}'
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_llm_calls_timestamp ON llm_calls(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_llm_calls_client_id ON llm_calls(client_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_model ON llm_calls(model);
CREATE INDEX IF NOT EXISTS idx_llm_calls_status ON llm_calls(status);
CREATE INDEX IF NOT EXISTS idx_llm_calls_persona ON llm_calls(persona);

-- Composite index for client reports
CREATE INDEX IF NOT EXISTS idx_llm_calls_client_timestamp
    ON llm_calls(client_id, timestamp DESC);

-- View for quick stats
CREATE VIEW IF NOT EXISTS v_call_stats AS
SELECT
    DATE(timestamp) as date,
    model,
    provider,
    COUNT(*) as total_calls,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_calls,
    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_calls,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(completion_tokens) as total_completion_tokens,
    AVG(latency_ms) as avg_latency_ms
FROM llm_calls
GROUP BY DATE(timestamp), model, provider;

-- View for client summary
CREATE VIEW IF NOT EXISTS v_client_summary AS
SELECT
    client_id,
    COUNT(*) as total_calls,
    SUM(prompt_tokens + completion_tokens) as total_tokens,
    AVG(latency_ms) as avg_latency_ms,
    MIN(timestamp) as first_call,
    MAX(timestamp) as last_call
FROM llm_calls
WHERE client_id IS NOT NULL
GROUP BY client_id;
"""


_db_path: Path = DEFAULT_DB_PATH
_initialized: bool = False


def init_observability_db(db_path: Path | str | None = None) -> None:
    """Initialize the observability database."""
    global _db_path, _initialized

    if db_path:
        _db_path = Path(db_path)

    # Ensure directory exists
    _db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initializing observability database at {_db_path}")

    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()

    _initialized = True
    logger.info("Observability database initialized")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection]:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(_db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_initialized() -> None:
    """Ensure database is initialized."""
    global _initialized
    if not _initialized:
        init_observability_db()


def cleanup_old_records(days: int = 30) -> int:
    """Delete records older than specified days. Returns count deleted."""
    ensure_initialized()

    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM llm_calls WHERE timestamp < datetime('now', ?)", (f"-{days} days",)
        )
        conn.commit()
        deleted = cursor.rowcount

    logger.info(f"Cleaned up {deleted} records older than {days} days")
    return deleted


def get_db_stats() -> dict:
    """Get database statistics."""
    ensure_initialized()

    with get_connection() as conn:
        # Total records
        total = conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]

        # DB file size
        db_size = _db_path.stat().st_size if _db_path.exists() else 0

        # Date range
        date_range = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM llm_calls").fetchone()

        return {
            "total_records": total,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "db_path": str(_db_path),
            "oldest_record": date_range[0],
            "newest_record": date_range[1],
        }
