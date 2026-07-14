"""Per-slot session pool — the long-lived ClaudeSDKClients and their lifecycle.

Each pool slot maps to a ClaudeSDKClient already entered (`__aenter__` called).
Subsequent turns for the same slot reuse the client → the SDK auto-continues the
session → the prompt cache hits the persona + tool defs + CLAUDE.md. Opening a
fresh client per turn paid the full system prompt (~14k tokens for the persona
alone) EVERY turn; reuse drops a warm turn to ~500-2k.

Slot key: the bare `channel_id` for the default persona, `channel_id:persona_id`
for a sibling — so Insult and Vultur in the same channel never share one SDK
session (and never leak each other's thread).

Concurrency:
- `_pool_lock` protects pool dict mutations (add/evict/remove).
- `_channel_locks` holds one Lock per slot, serializing queries against that
  slot's client (ClaudeSDKClient is bidirectional, but a single
  query/receive_response sequence is NOT concurrency-safe).
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

import structlog

from persona_runner.core import config
from persona_runner.engine.options import build_options
from persona_runner.engine.persona_files import load_persona

log = structlog.get_logger()

_pool: dict[str, Any] = {}  # slot key → ClaudeSDKClient (entered)
_pool_last_used: dict[str, float] = {}  # slot key → unix ts
_pool_models: dict[str, str] = {}  # slot key → model chosen at session creation
_channel_locks: dict[str, asyncio.Lock] = {}  # slot key → Lock
_pool_lock = asyncio.Lock()


def pool_key(channel_id: str, persona_id: str | None) -> str:
    """Session-pool key. The default persona (persona_id=None) keeps the bare
    channel_id so existing sessions are untouched; a sibling persona gets its own
    `channel_id:persona_id` slot."""
    return channel_id if not persona_id else f"{channel_id}:{persona_id}"


def slot_lock(key: str) -> asyncio.Lock:
    """The per-slot lock, created on first use. Held around query+receive."""
    return _channel_locks.setdefault(key, asyncio.Lock())


def pool_size() -> int:
    return len(_pool)


def is_open(key: str) -> bool:
    return key in _pool


def model_for(key: str) -> str:
    """Model chosen when this slot's session was created (router decision), or the
    default for legacy callers / slots not yet open."""
    return _pool_models.get(key, config.DEFAULT_MODEL)


def keys_for_channel(channel_id: str) -> list[str]:
    """Every open slot belonging to a channel: the default-persona slot plus one
    per sibling (`channel_id:persona_id`).

    Exists because a channel is no longer one session. The reset endpoint used to
    close only the bare `channel_id`, so a stuck Vultur/Frugívoro/ALICE session in
    that channel survived the reset silently (bug found while modularizing,
    2026-07-14).
    """
    prefix = f"{channel_id}:"
    return [k for k in _pool if k == channel_id or k.startswith(prefix)]


async def _route_model(channel_id: str, user_id: str, user_text: str) -> tuple[str, dict[str, Any]]:
    """Run the 3-tier router (Haiku/Sonnet/Opus) for a session about to open.

    The chosen model sticks for the session's lifetime (see routing/router_runtime
    for per-session stickiness vs per-turn rerouting). Every failure falls back to
    DEFAULT_MODEL — a routing fault must never cost the turn.
    """
    from persona_runner.routing.router_runtime import route_for_session

    pg_conn = None
    try:
        from persona_runner.mcp_tools import _connect as _pg_connect

        pg_conn = await _pg_connect()
        decision = await route_for_session(
            channel_id=channel_id,
            user_id=user_id,
            user_text=user_text,
            pg_conn=pg_conn,
        )
        return decision.model, {
            "routed": True,
            "tier": decision.tier,
            "reason": decision.reason,
            "preset_mode": decision.preset_mode,
            "preset_modifiers": decision.preset_modifiers,
            "disclosure_severity": decision.disclosure_severity,
            "forced": decision.forced,
        }
    except Exception:
        log.exception("agent_runner_router_failed", channel_id=channel_id)
        return config.DEFAULT_MODEL, {"routed": False, "reason": "exception_fallback"}
    finally:
        if pg_conn is not None:
            with contextlib.suppress(Exception):
                await pg_conn.close()


async def _evict_lru_until_room(for_key: str) -> None:
    """Close least-recently-used slots until there is room for a new one.

    A slot mid-turn refreshed its last_used at turn start, so an in-flight session
    is only ever the LRU pick when EVERY slot is busy — at which point the box is
    past its concurrency budget anyway and that turn's error path rebuilds cleanly.
    Caller MUST hold `_pool_lock`.
    """
    while len(_pool) >= config.MAX_POOL_SESSIONS:
        lru_key = min(_pool, key=lambda k: _pool_last_used.get(k, 0.0))
        evicted = _pool.pop(lru_key, None)
        _pool_last_used.pop(lru_key, None)
        _channel_locks.pop(lru_key, None)
        _pool_models.pop(lru_key, None)
        if evicted is None:
            continue
        try:
            await evicted.__aexit__(None, None, None)
            log.info(
                "agent_runner_session_evicted_lru",
                evicted_key=lru_key,
                for_key=for_key,
                pool_size=len(_pool),
                max_pool=config.MAX_POOL_SESSIONS,
            )
        except Exception:
            log.exception("agent_runner_session_evict_failed", evicted_key=lru_key)


async def get_or_create_client(
    channel_id: str,
    *,
    persona_id: str | None = None,
    user_id: str | None = None,
    user_text: str | None = None,
) -> Any:
    """Return this slot's ClaudeSDKClient, creating + entering it if absent.

    Caller MUST hold the per-slot lock before calling `query` on the result.
    When user_id/user_text are provided, a NEW session runs the model router; the
    decision sticks for the session. Without them (legacy callers, tests) the
    session opens on DEFAULT_MODEL.
    """
    from claude_agent_sdk import ClaudeSDKClient

    key = pool_key(channel_id, persona_id)
    async with _pool_lock:
        existing = _pool.get(key)
        if existing is not None:
            _pool_last_used[key] = time.time()
            return existing

        await _evict_lru_until_room(key)

        chosen_model = config.DEFAULT_MODEL
        route_meta: dict[str, Any] = {"routed": False}
        if user_id and user_text:
            chosen_model, route_meta = await _route_model(channel_id, user_id, user_text)

        persona = load_persona(persona_id)
        options = await build_options(persona, model=chosen_model)
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        _pool[key] = client
        _pool_models[key] = chosen_model
        _pool_last_used[key] = time.time()
        log.info(
            "agent_runner_session_created",
            channel_id=channel_id,
            persona_id=persona_id or "insult",
            model=chosen_model,
            pool_size=len(_pool),
            **route_meta,
        )
        return client


async def close_client(key: str) -> None:
    """Close + remove ONE slot's client. Safe to call when absent."""
    async with _pool_lock:
        client = _pool.pop(key, None)
        _pool_last_used.pop(key, None)
        _channel_locks.pop(key, None)
        _pool_models.pop(key, None)
    if client is None:
        return
    try:
        await client.__aexit__(None, None, None)
        log.info("agent_runner_session_closed", key=key)
    except Exception:
        log.exception("agent_runner_session_close_failed", key=key)


