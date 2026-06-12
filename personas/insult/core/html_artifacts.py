"""HTML artifact storage — agent-generated pages served by GET /a/{id}.

The Insult agent can publish standalone HTML pages (reports, mini-apps,
chat snapshots) via the `mcp__insult_db__publish_html_artifact` tool.
The discord-bot's debug HTTP server exposes a public `GET /a/{id}`
endpoint that streams the stored HTML back. The system is dynamic:
adding an artifact does NOT require a redeploy of anything.

Architecture mirrors `pg_state.py`: one-shot asyncpg connections per
call. Volume is low (probably a few artifacts per day), so a pool is
overkill and would couple this module to the debug server's lifecycle.

ID generation: `secrets.token_urlsafe(8)` gives 11 URL-safe chars,
~64 bits of entropy. Collisions are statistically irrelevant at any
realistic volume. The ID lives in the URL path so we use only chars
that don't need percent-encoding.

Public exposure note: the GET /a/{id} endpoint is unauthenticated.
Anyone with the short id can view the artifact. Treat artifacts as
shareable-by-link content — do NOT publish anything with secrets.
"""

from __future__ import annotations

import os
import secrets

import asyncpg
import structlog

log = structlog.get_logger()


async def _connect() -> asyncpg.Connection | None:
    """One-shot Postgres connection. Returns None when PG is unreachable."""
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        return await asyncpg.connect(url)
    except Exception:
        log.exception("html_artifacts_pg_connect_failed")
        return None


def _new_id() -> str:
    """Short URL-safe id. 11 chars, ~64 bits of entropy."""
    return secrets.token_urlsafe(8)


async def insert_artifact(*, title: str, html_content: str, created_by_user_id: str | None = None) -> str | None:
    """Insert a new artifact, return the generated id (or None on failure).

    Title and html_content are mandatory; created_by_user_id is optional
    (the agent may publish artifacts not tied to a specific user, e.g.
    snapshot pages summarizing multiple users).
    """
    if not title or not html_content:
        return None
    conn = await _connect()
    if conn is None:
        return None
    artifact_id = _new_id()
    try:
        await conn.execute(
            """
            INSERT INTO html_artifacts (id, title, html_content, created_by_user_id)
            VALUES ($1, $2, $3, $4)
            """,
            artifact_id,
            title,
            html_content,
            created_by_user_id,
        )
        log.info(
            "html_artifact_published",
            id=artifact_id,
            title=title[:80],
            size_bytes=len(html_content),
            created_by_user_id=created_by_user_id,
        )
        return artifact_id
    except Exception:
        log.exception("html_artifact_insert_failed")
        return None
    finally:
        await conn.close()


async def get_artifact(artifact_id: str) -> dict | None:
    """Fetch an artifact by id. Returns None if not found.

    Also increments view_count atomically so we can see which artifacts
    are actually being looked at. Counter is best-effort — a failure to
    increment never blocks the read.
    """
    if not artifact_id:
        return None
    conn = await _connect()
    if conn is None:
        return None
    try:
        row = await conn.fetchrow(
            "SELECT id, title, html_content, created_at, view_count FROM html_artifacts WHERE id = $1",
            artifact_id,
        )
        if row is None:
            return None
        # Best-effort view increment; never raises.
        try:
            await conn.execute(
                "UPDATE html_artifacts SET view_count = view_count + 1 WHERE id = $1",
                artifact_id,
            )
        except Exception:
            log.warning("html_artifact_view_increment_failed", id=artifact_id)
        return {
            "id": row["id"],
            "title": row["title"],
            "html_content": row["html_content"],
            "created_at": row["created_at"],
            "view_count": row["view_count"],
        }
    except Exception:
        log.exception("html_artifact_read_failed", id=artifact_id)
        return None
    finally:
        await conn.close()
