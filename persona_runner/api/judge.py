"""Judge surface — the one-shot utility call, serialized on purpose.

NOT a chat turn: no persona, no MCP servers, no model router. The caller
supplies the entire system prompt; the runner supplies the auth — Shape B per
[[mcp-shape-b-canonical]]: fi-core BUILDS the prompt, the runner EXECUTES it.
Since the AIRE flag flipped permanent, the call is a ``mode=complete`` turn in
a prompt-digest-named utility casita (``aire_route.judge_via_aire``); the local
SDK subprocess it used to spawn died with the local host (backlog
``aire-engine-stage2.md``).

The concurrency gate is the load-bearing part, and it SURVIVES the migration:
the pile-up only MOVED (from this box's Node subprocesses to AIRE's 2 RAM
slots), so serializing here is what stops a consolidator burst from starving
every interactive turn on the droplet. On 2026-05-22 a consolidator backlog
fired ~25 judges at once and OOM-killed the interactive turns. The gate is
THROUGHPUT only: two judges must not cross prompts at ANY value of
JUDGE_MAX_CONCURRENCY, and what guarantees that is the prompt-digest casita
name (``aire_route.judge_casita_for``), never this semaphore.
"""

from __future__ import annotations

import asyncio
import time

import structlog
from fastapi import APIRouter, Header

from persona_runner.core import config
from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import JudgeRequest, JudgeResponse
from persona_runner.engine import aire_route

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
    """Run one utility call with an arbitrary system prompt (text or
    text+image in, text out)."""
    check_auth(authorization)
    semaphore = get_judge_semaphore()
    if semaphore.locked():
        log.info("agent_runner_judge_queued", model=req.model or config.JUDGE_DEFAULT_MODEL)
    queue_start = time.monotonic()
    async with semaphore:
        queued_ms = int((time.monotonic() - queue_start) * 1000)
        response = await aire_route.judge_via_aire(req)
    if queued_ms:
        # A growing queued_ms means judge demand exceeds JUDGE_MAX_CONCURRENCY —
        # expected during consolidator bursts; the point is the wait lands HERE,
        # not on the interactive turns.
        log.info("agent_runner_judge_dequeued", queued_ms=queued_ms)
    return response
