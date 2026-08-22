"""Judge surface — the one-shot utility call, serialized on purpose.

NOT a chat turn: no persona, no session pool, no MCP servers, no model router.
The caller supplies the entire system prompt; the runner supplies the auth (OAuth
Max) — Shape B per [[mcp-shape-b-canonical]]: fi-core BUILDS the prompt, the
runner EXECUTES it, nobody else needs a key.

The concurrency gate is the load-bearing part. The judge spawns a FRESH Node
subprocess per call and the SDK has no max_tokens knob. On 2026-05-22 a
consolidator backlog fired ~25 judges at once on a 1-CPU/2Gi runner: the
subprocess pile-up OOM-killed the interactive turns' SDK and starved their CPU
(p50 turn latency 27-53s). Judges are BACKGROUND work — nobody waits on them — so
they queue here instead of stampeding the box.
"""

from __future__ import annotations

import asyncio
import time

import structlog
from fastapi import APIRouter, Header, HTTPException

from persona_runner.core import config
from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import JudgeRequest, JudgeResponse
from persona_runner.engine.framing import query_input_for

log = structlog.get_logger()

router = APIRouter()

# Lazy-initialized inside the running loop (a module-level asyncio.Semaphore can
# bind to the wrong/closed loop under some test + uvicorn-reload setups).
_judge_semaphore: asyncio.Semaphore | None = None


def get_judge_semaphore() -> asyncio.Semaphore:
    """The process-wide judge concurrency gate, created on first use inside the
    active event loop."""
    global _judge_semaphore
    if _judge_semaphore is None:
        _judge_semaphore = asyncio.Semaphore(config.JUDGE_MAX_CONCURRENCY)
    return _judge_semaphore


def reset_judge_semaphore() -> None:
    """Drop the gate so the next call rebuilds it in the current loop (tests)."""
    global _judge_semaphore
    _judge_semaphore = None


@router.post("/v1/judge", response_model=JudgeResponse)
async def judge(req: JudgeRequest, authorization: str | None = Header(default=None)) -> JudgeResponse:
    """Run one utility SDK call with an arbitrary system prompt (text or
    text+image in, text out)."""
    check_auth(authorization)
    if config.TURN_BACKEND == "aire":
        # AIRE stage 2: the judge becomes a mode=complete turn in the persona's
        # utility casita. It keeps THIS gate — the pile-up only MOVED (from this
        # box's Node subprocesses to AIRE's 2 RAM slots), so serializing here is
        # what stops a consolidator burst from starving every interactive turn on
        # the droplet. The gate is THROUGHPUT only: two judges must not cross
        # prompts at ANY value of JUDGE_MAX_CONCURRENCY, and what guarantees that
        # is the prompt-digest casita name (aire_route.judge_casita_for), never
        # this semaphore. Everything below is the LOCAL SDK path, which dies when
        # the flag flips permanent (backlog aire-engine-stage2.md).
        from persona_runner.engine import aire_route

        async with get_judge_semaphore():
            return await aire_route.judge_via_aire(req)
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    chosen_model = req.model or config.JUDGE_DEFAULT_MODEL
    start = time.monotonic()
    options = ClaudeAgentOptions(
        system_prompt=req.system_prompt,
        model=chosen_model,
        # No tools, no MCP servers — pure one-shot utility. `tools=[]` is what
        # actually makes that true: it DISABLES every built-in. `allowed_tools=[]`
        # alone only means "none are pre-approved", and the tools it omits stay
        # available — which `bypassPermissions` below then auto-approves. This
        # comment claimed toolless while the judge could reach Bash (2026-08-10).
        tools=[],
        allowed_tools=[],
        mcp_servers={},
        permission_mode="bypassPermissions",
        # No project context — the caller's prompt is the entire instruction.
        setting_sources=[],
        # One shot. The judge never needs a tool-use loop; capping turns stops the
        # SDK from spending extra round-trips (max_turns is the only structural
        # bound available — there is no max_tokens knob).
        max_turns=1,
    )

    accumulated_text = ""
    model_used = chosen_model
    stop_reason = "end_turn"
    input_tokens = 0
    output_tokens = 0

    semaphore = get_judge_semaphore()
    if semaphore.locked():
        log.info("agent_runner_judge_queued", model=chosen_model)
    queue_start = time.monotonic()
    async with semaphore:
        queued_ms = int((time.monotonic() - queue_start) * 1000)
        sdk_start = time.monotonic()
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(query_input_for(req.user_text, req.attachments))
                async for message in client.receive_response():
                    mtype = type(message).__name__
                    if mtype == "AssistantMessage":
                        for block in getattr(message, "content", []) or []:
                            if type(block).__name__ == "TextBlock":
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

    log.info(
        "agent_runner_judge_complete",
        model=model_used,
        attachments=len(req.attachments or []),
        text_len=len(accumulated_text),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=stop_reason,
        elapsed_ms=int((time.monotonic() - start) * 1000),
        # queued_ms = time waiting on the gate; sdk_ms = the actual call. A growing
        # queued_ms means judge demand exceeds config.JUDGE_MAX_CONCURRENCY (expected
        # during consolidator bursts — the point is the wait lands HERE, not on the
        # interactive turns).
        queued_ms=queued_ms,
        sdk_ms=int((time.monotonic() - sdk_start) * 1000),
    )

    return JudgeResponse(
        text=accumulated_text,
        model=model_used,
        stop_reason=stop_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
