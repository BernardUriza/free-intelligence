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
import re
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
# Multi-persona (Khimeras): a turn may carry a `persona_id` to load a sibling
# persona (e.g. "vultur") from PERSONAS_DIR/<id>.md instead of Insult's default
# PERSONA_PATH. The id is allowlisted to a tight charset so it can never escape
# the directory (path traversal) — anything else falls back to Insult.
PERSONAS_DIR = Path(os.environ.get("PERSONAS_DIR", "/app/personas"))
_PERSONA_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
RUNNER_AUTH_TOKEN = os.environ.get("INSULT_AGENT_RUNNER_TOKEN", "")
DEFAULT_MODEL = os.environ.get("AGENT_RUNNER_MODEL", "claude-sonnet-4-6")
TURN_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_TIMEOUT_S", "90"))
# Close a per-channel ClaudeSDKClient after this many seconds of no turn
# activity. Default 15 min — comfortably past the 5-min cache TTL so the
# next turn after this re-opens with a fresh cache window anyway.
SESSION_IDLE_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_SESSION_IDLE_TIMEOUT_S", "900"))

# Max concurrent /v1/judge SDK calls. Default 1 — the judge spawns a FRESH
# Node subprocess per call (no session pool) and generates thousands of tokens
# (the SDK has no max_tokens cap). On 2026-05-22 a consolidator backlog fired
# ~25 judges at once on a 1-CPU/2Gi runner: the subprocess pile-up OOM-killed
# the chat turns' SDK and starved their CPU (p50 turn latency 27-53s). Judges
# are background utility work (consolidator, fact-extraction, summaries) — the
# user is NOT waiting on them — so serializing them protects the interactive
# turns. Override via env for a bigger runner.
JUDGE_MAX_CONCURRENCY = int(os.environ.get("AGENT_RUNNER_JUDGE_MAX_CONCURRENCY", "1"))
# Lazy-initialized inside the running loop (a module-level asyncio.Semaphore can
# bind to the wrong/closed loop under some test + uvicorn-reload setups).
_judge_semaphore: asyncio.Semaphore | None = None


def _get_judge_semaphore() -> asyncio.Semaphore:
    """Return the process-wide judge concurrency gate, creating it on first use
    inside the active event loop."""
    global _judge_semaphore
    if _judge_semaphore is None:
        _judge_semaphore = asyncio.Semaphore(JUDGE_MAX_CONCURRENCY)
    return _judge_semaphore


class TurnRequest(BaseModel):
    channel_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    # v3.9.58: raised from 8000 -> 256000 chars. Bernard 2026-05-19 07:06
    # pasted `message.txt` (21KB) and the runner rejected with 422, falling
    # over to ALICE who never saw the attachment content. The Claude Agent
    # SDK handles long inputs fine; the previous cap was arbitrary Pydantic
    # constraint with no upstream justification.
    user_text: str = Field(..., min_length=1, max_length=256000)
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
    # v3.9.94: per-turn behavioral guidance (preset + vulnerability overlay)
    # computed by discord-bot's classifier. Pre-F3 the legacy LLM path baked
    # this into the system prompt; the runner-extracted architecture dropped
    # it (agent_client discarded `system_prompt`), so Insult responded with
    # the raw persona.md base tone regardless of what the classifier decided.
    # Symptom 2026-05-22: classifier picked relational_probe + vulnerability
    # overlay (score 11) for a user hours after suicidal ideation, but Insult
    # stayed abrasive. We inject this into the USER message (not the system
    # prompt) so persona.md stays cache-stable while the guidance varies
    # per turn. Capped to keep the turn payload bounded.
    behavioral_guidance: str | None = Field(default=None, max_length=16000)
    # Khimeras multi-persona: which sibling persona answers this turn. None ⇒
    # Insult (default PERSONA_PATH), fully backward-compatible. A valid id loads
    # PERSONAS_DIR/<id>.md; an unknown/invalid id falls back to Insult + a log.
    persona_id: str | None = Field(default=None, max_length=32)


class TurnResponse(BaseModel):
    text: str
    session_uuid: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""
    tool_calls: list[dict] = Field(default_factory=list)


