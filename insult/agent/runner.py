"""FastAPI service hosting the Claude Agent SDK loop for Insult.

Endpoint contract (called by `insult.core.llm.agent_client.AgentRunnerClient`
from the Insult Container App, behind a per-user feature flag):

    POST /v1/turn
    Authorization: Bearer <INSULT_AGENT_RUNNER_TOKEN>
    Content-Type: application/json
    {
      "channel_id": "1489...",
      "user_id": "907...",
      "user_text": "lo que el usuario acaba de mandar",
      "session_uuid": "<previous-uuid-or-null>"  # currently ignored — long-lived
                                                  # client per channel handles continuity
    }

    -> 200 OK
    {
      "text": "respuesta del agente",
      "session_uuid": "<uuid-for-next-turn>",
      "input_tokens": 0,
      "output_tokens": 0,
      "model": "claude-sonnet-4-6",
      "stop_reason": "end_turn",
      "tool_calls": [{"name": "Read", "input_keys": [...]}, ...]
    }

The agent reads selectively from `/data/insult-workspace/*.md` (populated
by the workspace_renderer) via Read/Grep/Glob tools. The full conversation
context is NOT inlined into the request — only the latest user message is
forwarded; earlier turns live in the workspace already.

## Long-lived per-channel sessions (v3.9.31)

The previous flow opened a fresh `ClaudeSDKClient` per turn (`async with
ClaudeSDKClient(...) as client`). That paid the full system prompt cost
(~14k tokens for persona.md alone) on EVERY turn — no prompt cache reuse,
no conversation continuity in the SDK session. Bernard's discord DM bursts
quickly hit Claude Code's per-window token limits because the runner kept
re-loading persona.md + CLAUDE.md + the workspace Read every time.

Now: we maintain a `ClaudeSDKClient` instance PER channel_id in module
state, opened with `__aenter__` and reused across turns. The SDK
auto-continues the same session (per the `ClaudeSDKClient handles session
IDs internally, each call to client.query() automatically continues the
same session` doc — see https://platform.claude.com/docs/en/agent-sdk/python).
After the first turn, subsequent turns hit the prompt cache and incur
~500-2k tokens instead of ~25k.

A background reaper closes idle clients after `SESSION_IDLE_TIMEOUT_S` of
no use to free memory and let Anthropic's 5-min cache TTL roll naturally.

A per-channel `asyncio.Lock` serializes queries to the same client
because `ClaudeSDKClient` is bidirectional but a single
query/receive_response sequence is not concurrency-safe.

Auth model: OAuth Max only. The credentials.json was written to
`/home/runner/.claude/.credentials.json` by the entrypoint script
(see `infra/azure/entrypoint.sh`). No API key fallback — on rate-limit
the discord-bot caller falls over to ALICE (FAILOVER-1).
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from shared.logging_setup import configure_structlog

log = structlog.get_logger()

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/data/insult-workspace"))
PERSONA_PATH = Path(os.environ.get("PERSONA_PATH", "/app/persona.md"))
RUNNER_AUTH_TOKEN = os.environ.get("INSULT_AGENT_RUNNER_TOKEN", "")
DEFAULT_MODEL = os.environ.get("AGENT_RUNNER_MODEL", "claude-sonnet-4-6")
TURN_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_TIMEOUT_S", "90"))
# Close a per-channel ClaudeSDKClient after this many seconds of no turn
# activity. Default 15 min — comfortably past the 5-min cache TTL so the
# next turn after this re-opens with a fresh cache window anyway.
SESSION_IDLE_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_SESSION_IDLE_TIMEOUT_S", "900"))


class TurnRequest(BaseModel):
    channel_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    user_text: str = Field(..., min_length=1, max_length=8000)
    # session_uuid kept in the schema for caller backward-compat but ignored —
    # the per-channel client owns continuity now.
    session_uuid: str | None = None
    # v3.9.43 (REWRITE-B1): Anthropic-shape content blocks for non-text
    # attachments (image, document). Caller extracts them from the
    # `messages[-1].content` list and forwards them raw. When present
    # the agent receives a multimodal user message instead of text-only.
    # Bug origin: 2026-05-18 Alex sent text+2 images, runner only saw
    # text → bot ignored images entirely.
    attachments: list[dict] | None = None


class TurnResponse(BaseModel):
    text: str
    session_uuid: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""
    tool_calls: list[dict] = Field(default_factory=list)


def _load_persona() -> str:
    """Read persona.md from disk on first session creation only.

    Each long-lived ClaudeSDKClient gets persona.md inlined as its
    system_prompt at construction time. The SDK then caches it across
    that client's lifetime. Re-reading from disk is cheap and lets
    `mtime` updates take effect on the NEXT new session.
    """
    if not PERSONA_PATH.exists():
        log.error("agent_runner_persona_missing", path=str(PERSONA_PATH))
        return ""
    return PERSONA_PATH.read_text(encoding="utf-8")


# --- Per-channel session pool ---
#
# Each channel_id maps to a long-lived ClaudeSDKClient that has already
# been entered (ClaudeSDKClient.__aenter__ called). Subsequent turns for
# the same channel reuse the client → SDK auto-continues the same session
# → prompt cache hits the persona + tool defs + CLAUDE.md.
#
# Concurrency:
# - _pool_lock: protects pool dict mutations (add/remove)
# - _channel_locks: one Lock per channel, serializes queries against
#   that channel's client (the SDK can't handle concurrent query+receive
#   on the same client)

_pool: dict[str, Any] = {}  # channel_id → ClaudeSDKClient (entered)
_pool_last_used: dict[str, float] = {}  # channel_id → unix ts
_channel_locks: dict[str, asyncio.Lock] = {}  # channel_id → Lock
_pool_lock = asyncio.Lock()
_reaper_task: asyncio.Task | None = None


async def _build_options(persona: str) -> Any:
    """Construct ClaudeAgentOptions for a new channel session.

    F4 phase 1 (v3.9.51): the in-process `insult_db` MCP server is
    registered alongside the workspace `Read/Grep/Glob` tools. The
    agent can hit Postgres directly via `mcp__insult_db__*` calls or
    keep reading the workspace markdown — both paths work during the
    migration so we can validate before decommissioning the renderer.
    """
    from claude_agent_sdk import ClaudeAgentOptions

    from insult.agent.mcp_tools import (
        INSULT_DB_SERVER_NAME,
        INSULT_DB_TOOLS,
        build_insult_db_server,
    )

    insult_db_server = build_insult_db_server()
    mcp_tool_names = [f"mcp__{INSULT_DB_SERVER_NAME}__{t.name}" for t in INSULT_DB_TOOLS]

    return ClaudeAgentOptions(
        system_prompt=persona,
        cwd=str(WORKSPACE_ROOT),
        model=DEFAULT_MODEL,
        allowed_tools=["Read", "Grep", "Glob", *mcp_tool_names],
        mcp_servers={INSULT_DB_SERVER_NAME: insult_db_server},
        permission_mode="bypassPermissions",
        # Project-only filesystem settings: load <cwd>/CLAUDE.md as project
        # context, but do NOT read ~/.claude/ from the runner user.
        setting_sources=["project"],
    )


async def _get_or_create_client(channel_id: str) -> Any:
    """Return a ClaudeSDKClient for this channel, creating + entering it
    if absent. Caller MUST hold the per-channel lock before calling query
    on the returned client.
    """
    from claude_agent_sdk import ClaudeSDKClient

    async with _pool_lock:
        existing = _pool.get(channel_id)
        if existing is not None:
            _pool_last_used[channel_id] = time.time()
            return existing

        # First turn for this channel — build + enter a new client.
        persona = _load_persona()
        options = await _build_options(persona)
        client = ClaudeSDKClient(options=options)
        await client.__aenter__()
        _pool[channel_id] = client
        _pool_last_used[channel_id] = time.time()
        log.info(
            "agent_runner_session_created",
            channel_id=channel_id,
            pool_size=len(_pool),
        )
        return client


async def _close_client(channel_id: str) -> None:
    """Close + remove a channel's client. Safe to call even if absent."""
    async with _pool_lock:
        client = _pool.pop(channel_id, None)
        _pool_last_used.pop(channel_id, None)
        _channel_locks.pop(channel_id, None)
    if client is not None:
        try:
            await client.__aexit__(None, None, None)
            log.info("agent_runner_session_closed", channel_id=channel_id)
        except Exception:
            log.exception("agent_runner_session_close_failed", channel_id=channel_id)


