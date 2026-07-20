"""Shared plumbing for the insult_db MCP tools — PG connection + result envelopes.

Architecture mirrors `pg_state.py`: one-shot asyncpg connections per
tool call. The agent invokes tools rarely enough (a few per turn) that
a shared pool is overkill and would force coupling to the runner's
event loop lifecycle.
"""

from __future__ import annotations

import os

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
        log.exception("mcp_tools_pg_connect_failed")
        return None


def _text(payload: str) -> dict:
    """Wrap a string into the MCP tool-result content envelope."""
    return {"content": [{"type": "text", "text": payload}]}


def _error(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}