class JudgeRequest(BaseModel):
    """One-shot utility request — runs an SDK call with arbitrary system
    prompt + user text, no session pool, no persona.md. Used by the
    consolidator job (and any future utility caller) so OAuth Max stays
    centralized in the runner. Memory: [[mcp-shape-b-canonical]].

    The judge prompt + user text shape mirrors the legacy utility_call
    signature so the consolidator runs against RunnerJudgeClient with
    minimal churn.
    """

    system_prompt: str = Field(..., min_length=1, max_length=256000)
    user_text: str = Field(..., min_length=1, max_length=256000)
    max_tokens: int = Field(default=4096, ge=1, le=64000)
    model: str | None = Field(
        default=None,
        description="Override AGENT_RUNNER_JUDGE_MODEL. Defaults to Haiku.",
    )


class JudgeResponse(BaseModel):
    text: str
    model: str = ""
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def _frame_turn_text(
    *,
    channel_id: str,
    user_id: str,
    user_text: str,
    behavioral_guidance: str | None = None,
) -> str:
    """Assemble the user-message text the SDK sees for one turn.

    Order matters: `<turn_context>` (who/where) → optional
    `<behavioral_guidance>` (how to respond, computed per turn by the
    caller's classifier) → the actual user text. The guidance lives here in
    the user message, NOT in the cached system prompt, so it can vary per
    turn without invalidating persona.md's prompt cache. Returns the bare
    framed text when no guidance is supplied — byte-identical to the
    pre-v3.9.94 behavior.
    """
    guidance_block = ""
    if behavioral_guidance:
        guidance_block = f"<behavioral_guidance>\n{behavioral_guidance}\n</behavioral_guidance>\n\n"
    return (
        f"<turn_context>\nchannel_id: {channel_id}\nuser_id: {user_id}\n</turn_context>\n\n{guidance_block}{user_text}"
    )


def _resolve_persona_path(persona_id: str | None) -> Path:
    """Map a persona_id to its persona file, defaulting to Insult.

    Returns PERSONA_PATH (Insult) when persona_id is None, fails the allowlist
    (anti path-traversal), or the sibling file is missing — logging the unknown
    case so a typo'd id is visible instead of silently impersonating Insult.
    """
    if not persona_id:
        return PERSONA_PATH
    if not _PERSONA_ID_RE.match(persona_id):
        log.warning("agent_runner_persona_invalid_id", persona_id=persona_id)
        return PERSONA_PATH
    candidate = PERSONAS_DIR / f"{persona_id}.md"
    if not candidate.exists():
        log.warning("agent_runner_persona_unknown", persona_id=persona_id, path=str(candidate))
        return PERSONA_PATH
    return candidate


def _load_persona(persona_id: str | None = None) -> str:
    """Read the persona markdown from disk on first session creation only.

    Each long-lived ClaudeSDKClient gets the persona inlined as its
    system_prompt at construction time. The SDK then caches it across
    that client's lifetime. Re-reading from disk is cheap and lets
    `mtime` updates take effect on the NEXT new session.

    With `persona_id` set (Khimeras siblings), loads PERSONAS_DIR/<id>.md;
    otherwise the default Insult PERSONA_PATH. Resolution + safety live in
    `_resolve_persona_path`.
    """
    path = _resolve_persona_path(persona_id)
    if not path.exists():
        log.error("agent_runner_persona_missing", path=str(path))
        return ""
    return path.read_text(encoding="utf-8")


def _pool_key(channel_id: str, persona_id: str | None) -> str:
    """Session-pool key. Insult (persona_id=None) keeps the bare channel_id so
    existing sessions and behavior are untouched; a sibling persona gets its own
    `channel_id:persona_id` slot so it never shares Insult's SDK session."""
    return channel_id if not persona_id else f"{channel_id}:{persona_id}"


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


# Playwright MCP — stdio subprocess spawned by the SDK on session creation.
# Lets the agent scrape JS-heavy / social-media sites (IG/FB/TikTok/X) that
# Anthropic's `web_search` server tool cannot reach (no SERP coverage, JS
# rendering required, anti-bot). `--isolated` keeps cookies in memory so the
# bot never logs in with a real account. `--headless` mandatory in container.
# Chromium binary at PLAYWRIGHT_BROWSERS_PATH (set in runner.Dockerfile).
_PLAYWRIGHT_SERVER_NAME = "playwright"
_PLAYWRIGHT_ALLOWED_TOOLS = [
    "browser_navigate",
    "browser_snapshot",
    "browser_take_screenshot",
    "browser_wait_for",
    "browser_click",
    "browser_evaluate",
]