async def _reap_idle_sessions() -> None:
    """Background task: close clients idle longer than SESSION_IDLE_TIMEOUT_S."""
    while True:
        await asyncio.sleep(60)
        try:
            now = time.time()
            stale = [cid for cid, ts in list(_pool_last_used.items()) if now - ts > SESSION_IDLE_TIMEOUT_S]
            for cid in stale:
                log.info(
                    "agent_runner_session_reap",
                    channel_id=cid,
                    idle_s=int(now - _pool_last_used.get(cid, now)),
                )
                await _close_client(cid)
        except Exception:
            log.exception("agent_runner_reaper_iteration_failed")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown hooks. Verifies workspace mount + persona at boot,
    spawns the idle-session reaper, and tears down all open clients on
    shutdown."""
    global _reaper_task
    configure_structlog()
    if not WORKSPACE_ROOT.exists():
        log.error("agent_runner_workspace_missing", path=str(WORKSPACE_ROOT))
    if not RUNNER_AUTH_TOKEN:
        log.warning("agent_runner_no_auth_token_configured")
    log.info(
        "agent_runner_starting",
        workspace=str(WORKSPACE_ROOT),
        persona=str(PERSONA_PATH),
        model=DEFAULT_MODEL,
        token_set=bool(RUNNER_AUTH_TOKEN),
        session_idle_timeout_s=SESSION_IDLE_TIMEOUT_S,
    )
    _reaper_task = asyncio.create_task(_reap_idle_sessions(), name="session_reaper")
    yield

    # Shutdown: cancel reaper + close all open clients
    if _reaper_task is not None:
        _reaper_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _reaper_task
    open_channels = list(_pool.keys())
    log.info("agent_runner_shutdown_closing_sessions", count=len(open_channels))
    for cid in open_channels:
        await _close_client(cid)
    log.info("agent_runner_stopped")


app = FastAPI(title="Insult Agent Runner", version="0.1.0", lifespan=_lifespan)


def _check_auth(authorization: str | None) -> None:
    """Bearer auth check. Fail-closed when token unconfigured (503)."""
    if not RUNNER_AUTH_TOKEN:
        raise HTTPException(503, "Runner auth token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    provided = authorization[len("Bearer ") :]
    if not hmac.compare_digest(provided, RUNNER_AUTH_TOKEN):
        raise HTTPException(401, "Invalid token")


@app.get("/health")
async def health() -> dict:
    """Public liveness probe. Always 200. Body reflects state for monitoring."""
    claude_md_path = WORKSPACE_ROOT / "CLAUDE.md"
    return {
        "status": "ok",
        "service": "insult-agent-runner",
        "workspace_present": WORKSPACE_ROOT.exists(),
        "persona_present": PERSONA_PATH.exists(),
        "claude_md_present": claude_md_path.exists(),
        "auth_configured": bool(RUNNER_AUTH_TOKEN),
        "model": DEFAULT_MODEL,
        "open_sessions": len(_pool),
    }


@app.post("/v1/turn", response_model=TurnResponse)
async def turn(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnResponse:
    """Run one Agent SDK turn against the workspace, reusing the per-channel
    long-lived ClaudeSDKClient so the SDK auto-continues the session and the
    prompt cache hits.

    The agent reads selectively from /data/insult-workspace via Read/Grep/Glob.
    Earlier conversation context is in the SDK session's internal history (not
    re-inlined per turn). The first turn for a channel pays the persona +
    CLAUDE.md cost; subsequent turns within ~5 min hit cache.
    """
    _check_auth(authorization)
    start = time.monotonic()

    # Lock per-channel so concurrent /v1/turn calls for the same channel
    # serialize queries against the same client. Different channels run
    # in parallel.
    lock = _channel_locks.setdefault(req.channel_id, asyncio.Lock())

    framed_text = (
        f"<turn_context>\nchannel_id: {req.channel_id}\nuser_id: {req.user_id}\n</turn_context>\n\n{req.user_text}"
    )

    # When the turn has image/document attachments we build a multimodal
    # streaming message and hand the SDK an AsyncIterable. The SDK's
    # `query(str)` branch wraps strings into a text-only user message,
    # which silently discards the attachments — hence the dual path.
    # See `ClaudeSDKClient.query()` source.
    has_attachments = bool(req.attachments)
    if has_attachments:
        content_blocks: list[dict] = [{"type": "text", "text": framed_text}]
        content_blocks.extend(req.attachments or [])
        streaming_msg = {
            "type": "user",
            "message": {"role": "user", "content": content_blocks},
            "parent_tool_use_id": None,
        }

        async def _stream():
            yield streaming_msg

        query_input: Any = _stream()
    else:
        query_input = framed_text

    accumulated_text = ""
    tool_calls: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    stop_reason = ""
    session_uuid: str | None = None
    model = DEFAULT_MODEL
    is_first_turn = req.channel_id not in _pool

    try:
        async with lock:
            client = await _get_or_create_client(req.channel_id)
            await client.query(query_input)
            async for message in client.receive_response():
                mtype = type(message).__name__
                if mtype == "AssistantMessage":
                    for block in getattr(message, "content", []) or []:
                        btype = type(block).__name__
                        if btype == "TextBlock":
                            accumulated_text += getattr(block, "text", "") or ""
                        elif btype == "ToolUseBlock":
                            tool_calls.append(
                                {
                                    "name": getattr(block, "name", "?"),
                                    "input_keys": list((getattr(block, "input", {}) or {}).keys()),
                                }
                            )
                elif mtype == "ResultMessage":
                    usage = getattr(message, "usage", None) or {}
                    input_tokens = int(usage.get("input_tokens", 0))
                    output_tokens = int(usage.get("output_tokens", 0))
                    stop_reason = getattr(message, "stop_reason", "") or ""
                    session_uuid = getattr(message, "session_id", None)
                    model = getattr(message, "model", DEFAULT_MODEL) or DEFAULT_MODEL
                else:
                    log.debug("agent_runner_message_ignored", type=mtype)
    except Exception as e:
        # On error, drop this client from the pool so the next turn can
        # rebuild from scratch. A broken session is worse than a fresh one.
        log.exception(
            "agent_runner_turn_failed",
            channel_id=req.channel_id,
            user_id=req.user_id,
            user_text_len=len(req.user_text),
            elapsed_ms=int((time.monotonic() - start) * 1000),
            is_first_turn=is_first_turn,
        )
        await _close_client(req.channel_id)
        raise HTTPException(502, f"agent loop failed: {type(e).__name__}: {e}") from e

    elapsed_ms = int((time.monotonic() - start) * 1000)
    tool_names = [tc.get("name", "?") for tc in tool_calls]
    log.info(
        "agent_runner_turn_complete",
        channel_id=req.channel_id,
        user_id=req.user_id,
        text_len=len(accumulated_text),
        tool_calls=len(tool_calls),
        # Tool names included so KQL can distinguish workspace Read/Grep/Glob
        # from the F4 mcp__insult_db__* tools. Critical for verifying Phase 2
        # adoption before removing the workspace fallback in Phase 3.
        tool_names=tool_names,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=stop_reason,
        session_uuid=session_uuid,
        elapsed_ms=elapsed_ms,
        is_first_turn=is_first_turn,
        pool_size=len(_pool),
        has_attachments=has_attachments,
        attachment_count=len(req.attachments or []),
    )

    return TurnResponse(
        text=accumulated_text,
        session_uuid=session_uuid,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        stop_reason=stop_reason,
        tool_calls=tool_calls,
    )
