"""The runner as a pipeline host (F3, 2026-09-28).

A turn with `pipeline="runner"` comes from a surface that has no pipeline of
its own — og118 today. For it the runner runs `persona_core.turn.run_turn`
around its usual brain call: the ask and the reply land in Postgres, the
guardian classifies the turn, the framing carries relevant memory and the live
thread, markers persist their side effects, and facts grow in the background.
A `pipeline="caller"` turn (the gateway) goes straight to the brain, exactly as
before — the gateway already ran the pipeline on its side.

Three process-wide pieces live here:

- the `MemoryStore`, ONE per process, created on first use (a store per turn
  would rebuild the pool and re-run the schema every turn — rule
  db-client-per-process-singleton);
- the in-process judge, which reaches AIRE directly but queues on the SAME
  semaphore as `/v1/judge`, so fact extraction can never crowd out live turns;
- the background-task set that keeps fact extractions from being GC'd.

Degradation is explicit and logged: no Postgres, or a persona the registry does
not know, and the turn runs bare — the pre-F3 behavior — never a failed turn.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog

from persona_core.memory import MemoryStore
from persona_core.runner.judge_client import flatten_utility_messages
from persona_core.turn.pipeline import BrainReply, BrainTurn, InboundTurn, run_turn
from persona_runner.api.judge import get_judge_semaphore
from persona_runner.core.schemas import JudgeRequest, JudgeResponse, TurnRequest, TurnResponse
from persona_runner.engine import aire_route
from shared.personas.registry import get_persona

log = structlog.get_logger()

# Small on purpose: the runner already holds the MCP-tools pool, and a turn
# touches Postgres a handful of times.
_MEMORY_POOL_MIN = 1
_MEMORY_POOL_MAX = 4

# Placeholder ids a caller sends when it has no identity to give.
NO_PRINCIPAL_IDS = frozenset({"0"})

_memory: MemoryStore | None = None
_memory_lock: asyncio.Lock | None = None
_bg_tasks: set[asyncio.Task] = set()


async def get_memory() -> MemoryStore | None:
    """The process-wide store, connected on first use. None without Postgres.

    A failed connect is NOT cached: the next turn tries again, so a Postgres
    blip heals without a restart. The turn in hand runs bare meanwhile.
    """
    global _memory, _memory_lock
    if _memory is not None:
        return _memory
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    if _memory_lock is None:
        _memory_lock = asyncio.Lock()
    async with _memory_lock:
        if _memory is None:
            # Construction AND connect inside the guard: on 2026-09-28 a
            # constructor that raised outside it turned "no memory" into a 500
            # for og118 instead of the bare turn this module promises.
            try:
                store = MemoryStore(url, min_size=_MEMORY_POOL_MIN, max_size=_MEMORY_POOL_MAX)
                await store.connect()
            except Exception:
                log.exception("turn_pipeline_memory_connect_failed")
                return None
            _memory = store
    return _memory


def reset_memory() -> None:
    """Forget the process store so the next turn builds a fresh one (tests)."""
    global _memory, _memory_lock
    _memory = None
    _memory_lock = None


class InProcessJudge:
    """The fact extractor's judge without the HTTP hop to ourselves.

    Same contract as `RunnerJudgeClient.utility_call`, same casita naming
    (`judge_via_aire`) and the same queue as `/v1/judge`.
    """

    def __init__(self, persona_id: str) -> None:
        self.persona_id = persona_id

    async def utility_call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> JudgeResponse:
        user_text, attachments = flatten_utility_messages(messages)
        if not user_text.strip():
            raise ValueError("InProcessJudge.utility_call: messages produced empty user_text")
        req = JudgeRequest(
            system_prompt=system_prompt,
            user_text=user_text,
            max_tokens=max_tokens,
            model=model or None,
            attachments=attachments or None,
            persona_id=self.persona_id,
        )
        async with get_judge_semaphore():
            return await aire_route.judge_via_aire(req)


async def _known_name(memory: MemoryStore, user_id: str) -> str:
    """The name this principal already speaks under, else the id itself.

    og118 knows Bernard only by an Auth0 `sub`, resolved by F2 to his Discord
    principal. Storing his og118 turns under that id, or feeding it to the fact
    extractor as his name, would make him two people in his own memory.
    """
    try:
        return await memory.get_latest_username(user_id) or user_id
    except Exception:
        log.warning("turn_pipeline_name_lookup_failed", user_id=user_id, exc_info=True)
        return user_id


async def serve_turn(req: TurnRequest) -> TurnResponse:
    """The one entry both `/v1/turn` and `/v1/turn/jobs` run."""
    if req.pipeline != "runner":
        return await aire_route.turn_via_aire(req)

    # og118 sends "0" for a caller with no identity (its legacy bearer). A
    # pipeline under that id would store turns and grow facts for nobody.
    if req.user_id in NO_PRINCIPAL_IDS:
        log.warning("turn_pipeline_unavailable", persona_id=req.persona_id, surface=req.surface, reason="no_principal")
        return await aire_route.turn_via_aire(req)
    persona = get_persona(aire_route.base_persona_id(req.persona_id))
    memory = await get_memory()
    if persona is None or memory is None:
        log.warning(
            "turn_pipeline_unavailable",
            persona_id=req.persona_id,
            surface=req.surface,
            reason="unknown_persona" if persona is None else "no_postgres",
        )
        return await aire_route.turn_via_aire(req)

    user_name = req.user_name or await _known_name(memory, req.user_id)
    answered: dict[str, TurnResponse] = {}

    async def brain(turn: BrainTurn) -> BrainReply:
        response = await aire_route.turn_via_aire(
            req.model_copy(
                update={
                    "user_text": turn.user_text,
                    "behavioral_guidance": turn.behavioral_guidance,
                    "attachments": turn.attachments or None,
                }
            )
        )
        answered["response"] = response
        return BrainReply(response.text, response.model or None)

    outbound = await run_turn(
        InboundTurn(
            persona=persona,
            surface=req.surface or "unknown",
            channel_id=req.channel_id,
            user_id=req.user_id,
            user_name=user_name,
            ask=req.user_text,
            # Stored as the persona's Discord account when it has one, so one
            # persona reads as one speaker in `messages` whatever the surface.
            assistant_id=persona.bot_user_id or persona.persona_id,
            attachments=list(req.attachments or []),
            resumed=req.resumed,
        ),
        memory=memory,
        brain=brain,
        judge=InProcessJudge(persona.persona_id),
        bg_tasks=_bg_tasks,
    )
    # Reactions and GIFs have no carrier on this wire yet; say so instead of
    # dropping them in silence.
    if outbound.reactions or outbound.gif_urls:
        log.info(
            "turn_pipeline_sidecars_not_delivered",
            persona_id=persona.persona_id,
            surface=req.surface,
            reactions=len(outbound.reactions),
            gifs=len(outbound.gif_urls),
        )
    return answered["response"].model_copy(update={"text": outbound.text})