async def _build_options(persona: str, model: str | None = None) -> Any:
    """Construct ClaudeAgentOptions for a new channel session.

    F4 phase 3 (v3.9.56): only the `mcp__insult_db__*` tools are allowed.
    `Read`, `Grep`, `Glob` were removed — the agent must use Postgres
    directly. The workspace mount is still around so the agent can read
    `CLAUDE.md` via `setting_sources=["project"]`, but the projected
    facts/messages/disclosure markdown is no longer written (the
    workspace_renderer process was removed from the entrypoint).

    v3.9.71: `model` parameter accepts a router decision (Haiku/Sonnet/
    Opus). Falls back to DEFAULT_MODEL when None — that path is what the
    earlier (router-less) code did, so behavior is preserved if the
    caller skips routing.

    v3.9.73: registers the fi-core persona MCP server (anti-drift detectors)
    alongside the insult_db in-process server. fi-core lives in a sibling
    Python package and ships its own FastMCP-over-stdio server; the SDK
    spawns it on session creation.
    """
    # v4.0 (fi-runner): option assembly is delegated to fi_runner — the
    # backend-agnostic runner framework. insult declares its MCP servers and
    # the ToolPolicy; fi_runner builds the ClaudeAgentOptions (allowlist,
    # mcp_servers, cwd, setting_sources, permission mode). The per-channel pool
    # and turn loop below stay in insult — fi_runner owns option/capability
    # wiring, insult owns orchestration.
    #
    # The fi-core persona server is wired via fi_runner's CAPABILITY registry
    # (capabilities.resolve(["persona"])) rather than a hand-built spec — the
    # registry reads the server name + tool contract from fi_core itself, so
    # there is no name/tool list to keep in sync here. env_passthrough=False
    # keeps the stdio entry byte-identical to the pre-capability behavior.
    from fi_runner import ClaudeCodeBackend, MCPServerSpec, PermissionMode, ToolPolicy, capabilities

    from personas.insult.agent.mcp_tools import (
        INSULT_DB_SERVER_NAME,
        INSULT_DB_TOOLS,
        build_insult_db_server,
    )

    specs = [
        MCPServerSpec(
            name=INSULT_DB_SERVER_NAME,
            server=build_insult_db_server(),  # in-process MCP server
            tools=tuple(t.name for t in INSULT_DB_TOOLS),
        ),
        # fi-core persona (anti-drift) — resolved from the capability registry.
        *capabilities.resolve(["persona"], env_passthrough=False),
        # `--isolated`: never log in with a real account from prod. `--headless`
        # mandatory in container.
        MCPServerSpec(
            name=_PLAYWRIGHT_SERVER_NAME,
            command="npx",
            args=["@playwright/mcp@latest", "--headless", "--isolated"],
            tools=tuple(_PLAYWRIGHT_ALLOWED_TOOLS),
            env_passthrough=False,
        ),
    ]

    backend = ClaudeCodeBackend(cwd=str(WORKSPACE_ROOT), setting_sources=["project"])
    return backend.build_options(
        system_prompt=persona,
        mcp_servers=specs,
        tool_policy=ToolPolicy(permission_mode=PermissionMode.BYPASS),
        model=model or DEFAULT_MODEL,
    )


_pool_models: dict[str, str] = {}  # channel_id → model id chosen at session creation


