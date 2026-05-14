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
      "session_uuid": "<previous-uuid-or-null>"
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

Auth model: OAuth Max only. The credentials.json was written to
`/home/runner/.claude/.credentials.json` by the entrypoint script
(see `infra/azure/entrypoint.sh`). No API key fallback — on 429 quota
exhaustion we return an in-character error and the caller falls back
to the legacy LLMClient path.

Sessions are managed by the SDK itself: pass `resume=session_uuid` and
the SDK reanudates the previous conversation. New session if None.
"""

from __future__ import annotations

import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

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


class TurnRequest(BaseModel):
    channel_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    user_text: str = Field(..., min_length=1, max_length=8000)
    session_uuid: str | None = None


class TurnResponse(BaseModel):
    text: str
    session_uuid: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""
    tool_calls: list[dict] = Field(default_factory=list)


def _load_persona() -> str:
    """Read persona.md from disk on every turn.

    Cached implicitly by the OS FS layer; persona is small (~30 KiB) and
    re-reading lets `mtime` updates take effect without a runner restart.
    Empty string on missing file so the runner serves a degraded response
    instead of crashing the request.
    """
    if not PERSONA_PATH.exists():
        log.error("agent_runner_persona_missing", path=str(PERSONA_PATH))
        return ""
    return PERSONA_PATH.read_text(encoding="utf-8")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown hooks. Verifies workspace mount + persona at boot."""
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
    )
    yield
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
    return {
        "status": "ok",
        "service": "insult-agent-runner",
        "workspace_present": WORKSPACE_ROOT.exists(),
        "persona_present": PERSONA_PATH.exists(),
        "auth_configured": bool(RUNNER_AUTH_TOKEN),
        "model": DEFAULT_MODEL,
    }


@app.post("/v1/turn", response_model=TurnResponse)
async def turn(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnResponse:
    """Run one Agent SDK turn against the workspace.

    The agent reads selectively from /data/insult-workspace via Read/Grep/Glob.
    Earlier conversation context is NOT inlined — it's already in the
    workspace files updated by the renderer.
    """
    _check_auth(authorization)

    persona = _load_persona()
    start = time.monotonic()

    # Imported lazily so a broken claude-agent-sdk install doesn't crash the
    # FastAPI process at module load time — instead returns a clean 503 here.
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    except ImportError as e:
        log.exception("agent_runner_sdk_import_failed")
        raise HTTPException(503, f"claude-agent-sdk import failed: {e}") from e

    options = ClaudeAgentOptions(
        system_prompt=persona,
        cwd=str(WORKSPACE_ROOT),
        model=DEFAULT_MODEL,
        allowed_tools=["Read", "Grep", "Glob"],
        permission_mode="bypassPermissions",
        resume=req.session_uuid,
    )

    accumulated_text = ""
    tool_calls: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    stop_reason = ""
    session_uuid: str | None = req.session_uuid
    model = DEFAULT_MODEL

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(req.user_text)
            async for message in client.receive_response():
                # Message shapes vary across SDK versions. We only care about
                # text payloads, tool_use calls, and the final result with
                # usage metadata. Everything else is logged at debug.
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
                    session_uuid = getattr(message, "session_id", None) or session_uuid
                    model = getattr(message, "model", DEFAULT_MODEL) or DEFAULT_MODEL
                else:
                    log.debug("agent_runner_message_ignored", type=mtype)
    except Exception as e:
        log.exception(
            "agent_runner_turn_failed",
            channel_id=req.channel_id,
            user_id=req.user_id,
            user_text_len=len(req.user_text),
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
        raise HTTPException(502, f"agent loop failed: {type(e).__name__}: {e}") from e

    elapsed_ms = int((time.monotonic() - start) * 1000)
    log.info(
        "agent_runner_turn_complete",
        channel_id=req.channel_id,
        user_id=req.user_id,
        text_len=len(accumulated_text),
        tool_calls=len(tool_calls),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=stop_reason,
        session_uuid=session_uuid,
        elapsed_ms=elapsed_ms,
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