async def close_channel(channel_id: str) -> list[str]:
    """Close EVERY open slot of a channel (default persona + all siblings).

    Returns the keys that were open. This is what the reset endpoint needs: a
    channel hosts up to one session per persona, and a poisoned belief lives in
    the session that holds it — closing only the bare channel_id left the sibling
    sessions poisoned.
    """
    keys = keys_for_channel(channel_id)
    for key in keys:
        await close_client(key)
    return keys


async def close_all() -> None:
    """Shutdown path: close every open slot."""
    open_keys = list(_pool.keys())
    log.info("agent_runner_shutdown_closing_sessions", count=len(open_keys))
    for key in open_keys:
        await close_client(key)


async def reap_idle_sessions() -> None:
    """Background task: close clients idle longer than config.SESSION_IDLE_TIMEOUT_S.

    Frees the Node subprocess memory and lets Anthropic's 5-min cache TTL roll
    naturally — a session idle past the TTL has nothing warm left to protect.
    """
    while True:
        await asyncio.sleep(60)
        try:
            now = time.time()
            stale = [k for k, ts in list(_pool_last_used.items()) if now - ts > config.SESSION_IDLE_TIMEOUT_S]
            for key in stale:
                log.info(
                    "agent_runner_session_reap",
                    key=key,
                    idle_s=int(now - _pool_last_used.get(key, now)),
                )
                await close_client(key)
        except Exception:
            log.exception("agent_runner_reaper_iteration_failed")