async def _get_or_create_client(
    channel_id: str,
    *,
    persona_id: str | None = None,
    user_id: str | None = None,
    user_text: str | None = None,
) -> Any:
    """Return a ClaudeSDKClient for this channel, creating + entering it
    if absent. Caller MUST hold the per-channel lock before calling query
    on the returned client.

    v3.9.71: when a new client is created, runs the 3-tier router
    (Haiku/Sonnet/Opus) using `user_id` + `user_text` + disclosure
    severity from Postgres. The chosen model sticks for the session's
    lifetime — see router_runtime.py for the rationale on per-session
    stickiness vs per-turn rerouting.

    When user_id/user_text are not provided (e.g. legacy callers, tests),
    falls back to DEFAULT_MODEL — same behavior as before v3.9.71.
    """
    from claude_agent_sdk import ClaudeSDKClient

    key = _pool_key(channel_id, persona_id)
    async with _pool_lock:
        existing = _pool.get(key)
        if existing is not None:
            _pool_last_used[key] = time.time()
            return existing

        # First turn for this channel — route, then build + enter client.
        chosen_model = DEFAULT_MODEL
        route_meta: dict[str, Any] = {"routed": False}
        if user_id and user_text:
            from personas.insult.agent.router_runtime import route_for_session

            pg_conn = None
            try:
                from personas.insult.agent.mcp_tools import _connect as _pg_connect

                pg_conn = await _pg_connect()
                decision = await route_for_session(
                    channel_id=channel_id,
                    user_id=user_id,
                    user_text=user_text,
                    pg_conn=pg_conn,
                )
                chosen_model = decision.model
                route_meta = {
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
                chosen_model = DEFAULT_MODEL
                route_meta = {"routed": False, "reason": "exception_fallback"}
            finally:
                if pg_conn is not None:
                    with contextlib.suppress(Exception):
                        await pg_conn.close()

        persona = _load_persona(persona_id)
        options = await _build_options(persona, model=chosen_model)
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


async def _close_client(channel_id: str) -> None:
    """Close + remove a channel's client. Safe to call even if absent."""
    async with _pool_lock:
        client = _pool.pop(channel_id, None)
        _pool_last_used.pop(channel_id, None)
        _channel_locks.pop(channel_id, None)
        _pool_models.pop(channel_id, None)
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


@app.delete("/v1/session/{channel_id}")
async def reset_session(channel_id: str, authorization: str | None = Header(default=None)) -> dict:
    """Force-close a channel's long-lived ClaudeSDKClient.

    The next `/v1/turn` for this channel re-creates a fresh session — new
    session_uuid, no prior turn history, persona + CLAUDE.md re-cached on
    first turn. Idempotent: calling on a channel with no open client
    returns `existed=false` and does not raise.

    Use when a session gets stuck in a wrong belief (a tool call failed
    and the agent now thinks the tool does not exist, a confabulated
    fact got baked in, etc.). Without this endpoint the only options
    were waiting `SESSION_IDLE_TIMEOUT_S` for the reaper or hitting from
    a different channel_id — both bad UX during incident response.

    Discovered 2026-05-19 during the F+C smoke test: a tool call against
    `publish_html_artifact` failed because the html_artifacts table was
    missing; the agent received the error and from that point on
    insisted the tool was unavailable even after the table was created
    and tools were verified registered. The poisoned belief stayed in
    session history for as long as the client lived.
    """
    _check_auth(authorization)
    existed = channel_id in _pool
    await _close_client(channel_id)
    log.info(
        "agent_runner_session_reset",
        channel_id=channel_id,
        existed=existed,
        pool_size=len(_pool),
    )
    return {"channel_id": channel_id, "existed": existed, "pool_size": len(_pool)}


@app.post("/v1/judge", response_model=JudgeResponse)
async def judge(req: JudgeRequest, authorization: str | None = Header(default=None)) -> JudgeResponse:
    """One-shot utility call against the SDK with arbitrary system prompt.

    Designed for the fact-consolidation job (and any future utility
    consumer) to delegate LLM execution to the runner instead of holding
    its own Anthropic API key. The runner already has OAuth Max wired
    via CLAUDE_CODE_OAUTH_TOKEN — this endpoint exposes it as a generic
    utility surface.

    NOT a chat turn:
    - Does NOT load persona.md (caller supplies the full system_prompt)
    - Does NOT use the session pool (no continuity, fresh client per call)
    - Does NOT register fi-core / insult_db MCP servers (the prompt does
      what it does, no tool use needed)
    - Does NOT route via the 3-tier model router (caller picks model)

    Shape B per [[mcp-shape-b-canonical]]: this is the runtime that
    EXECUTES what fi-core's build_consolidation_prompt + similar tools
    BUILD. fi-core stays LLM-agnostic; the runner is the auth holder.
    """
    _check_auth(authorization)
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    chosen_model = req.model or os.environ.get("AGENT_RUNNER_JUDGE_MODEL", "claude-haiku-4-5-20251001")
    start = time.monotonic()
    options = ClaudeAgentOptions(
        system_prompt=req.system_prompt,
        model=chosen_model,
        # No tools, no MCP servers — pure text-in, text-out utility.
        allowed_tools=[],
        mcp_servers={},
        permission_mode="bypassPermissions",
        # No project context — the caller's prompt is the entire instruction.
        setting_sources=[],
        # One shot. The judge never needs a tool-use loop; capping turns stops
        # the SDK from ever spending extra round-trips (the SDK has no
        # max_tokens knob, so max_turns is the only structural bound we get).
        max_turns=1,
    )

    accumulated_text = ""
    model_used = chosen_model
    stop_reason = "end_turn"
    input_tokens = 0
    output_tokens = 0

    # Concurrency gate: serialize judge SDK calls so a consolidator backlog
    # can't spawn a pile of Node subprocesses that OOM-kill / starve the
    # interactive chat turns sharing this container. When the gate is held,
    # the extra judges queue here instead of all launching at once.
    semaphore = _get_judge_semaphore()
    if semaphore.locked():
        log.info("agent_runner_judge_queued", model=chosen_model)
    queue_start = time.monotonic()
    async with semaphore:
        queued_ms = int((time.monotonic() - queue_start) * 1000)
        sdk_start = time.monotonic()
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(req.user_text)
                async for message in client.receive_response():
                    mtype = type(message).__name__
                    if mtype == "AssistantMessage":
                        for block in getattr(message, "content", []) or []:
                            btype = type(block).__name__
                            if btype == "TextBlock":
                                accumulated_text += getattr(block, "text", "") or ""
                    elif mtype == "ResultMessage":
                        usage = getattr(message, "usage", None) or {}
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        stop_reason = getattr(message, "stop_reason", "end_turn") or "end_turn"
                        model_used = getattr(message, "model", chosen_model) or chosen_model
        except Exception as e:
            log.exception("agent_runner_judge_failed", error=str(e), model=chosen_model)
            raise HTTPException(500, f"judge call failed: {e}") from e

    elapsed_ms = int((time.monotonic() - start) * 1000)
    sdk_ms = int((time.monotonic() - sdk_start) * 1000)
    log.info(
        "agent_runner_judge_complete",
        model=model_used,
        text_len=len(accumulated_text),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=stop_reason,
        elapsed_ms=elapsed_ms,
        # queued_ms = time spent waiting on the concurrency gate; sdk_ms = the
        # actual SDK call. A growing queued_ms means judge demand exceeds
        # JUDGE_MAX_CONCURRENCY (expected during consolidator bursts; the point
        # is that the wait lands here, not on the chat turns).
        queued_ms=queued_ms,
        sdk_ms=sdk_ms,
    )

    return JudgeResponse(
        text=accumulated_text,
        model=model_used,
        stop_reason=stop_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


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

    # Pool slot for this turn. Insult (persona_id=None) keeps the bare
    # channel_id; a sibling persona gets its own channel_id:persona_id slot so
    # Insult and Vultur in the same channel never share one SDK session.
    pool_key = _pool_key(req.channel_id, req.persona_id)

    # Lock per-slot so concurrent /v1/turn calls for the same slot serialize
    # queries against the same client. Different slots run in parallel.
    lock = _channel_locks.setdefault(pool_key, asyncio.Lock())

    # Per-turn behavioral guidance goes BEFORE the user text so the model
    # reads "how to respond" before "what to respond to". See _frame_turn_text.
    framed_text = _frame_turn_text(
        channel_id=req.channel_id,
        user_id=req.user_id,
        user_text=req.user_text,
        behavioral_guidance=req.behavioral_guidance,
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
    is_first_turn = pool_key not in _pool
    # Best-known model for this turn: prefer the per-session decision
    # picked at create-time (set by the router), fall back to DEFAULT_MODEL
    # for legacy callers and the synthetic logging path before client open.
    model = _pool_models.get(pool_key, DEFAULT_MODEL)

    try:
        async with lock:
            client = await _get_or_create_client(
                req.channel_id,
                persona_id=req.persona_id,
                user_id=req.user_id,
                user_text=req.user_text,
            )
            # After create the chosen model is in the pool. Refresh local
            # binding so the response payload reports what was actually used.
            model = _pool_models.get(pool_key, DEFAULT_MODEL)
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
        await _close_client(pool_key)
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
