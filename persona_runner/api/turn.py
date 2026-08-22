"""Turn surface — the agent loop every persona speaks through.

One turn = reuse (or open) this slot's long-lived SDK client, frame the user
message, query, and drain the response stream. Earlier conversation context lives
in the SDK session's internal history; only a FRESH session folds caller-replayed
history (a live session already holds the thread — re-inlining would duplicate it
every turn).

On ANY failure the slot's client is dropped from the pool: a broken session is
worse than a fresh one, and the next turn rebuilds cleanly.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException

from persona_runner.core import config
from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import auth_failure, session_pool
from persona_runner.engine.framing import fold_history, frame_turn_text, query_input_for
from persona_runner.mcp_tools import turn_context

log = structlog.get_logger()

router = APIRouter()


def _drain(message: Any, state: dict) -> None:
    """Accumulate one SDK stream message into the turn's result state.

    Text that SHARES a message with a tool call is the model narrating what it
    is about to do ("necesito cargar mis herramientas de memoria primero…") —
    plumbing, never the answer. The persona must never expose its mechanics, so
    that text is counted (`preamble_chars`) and dropped; only the text of a
    message that calls no tool is the persona speaking. Final texts from
    separate messages join on a newline instead of butting together, so two
    blocks can never fuse into `…búsqueda.NADA`.
    """
    mtype = type(message).__name__
    if mtype == "AssistantMessage":
        blocks = getattr(message, "content", []) or []
        text = "".join(getattr(b, "text", "") or "" for b in blocks if type(b).__name__ == "TextBlock")
        tool_blocks = [b for b in blocks if type(b).__name__ == "ToolUseBlock"]
        for block in tool_blocks:
            state["tool_calls"].append(
                {
                    "name": getattr(block, "name", "?"),
                    "input_keys": list((getattr(block, "input", {}) or {}).keys()),
                }
            )
        if not text:
            return
        if tool_blocks:
            state["preamble_chars"] += len(text)
        else:
            state["text"] = f"{state['text']}\n{text}" if state["text"] else text
    elif mtype == "ResultMessage":
        usage = getattr(message, "usage", None) or {}
        state["input_tokens"] = int(usage.get("input_tokens", 0))
        state["output_tokens"] = int(usage.get("output_tokens", 0))
        state["stop_reason"] = getattr(message, "stop_reason", "") or ""
        state["session_uuid"] = getattr(message, "session_id", None)
        state["model"] = getattr(message, "model", state["model"]) or state["model"]
    else:
        log.debug("agent_runner_message_ignored", type=mtype)


@router.post("/v1/turn", response_model=TurnResponse)
async def turn(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnResponse:
    """Run one Agent SDK turn, reusing the per-slot long-lived client so the SDK
    auto-continues the session and the prompt cache hits."""
    check_auth(authorization)
    if config.TURN_BACKEND == "aire":
        # AIRE stage 2: the turn rides AIRE's engine door instead of the local
        # SDK host. Everything below this line is the LOCAL path, which dies
        # when the flag flips permanent (backlog aire-engine-stage2.md).
        from persona_runner.engine import aire_route

        return await aire_route.turn_via_aire(req)
    start = time.monotonic()

    key = session_pool.pool_key(req.channel_id, req.persona_id)
    lock = session_pool.slot_lock(key)
    has_attachments = bool(req.attachments)

    state: dict[str, Any] = {
        "text": "",
        "preamble_chars": 0,
        "tool_calls": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "stop_reason": "",
        "session_uuid": None,
        "model": session_pool.model_for(key),
    }
    is_first_turn = not session_pool.is_open(key)

    # Whose data the memory tools may touch, decided HERE and never asked of the
    # model. Bound around the whole turn — the SDK invokes tools while
    # `receive_response()` is draining, so the scope must outlive `query()`.
    principal_token = turn_context.bind_turn_principal(user_id=req.user_id, channel_id=req.channel_id)
    try:
        async with lock:
            # Race-free freshness: only under the lock does "not open" mean THIS
            # turn opens the session. Caller-replayed history is folded only then.
            is_first_turn = not session_pool.is_open(key)
            framed_text = frame_turn_text(
                channel_id=req.channel_id,
                user_id=req.user_id,
                user_text=req.user_text,
                behavioral_guidance=req.behavioral_guidance,
                history_block=fold_history(req.history) if is_first_turn else "",
            )
            query_input = query_input_for(framed_text, req.attachments)
            client = await session_pool.get_or_create_client(
                req.channel_id,
                persona_id=req.persona_id,
                user_id=req.user_id,
                user_text=req.user_text,
            )
            # After create, the router's model is in the pool — refresh so the
            # response reports what was actually used.
            state["model"] = session_pool.model_for(key)
            await client.query(query_input)
            async for message in client.receive_response():
                _drain(message, state)
    except Exception as e:
        log.exception(
            "agent_runner_turn_failed",
            channel_id=req.channel_id,
            user_id=req.user_id,
            user_text_len=len(req.user_text),
            elapsed_ms=int((time.monotonic() - start) * 1000),
            is_first_turn=is_first_turn,
        )
        await session_pool.close_client(key)
        raise HTTPException(502, f"agent loop failed: {type(e).__name__}: {e}") from e
    finally:
        turn_context.reset_turn_principal(principal_token)

    # A revoked/expired token comes back as ordinary text, not an exception, so
    # without this the 401 would be logged as a completed turn and returned 200
    # — mute personas with every proxy green (see engine/auth_failure.py).
    if auth_failure.looks_like_credential_failure(state):
        auth_failure.mark_failure(state["text"])
        log.error(
            "agent_runner_auth_failed",
            channel_id=req.channel_id,
            user_id=req.user_id,
            persona_id=req.persona_id,
            detail=state["text"][:200],
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
        await session_pool.close_client(key)
        # 500, not 502: the caller retries 502/503 as "mid-restart", and no
        # number of retries fixes a dead credential — it needs a human rotating
        # the token. A defined internal error is exactly what this is.
        raise HTTPException(500, "agent auth failed: credentials rejected upstream")

    auth_failure.clear_failure()

    log.info(
        "agent_runner_turn_complete",
        channel_id=req.channel_id,
        user_id=req.user_id,
        text_len=len(state["text"]),
        preamble_chars=state["preamble_chars"],
        tool_calls=len(state["tool_calls"]),
        # Tool names so KQL can distinguish workspace Read/Grep/Glob from the
        # mcp__persona_memory__* tools.
        tool_names=[tc.get("name", "?") for tc in state["tool_calls"]],
        input_tokens=state["input_tokens"],
        output_tokens=state["output_tokens"],
        stop_reason=state["stop_reason"],
        session_uuid=state["session_uuid"],
        elapsed_ms=int((time.monotonic() - start) * 1000),
        is_first_turn=is_first_turn,
        pool_size=session_pool.pool_size(),
        has_attachments=has_attachments,
        attachment_count=len(req.attachments or []),
    )

    return TurnResponse(
        text=state["text"],
        session_uuid=state["session_uuid"],
        input_tokens=state["input_tokens"],
        output_tokens=state["output_tokens"],
        model=state["model"],
        stop_reason=state["stop_reason"],
        tool_calls=state["tool_calls"],
    )
