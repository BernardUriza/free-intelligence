"""The gateway's memory (#30): both halves of every proxied exchange, appended.

``aire_gateway_log`` is a NEW append-only table, created lazily over the
daemon's own DSN — role ``aire``, so the reader's ``ALTER DEFAULT PRIVILEGES``
grant covers it the moment it exists ([[write-only-daemon]]). One ``request``
row lands before the relay starts, one ``response`` row when the stream ends,
correlated by ``exchange``; correcting means appending, never an UPDATE
([[log-is-the-truth]]). The mirror is best-effort by design: every failure here
is printed and swallowed — the relay is the critical path and must never pay
for its memory. This module NEVER touches ``claude_session_store`` or
``aire_log``; the gateway sees raw API turns, a different granularity.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .gateway_assemble import assemble

_pool: Any = None

DDL = """
CREATE TABLE IF NOT EXISTS aire_gateway_log (
  seq             bigserial PRIMARY KEY,
  ts              timestamptz NOT NULL DEFAULT now(),
  exchange        text NOT NULL,
  kind            text NOT NULL,
  session_id      text,
  agent_id        text,
  parent_agent_id text,
  project         text,
  model           text,
  body            jsonb,
  stop_reason     text,
  usage           jsonb,
  status          int
);
CREATE INDEX IF NOT EXISTS aire_gateway_log_session_idx
  ON aire_gateway_log (session_id);
CREATE INDEX IF NOT EXISTS aire_gateway_log_exchange_idx
  ON aire_gateway_log (exchange);
"""


def _dsn() -> str:
    return os.environ.get("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")


async def _get_pool() -> Any:
    global _pool
    if _pool is None:
        import asyncpg
        _pool = await asyncpg.create_pool(_dsn(), min_size=0, max_size=2)
        await _pool.execute(DDL)
    return _pool


async def reset() -> None:
    """Drop the cached pool (tests, or a database that went away and came back)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def log_request(exchange: str, headers: Any, body: bytes) -> None:
    """Append the request half before the relay starts. Never raises."""
    try:
        parsed = json.loads(body) if body else None
        await (await _get_pool()).execute(
            "INSERT INTO aire_gateway_log (exchange, kind, session_id, agent_id,"
            " parent_agent_id, project, model, body)"
            " VALUES ($1, 'request', $2, $3, $4, $5, $6, $7::jsonb)",
            exchange,
            headers.get("x-claude-code-session-id"),
            headers.get("x-claude-code-agent-id"),
            headers.get("x-claude-code-parent-agent-id"),
            headers.get("x-aire-project"),
            parsed.get("model") if isinstance(parsed, dict) else None,
            json.dumps(parsed) if parsed is not None else None)
    except Exception as exc:  # noqa: BLE001 — the relay never pays for the mirror
        print(f"GATEWAY-MIRROR request append failed: {type(exc).__name__}: {exc}")


class ResponseTap:
    """Accumulates the relayed bytes on the side; on finish, assembles the final
    message (gateway_assemble) and appends the response half. Feeding is
    synchronous and cheap — the relay yields each chunk before anything else.

    `on_usage` is how an invited key pays for the credential AIRE lent it (#32).
    It runs in its OWN try, before the mirror's: the mirror is best-effort by
    design, and letting a dead database silence a charge would make the spend
    ceiling depend on the logger."""

    def __init__(self, exchange: str, status: int, content_type: str,
                 on_usage: Any = None) -> None:
        self.exchange, self.status, self.content_type = exchange, status, content_type
        self.on_usage = on_usage
        self.raw = bytearray()
        self.done = False

    def feed(self, chunk: bytes) -> None:
        self.raw.extend(chunk)

    async def finish(self) -> None:
        if self.done:
            return
        self.done = True
        message = assemble(bytes(self.raw), self.content_type)
        fields = message if isinstance(message, dict) else {}
        if self.on_usage is not None:
            try:
                await self.on_usage(fields.get("usage"), str(fields.get("model") or ""))
            except Exception as exc:  # noqa: BLE001 — loud: an uncharged turn is free money
                print(f"GATEWAY-BILLING failed: {type(exc).__name__}: {exc}", flush=True)
        try:
            await _append_response(self, message)
        except Exception as exc:  # noqa: BLE001 — same law as log_request
            print(f"GATEWAY-MIRROR response append failed: {type(exc).__name__}: {exc}")


async def _append_response(tap: ResponseTap, message: Any) -> None:
    fields = message if isinstance(message, dict) else {}
    await (await _get_pool()).execute(
        "INSERT INTO aire_gateway_log (exchange, kind, model, body, stop_reason,"
        " usage, status) VALUES ($1, 'response', $2, $3::jsonb, $4, $5::jsonb, $6)",
        tap.exchange,
        fields.get("model"),
        json.dumps(message) if message is not None else None,
        fields.get("stop_reason"),
        json.dumps(fields["usage"]) if fields.get("usage") else None,
        tap.status)
