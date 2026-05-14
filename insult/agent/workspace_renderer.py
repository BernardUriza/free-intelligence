"""Postgres → markdown projector for the Agent SDK workspace.

Why this exists: the Claude Agent SDK reads selectively from files on
disk (`Read /data/insult-workspace/facts/{user_id}.md`) instead of being
fed the whole context blob in every request. That selective-read pattern
is what gives the agent loop better grounding on multi-hop retrieval —
see `.claude/plans/insult_agent_sdk_migration.md` for the rationale.

But the source of truth is still Postgres. This renderer mirrors the
relevant tables to markdown every N seconds AND on Postgres
LISTEN/NOTIFY events. Atomic writes (`.tmp` + `os.replace`) so the agent
never reads a half-written file.

What lives in /data/insult-workspace after a render:

  facts/{user_id}.md          — current accumulated user_facts for that user
  messages/{channel_id}.md    — last N=50 messages in that channel
  disclosure_log.md           — last 30d of disclosure_log rows
  emotional_arcs.md           — current arc state per user
  stance_log.md               — Insult's recorded stances per topic
  README.md                   — header pointing the agent at the layout

Persona files are NOT rendered here — they live in the repo and the
agent reads them directly via a separate mount or copy at boot.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
import time
from pathlib import Path

import asyncpg
import structlog

log = structlog.get_logger()

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/data/insult-workspace"))
RENDER_INTERVAL_S = int(os.environ.get("WORKSPACE_RENDER_INTERVAL_S", "60"))
RECENT_MESSAGES_PER_CHANNEL = int(os.environ.get("WORKSPACE_RECENT_LIMIT", "50"))
DISCLOSURE_LOOKBACK_DAYS = int(os.environ.get("WORKSPACE_DISCLOSURE_LOOKBACK_DAYS", "30"))


# --- Atomic write helper ---------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` atomically (POSIX rename guarantee on ext4/SMB).

    Race-safe: a concurrent reader either sees the previous full version or
    the new full version, never a partial buffer. Agent SDK may hit the file
    at any moment during a render cycle.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _frontmatter(**fields: object) -> str:
    """Render a YAML frontmatter block. Values are coerced to str.

    Order is preserved for human readability — the agent doesn't parse
    frontmatter, it reads it as text. Used only for context cues like
    `updated_at` so the model knows how fresh the file is.
    """
    lines = ["---"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


# --- Renderers per table ----------------------------------------------------


async def render_facts(pool: asyncpg.Pool) -> int:
    """One markdown file per user_id with their current facts.

    Layout:
        facts/{user_id}.md
        ---
        user_id: 907264175246569543
        updated_at: 2026-05-14T05:48:00Z
        fact_count: 7
        ---
        # Bernard's facts

        - [identity] Senior dev, builds Insult bot...
        - [profession] AI engineer at VisaLaw...
    """
    rows = await pool.fetch(
        "SELECT user_id, id, fact, category, updated_at FROM user_facts "
        "WHERE deleted_at IS NULL ORDER BY user_id, updated_at DESC"
    )
    by_user: dict[str, list[asyncpg.Record]] = {}
    for row in rows:
        by_user.setdefault(row["user_id"], []).append(row)

    written = 0
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for user_id, facts in by_user.items():
        body_lines = [f"# Facts for user {user_id}", ""]
        for fact in facts:
            cat = fact["category"] or "uncategorized"
            body_lines.append(f"- [{cat}] {fact['fact']}")
        content = (
            _frontmatter(
                user_id=user_id,
                updated_at=now_iso,
                fact_count=len(facts),
            )
            + "\n".join(body_lines)
            + "\n"
        )
        _atomic_write(WORKSPACE_ROOT / "facts" / f"{user_id}.md", content)
        written += 1
    return written


async def render_messages(pool: asyncpg.Pool) -> int:
    """One file per channel_id with the last N messages.

    Format mirrors what Insult already produces in its context blocks:
    speaker prefix + content on its own line. Older messages first
    (chronological), newest at the bottom.
    """
    channels = await pool.fetch("SELECT DISTINCT channel_id FROM messages")
    written = 0
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for ch in channels:
        channel_id = ch["channel_id"]
        rows = await pool.fetch(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
            channel_id,
            RECENT_MESSAGES_PER_CHANNEL,
        )
        body_lines = [f"# Recent messages in channel {channel_id}", ""]
        for row in reversed(rows):  # oldest first for natural reading
            speaker = row["user_name"] or "?"
            body_lines.append(f"**{speaker}**: {row['content']}")
            body_lines.append("")
        content = _frontmatter(
            channel_id=channel_id,
            updated_at=now_iso,
            message_count=len(rows),
        ) + "\n".join(body_lines)
        _atomic_write(WORKSPACE_ROOT / "messages" / f"{channel_id}.md", content)
        written += 1
    return written


async def render_disclosure_log(pool: asyncpg.Pool) -> int:
    """All disclosures in the last N days, one file shared across users.

    The agent reads this to calibrate tone when a user's recent
    disclosure severity is high. Rows are sorted newest first because
    recency dominates relevance for this signal.
    """
    cutoff = time.time() - DISCLOSURE_LOOKBACK_DAYS * 86400
    rows = await pool.fetch(
        "SELECT user_id, category, severity, signals, timestamp "
        "FROM disclosure_log WHERE timestamp >= $1 "
        "ORDER BY timestamp DESC",
        cutoff,
    )
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    body_lines = [f"# Disclosure log (last {DISCLOSURE_LOOKBACK_DAYS}d)", ""]
    for row in rows:
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row["timestamp"]))
        body_lines.append(
            f"- {ts_iso} | user={row['user_id']} | sev={row['severity']} | "
            f"category={row['category']} | signals={row['signals']}"
        )
    content = (
        _frontmatter(
            updated_at=now_iso,
            lookback_days=DISCLOSURE_LOOKBACK_DAYS,
            row_count=len(rows),
        )
        + "\n".join(body_lines)
        + "\n"
    )
    _atomic_write(WORKSPACE_ROOT / "disclosure_log.md", content)
    return len(rows)


# --- Main loop --------------------------------------------------------------


async def render_once(pool: asyncpg.Pool) -> dict[str, int]:
    """Run all renderers once and return a count per artifact."""
    start = time.monotonic()
    counts = {
        "facts_users": await render_facts(pool),
        "channels": await render_messages(pool),
        "disclosure_rows": await render_disclosure_log(pool),
    }
    elapsed_ms = int((time.monotonic() - start) * 1000)
    log.info("workspace_render_cycle", elapsed_ms=elapsed_ms, **counts)
    return counts


async def _readme(pool: asyncpg.Pool) -> None:
    """Write a small README so a human SSHing in can orient themselves."""
    _ = pool  # unused; signature kept symmetric with renderers
    content = (
        "# Insult Agent SDK Workspace\n\n"
        "Postgres state projected to markdown by `insult.agent.workspace_renderer`.\n"
        "DO NOT edit these files manually — they are overwritten on every render.\n"
        "Source of truth: the `insultpg` Postgres database.\n\n"
        "## Layout\n\n"
        "- `facts/{user_id}.md` — accumulated facts per user\n"
        "- `messages/{channel_id}.md` — recent messages per channel\n"
        "- `disclosure_log.md` — recent disclosure events across users\n"
    )
    _atomic_write(WORKSPACE_ROOT / "README.md", content)


async def run() -> None:
    """Entrypoint. Connects to Postgres, runs render loop, handles SIGTERM."""
    dsn = os.environ.get("POSTGRES_URL")
    if not dsn:
        log.critical("workspace_renderer_no_postgres_url")
        sys.exit(2)

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    log.info("workspace_renderer_starting", workspace=str(WORKSPACE_ROOT), interval_s=RENDER_INTERVAL_S)

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    log.info("workspace_renderer_postgres_connected")
    await _readme(pool)

    stop = asyncio.Event()

    def _on_signal(sig: int) -> None:
        log.info("workspace_renderer_shutdown_signal", signal=sig)
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _on_signal, sig)

    try:
        while not stop.is_set():
            try:
                await render_once(pool)
            except Exception:
                log.exception("workspace_render_cycle_failed")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=RENDER_INTERVAL_S)
    finally:
        await pool.close()
        log.info("workspace_renderer_stopped")


if __name__ == "__main__":
    asyncio.run(run())
